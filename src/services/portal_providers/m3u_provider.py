"""
M3U Playlist Provider for STB-ReStreamer.
Supports loading channels from M3U/M3U8 playlists.
"""
import time
import os
import re
import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

from src.services.portal_providers.base_provider import BasePortalProvider

# Configure logger
logger = logging.getLogger("STB-Proxy")

class M3UPlaylistProvider(BasePortalProvider):
    """Implementation of the M3U Playlist provider."""
    
    def __init__(self):
        """Initialize the M3U Playlist provider."""
        self.playlist_cache = {}  # Format: {url: (content, expiry)}
        self.playlist_lifetime = 24 * 3600  # 24 hours in seconds (default)
    
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get authentication token for M3U provider.
        For M3U playlists, we don't need a real token, but we return a dummy one.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            
        Returns:
            Dummy token for compatibility
        """
        # For M3U, we don't need real authentication
        # Just return a dummy token for compatibility with the interface
        return f"m3u_{mac}_{int(time.time())}"
            
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> Optional[Dict]:
        """
        Get user profile for M3U provider.
        For M3U playlists, we create a dummy profile.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token (dummy)
            
        Returns:
            Dummy profile for compatibility
        """
        # Create a dummy profile for compatibility
        return {
            'status': 'active',
            'expires': int(time.time()) + 365 * 24 * 3600,  # 1 year from now
            'max_connections': 1,
            'username': f"m3u_user_{mac[-6:]}",
            'package': 'M3U Playlist'
        }
            
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> List[Dict]:
        """
        Get channel list from M3U playlist.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token (dummy)
            
        Returns:
            List of channel dictionaries
        """
        try:
            # Extract portal configuration
            playlist_url = portal.get('url', '')
            refresh_interval = portal.get('refresh_interval', 24)  # Default 24 hours
            
            if not playlist_url:
                logger.error("M3U playlist URL is missing")
                return []
                
            # Convert refresh interval to seconds
            refresh_seconds = refresh_interval * 3600
            self.playlist_lifetime = refresh_seconds
            
            # Get playlist content
            playlist_content = self._get_playlist_content(playlist_url)
            if not playlist_content:
                logger.error("Failed to get M3U playlist content")
                return []
                
            # Parse playlist content
            channels = self._parse_playlist(playlist_content, playlist_url)
            
            logger.info(f"Loaded {len(channels)} channels from M3U playlist")
            return channels
                
        except Exception as e:
            logger.error(f"Error getting channels from M3U playlist: {str(e)}")
            return []
            
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str]) -> Optional[str]:
        """
        Get stream URL for a channel from M3U playlist.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID
            token: Authentication token (dummy)
            
        Returns:
            Stream URL or None if failed
        """
        try:
            # Extract portal configuration
            playlist_url = portal.get('url', '')
            
            if not playlist_url:
                logger.error("M3U playlist URL is missing")
                return None
                
            # Get playlist content
            playlist_content = self._get_playlist_content(playlist_url)
            if not playlist_content:
                logger.error("Failed to get M3U playlist content")
                return None
                
            # Parse playlist to find the channel
            channels = self._parse_playlist(playlist_content, playlist_url)
            
            # Find channel by ID
            for channel in channels:
                if channel.get('id') == channel_id:
                    stream_url = channel.get('stream_url')
                    if stream_url:
                        return stream_url
            
            logger.error(f"Channel ID {channel_id} not found in M3U playlist")
            return None
                
        except Exception as e:
            logger.error(f"Error getting stream URL from M3U playlist: {str(e)}")
            return None
            
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str], 
               token: Optional[str], start_time: Optional[int] = None, 
               end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data.
        For M3U playlists, we don't have built-in EPG, so return empty data.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID for specific channel, or None for all
            token: Authentication token (dummy)
            start_time: Start time timestamp, or None for current time
            end_time: End time timestamp, or None for 24 hours from start
            
        Returns:
            Empty dictionary (M3U playlists don't have built-in EPG)
        """
        # M3U playlists don't have built-in EPG
        # The EPG should be handled by an EPG manager that can load XMLTV data
        logger.error(f"Failed to get EPG for {portal.get('id', 'unknown')}:{mac}")
        return {}
        
    def _get_playlist_content(self, playlist_url: str) -> Optional[str]:
        """
        Get the content of an M3U playlist.
        Uses caching to avoid frequent downloads.
        
        Args:
            playlist_url: URL or path to the playlist
            
        Returns:
            Playlist content as string or None if failed
        """
        try:
            # Check if URL is in cache and not expired
            current_time = time.time()
            if playlist_url in self.playlist_cache:
                content, expiry = self.playlist_cache[playlist_url]
                if current_time < expiry:
                    logger.debug(f"Using cached M3U playlist: {playlist_url}")
                    return content
            
            # Check if the URL is actually a local file path
            parsed_url = urlparse(playlist_url)
            if not parsed_url.scheme or parsed_url.scheme == 'file':
                # It's a local file
                file_path = parsed_url.path
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Cache the content
                    self.playlist_cache[playlist_url] = (content, current_time + self.playlist_lifetime)
                    return content
                else:
                    logger.error(f"M3U playlist file not found: {file_path}")
                    return None
            
            # It's a remote URL, download it
            response = requests.get(playlist_url, timeout=30)
            if not response.ok:
                logger.error(f"Failed to download M3U playlist: {response.status_code}")
                return None
                
            content = response.text
            
            # Cache the content
            self.playlist_cache[playlist_url] = (content, current_time + self.playlist_lifetime)
            return content
                
        except Exception as e:
            logger.error(f"Error getting M3U playlist content: {str(e)}")
            return None
            
    def _parse_playlist(self, content: str, base_url: str) -> List[Dict]:
        """
        Parse M3U playlist content.
        
        Args:
            content: Playlist content as string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of channel dictionaries
        """
        try:
            channels = []
            channel_id = 1
            
            # Check if content starts with #EXTM3U
            if not content.strip().startswith('#EXTM3U'):
                logger.error("Invalid M3U playlist: missing #EXTM3U header")
                return channels
                
            # Split content into lines
            lines = content.strip().split('\n')
            
            current_title = None
            current_attrs = {}
            current_group = "Unknown"
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Parse EXTINF line (channel info)
                if line.startswith('#EXTINF:'):
                    # Extract title from the line
                    title_match = re.search(r'#EXTINF:.*,\s*(.*?)$', line)
                    if title_match:
                        current_title = title_match.group(1)
                    else:
                        current_title = f"Channel {channel_id}"
                        
                    # Extract attributes
                    current_attrs = {}
                    
                    # Extract tvg-id
                    tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
                    if tvg_id_match:
                        current_attrs['tvg_id'] = tvg_id_match.group(1)
                        
                    # Extract tvg-name
                    tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
                    if tvg_name_match:
                        current_attrs['tvg_name'] = tvg_name_match.group(1)
                        
                    # Extract tvg-logo
                    tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    if tvg_logo_match:
                        current_attrs['tvg_logo'] = tvg_logo_match.group(1)
                        
                    # Extract group-title
                    group_match = re.search(r'group-title="([^"]*)"', line)
                    if group_match:
                        current_group = group_match.group(1)
                        
                elif line.startswith('#EXTVLCOPT:') or line.startswith('#EXTGRP:'):
                    # Additional metadata, ignore for now
                    continue
                    
                elif not line.startswith('#'):
                    # This should be the URL
                    if current_title:
                        # Create a unique ID for the channel
                        ch_id = current_attrs.get('tvg_id', f"m3u_{channel_id}")
                        
                        # Resolve relative URL if needed
                        stream_url = line
                        if not (stream_url.startswith('http://') or stream_url.startswith('https://') or stream_url.startswith('rtmp://')):
                            stream_url = urljoin(base_url, stream_url)
                            
                        channel = {
                            'id': ch_id,
                            'name': current_attrs.get('tvg_name', current_title),
                            'number': channel_id,
                            'type': current_group,
                            'logo': current_attrs.get('tvg_logo', ''),
                            'stream_url': stream_url
                        }
                        
                        channels.append(channel)
                        channel_id += 1
                        current_title = None
                        current_attrs = {}
                        
            return channels
                
        except Exception as e:
            logger.error(f"Error parsing M3U playlist: {str(e)}")
            return []