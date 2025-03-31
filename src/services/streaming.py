"""
Streaming service for STB-ReStreamer.
Handles stream management and proxying.
"""
import os
import time
import logging
import subprocess
import shlex
import threading
from typing import Dict, Optional, Tuple, Any, Generator, List
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class StreamManager:
    """
    Service for handling stream proxying and management.
    """
    def __init__(self, config_manager, mac_manager):
        """
        Initialize the streaming service.
        
        Args:
            config_manager: Configuration manager instance
            mac_manager: MAC address manager instance
        """
        self.config_manager = config_manager
        self.mac_manager = mac_manager
        self.lock = Lock()
        self.active_streams = {}  # Format: {portal_id: {channel_id: {process, start_time, etc}}}
        self.cleanup_thread = threading.Thread(target=self._cleanup_streams, daemon=True)
        self.cleanup_thread.start()
        logger.info("Stream manager initialized")
        
    def test_stream(self, stream_url: str, timeout: int = 5, proxy: Optional[str] = None) -> bool:
        """
        Test if a stream URL is working.
        
        Args:
            stream_url (str): Stream URL to test
            timeout (int): Timeout in seconds
            proxy (Optional[str]): Proxy URL if needed
            
        Returns:
            bool: True if stream is working, False otherwise
        """
        try:
            # Build FFmpeg command for testing
            ffmpeg_path = self.config_manager.get_setting("ffmpeg path", "ffmpeg")
            cmd = [ffmpeg_path, "-hide_banner", "-loglevel", "error"]
            
            # Add proxy if provided
            if proxy:
                cmd.extend(["-http_proxy", proxy])
                
            # Add input options
            cmd.extend(["-timeout", str(timeout * 1000000), "-i", stream_url])
            
            # Add output options for quick testing (just get headers, don't actually stream)
            cmd.extend(["-t", "0.1", "-f", "null", "-"])
            
            # Run FFmpeg process
            logger.debug(f"Testing stream: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, timeout=timeout + 2)
            
            # Check if successful
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Error testing stream: {str(e)}")
            return False
            
    def prepare_ffmpeg_command(self, stream_url: str, proxy: Optional[str] = None, 
                             is_web: bool = False, is_preview: bool = False) -> List[str]:
        """
        Prepare FFmpeg command for streaming.
        
        Args:
            stream_url (str): Stream URL
            proxy (Optional[str]): Proxy URL if needed
            is_web (bool): Whether this is for web preview
            is_preview (bool): Alias for is_web parameter
            
        Returns:
            List[str]: FFmpeg command list
        """
        # Get FFmpeg path from configuration
        ffmpeg_path = self.config_manager.get_setting("ffmpeg path", "ffmpeg")
        
        # Determine if we need to transcode (either is_web or is_preview)
        transcode = is_web or is_preview
        
        # Build command
        cmd = [ffmpeg_path, "-hide_banner", "-loglevel", "error"]
        
        # Add proxy if provided
        if proxy:
            cmd.extend(["-http_proxy", proxy])
            
        # Add input options
        cmd.extend(["-i", stream_url])
        
        # Add output options
        if transcode:
            # Web preview (lower quality)
            cmd.extend([
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
                "-crf", "28", "-maxrate", "1M", "-bufsize", "2M", "-r", "25",
                "-c:a", "aac", "-ac", "2", "-ab", "128k",
                "-f", "mpegts", "pipe:1"
            ])
        else:
            # Normal streaming (copy codec)
            cmd.extend([
                "-c", "copy",
                "-f", "mpegts", "pipe:1"
            ])
            
        return cmd
        
    def stream_generator(self, ffmpeg_cmd: List[str], portal_id: str, channel_id: str,
                      mac: str, channel_name: str, client_ip: str, portal_name: str) -> Generator[bytes, None, None]:
        """
        Generate a stream using FFmpeg.
        
        Args:
            ffmpeg_cmd (List[str]): FFmpeg command
            portal_id (str): Portal ID
            channel_id (str): Channel ID
            mac (str): MAC address
            channel_name (str): Channel name
            client_ip (str): Client IP address
            portal_name (str): Portal name
            
        Yields:
            bytes: Stream data
        """
        process = None
        try:
            # Run FFmpeg process
            logger.info(f"Starting stream for Portal({portal_id}):Channel({channel_id})")
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10 * 1024 * 1024  # 10MB buffer
            )
            
            # Register stream
            self._register_stream(portal_id, channel_id, process, mac, 
                               channel_name, client_ip, portal_name)
            
            # Mark MAC as occupied
            self.mac_manager.occupy_mac(portal_id, mac, channel_id, 
                                     channel_name, client_ip, portal_name)
            
            # Stream data
            while process.poll() is None:
                data = process.stdout.read(1024 * 1024)  # Read 1MB at a time
                if not data:
                    break
                yield data
                
            # Check if process ended unexpectedly
            if process.poll() is not None:
                logger.warning(f"FFmpeg process ended: {process.poll()}")
                error = process.stderr.read().decode('utf-8', errors='ignore')
                if error:
                    logger.error(f"FFmpeg error: {error}")
                    
        except Exception as e:
            logger.error(f"Error in stream generator: {str(e)}")
            
        finally:
            # Clean up process
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    logger.error(f"Error terminating FFmpeg process: {str(e)}")
                    try:
                        process.kill()
                    except:
                        pass
                        
            # Unregister stream
            self._unregister_stream(portal_id, channel_id)
            
            # Release MAC
            self.mac_manager.release_mac(portal_id, mac, channel_id, 
                                      channel_name, client_ip, portal_name)
                                      
    def _register_stream(self, portal_id: str, channel_id: str, process: subprocess.Popen,
                      mac: str, channel_name: str, client_ip: str, portal_name: str) -> None:
        """
        Register an active stream.
        
        Args:
            portal_id (str): Portal ID
            channel_id (str): Channel ID
            process (subprocess.Popen): FFmpeg process
            mac (str): MAC address
            channel_name (str): Channel name
            client_ip (str): Client IP address
            portal_name (str): Portal name
        """
        with self.lock:
            if portal_id not in self.active_streams:
                self.active_streams[portal_id] = {}
                
            self.active_streams[portal_id][channel_id] = {
                "process": process,
                "mac": mac,
                "start_time": time.time(),
                "channel_name": channel_name,
                "client_ip": client_ip,
                "portal_name": portal_name
            }
            
    def _unregister_stream(self, portal_id: str, channel_id: str) -> None:
        """
        Unregister an active stream.
        
        Args:
            portal_id (str): Portal ID
            channel_id (str): Channel ID
        """
        with self.lock:
            if portal_id in self.active_streams and channel_id in self.active_streams[portal_id]:
                del self.active_streams[portal_id][channel_id]
                
                if not self.active_streams[portal_id]:
                    del self.active_streams[portal_id]
                    
    def _cleanup_streams(self) -> None:
        """
        Background thread to clean up stale streams.
        """
        while True:
            try:
                with self.lock:
                    # Check all active streams
                    for portal_id in list(self.active_streams.keys()):
                        for channel_id in list(self.active_streams[portal_id].keys()):
                            stream_data = self.active_streams[portal_id][channel_id]
                            process = stream_data.get("process")
                            
                            # Check if process is still running
                            if process and process.poll() is not None:
                                # Process ended, unregister and release MAC
                                logger.info(f"Cleaning up stale stream: Portal({portal_id}):Channel({channel_id})")
                                self._unregister_stream(portal_id, channel_id)
                                self.mac_manager.release_mac(
                                    portal_id, 
                                    stream_data.get("mac", ""),
                                    channel_id,
                                    stream_data.get("channel_name", ""),
                                    stream_data.get("client_ip", ""),
                                    stream_data.get("portal_name", "")
                                )
            except Exception as e:
                logger.error(f"Error in stream cleanup: {str(e)}")
                
            # Sleep for a while
            time.sleep(30)
            
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about currently active streams.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of active streams with details
        """
        with self.lock:
            # Create a copy without the process objects
            result = {}
            for portal_id, channels in self.active_streams.items():
                result[portal_id] = {}
                for channel_id, stream_data in channels.items():
                    result[portal_id][channel_id] = {
                        k: v for k, v in stream_data.items() if k != "process"
                    }
                    # Add duration
                    if "start_time" in result[portal_id][channel_id]:
                        start_time = result[portal_id][channel_id]["start_time"]
                        result[portal_id][channel_id]["duration"] = int(time.time() - start_time)
                        
            return result