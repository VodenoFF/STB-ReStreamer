"""
EPG (Electronic Program Guide) manager for STB-ReStreamer.
Handles loading, parsing, and accessing EPG data from XMLTV files.
"""
import os
import json
import logging
import time
import xml.etree.ElementTree as ET
import threading
import requests
from typing import Dict, List, Any, Optional, Tuple
from threading import Lock
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger("STB-Proxy")

class EPGManager:
    """
    Manager for EPG (Electronic Program Guide) data.
    Handles loading, parsing, and accessing EPG data from XMLTV files.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the EPG manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.lock = Lock()
        self.epg_data = {}  # Format: {channel_id: [programs]}
        self.channel_map = {}  # Format: {tvg_id: stb_channel_id}
        self.last_update = 0
        self.update_thread = None
        self.running = False
        
        # Initialize data directory
        if hasattr(self.config_manager, 'get_data_dir'):
            self.data_dir = self.config_manager.get_data_dir()
        else:
            # Fallback to default data directory
            self.data_dir = "data"
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize EPG file
        self.epg_file = os.path.join(self.data_dir, "epg_data.json")
        self.channel_map_file = os.path.join(self.data_dir, "epg_channel_map.json")
        
        # Load EPG data from file
        self._load_epg_data()
        
        # Start update thread
        self._start_update_thread()
        
        logger.info("EPG manager initialized")
        
    def _load_epg_data(self):
        """Load EPG data from file."""
        with self.lock:
            try:
                # Load channel map
                if os.path.exists(self.channel_map_file):
                    with open(self.channel_map_file, 'r', encoding='utf-8') as f:
                        self.channel_map = json.load(f)
                    logger.info(f"Loaded EPG channel map with {len(self.channel_map)} channels")
                
                # Load EPG data
                if os.path.exists(self.epg_file):
                    with open(self.epg_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.epg_data = data.get('epg_data', {})
                        self.last_update = data.get('last_update', 0)
                    
                    # Count programs
                    program_count = sum(len(programs) for programs in self.epg_data.values())
                    logger.info(f"Loaded EPG data with {len(self.epg_data)} channels and {program_count} programs")
                    logger.info(f"Last EPG update: {datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                logger.error(f"Error loading EPG data: {str(e)}")
                
    def _save_epg_data(self):
        """Save EPG data to file."""
        with self.lock:
            try:
                # Save EPG data
                data = {
                    'epg_data': self.epg_data,
                    'last_update': self.last_update
                }
                with open(self.epg_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                
                # Save channel map
                with open(self.channel_map_file, 'w', encoding='utf-8') as f:
                    json.dump(self.channel_map, f)
                
                # Count programs
                program_count = sum(len(programs) for programs in self.epg_data.values())
                logger.info(f"Saved EPG data with {len(self.epg_data)} channels and {program_count} programs")
            except Exception as e:
                logger.error(f"Error saving EPG data: {str(e)}")
                
    def _start_update_thread(self):
        """Start the EPG update thread."""
        if not self.update_thread:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_thread, daemon=True)
            self.update_thread.start()
            logger.info("Started EPG update thread")
            
    def _update_thread(self):
        """Background thread for updating EPG data."""
        while self.running:
            try:
                # Check if update is needed
                current_time = time.time()
                
                # Get update interval from config
                try:
                    if hasattr(self.config_manager, 'get'):
                        update_interval = self.config_manager.get('epg', 'update_interval', default=6)
                    else:
                        update_interval = self.config_manager.get_setting('epg_update_interval', 6)
                except Exception:
                    update_interval = 6  # Default to 6 hours
                    
                # Convert to seconds
                update_interval_seconds = update_interval * 3600
                
                # Check if update is needed
                if current_time - self.last_update > update_interval_seconds:
                    # Get EPG source URLs from config
                    try:
                        if hasattr(self.config_manager, 'get'):
                            epg_sources = self.config_manager.get('epg', 'sources', default=[])
                        else:
                            epg_sources = self.config_manager.get_setting('epg_sources', [])
                    except Exception:
                        epg_sources = []
                        
                    # Update EPG data from each source
                    for source in epg_sources:
                        try:
                            self.update_epg_from_source(source)
                        except Exception as e:
                            logger.error(f"Error updating EPG from source {source}: {str(e)}")
                    
                    # Save updated data
                    self._save_epg_data()
                
                # Sleep for 30 minutes before checking again
                sleep_interval = min(1800, update_interval_seconds / 4)
                time.sleep(sleep_interval)
            except Exception as e:
                logger.error(f"Error in EPG update thread: {str(e)}")
                time.sleep(300)  # Sleep for 5 minutes before trying again
                
    def update_epg_from_source(self, source_url: str) -> bool:
        """
        Update EPG data from a source URL.
        
        Args:
            source_url: URL of the EPG source (XMLTV format)
            
        Returns:
            True if updated, False if failed
        """
        try:
            logger.info(f"Updating EPG from source: {source_url}")
            
            # Check if source is a local file
            if os.path.exists(source_url):
                with open(source_url, 'r', encoding='utf-8') as f:
                    xmltv_content = f.read()
            else:
                # Download XMLTV file
                response = requests.get(source_url, timeout=60)
                if not response.ok:
                    logger.error(f"Failed to download EPG data: {response.status_code}")
                    return False
                
                xmltv_content = response.text
            
            # Parse XMLTV content
            self._parse_xmltv(xmltv_content)
            
            # Update last update time
            self.last_update = time.time()
            
            logger.info(f"EPG updated from source: {source_url}")
            return True
        except Exception as e:
            logger.error(f"Error updating EPG from source {source_url}: {str(e)}")
            return False
            
    def _parse_xmltv(self, xmltv_content: str):
        """
        Parse XMLTV content.
        
        Args:
            xmltv_content: XMLTV content as string
        """
        try:
            logger.debug("Parsing XMLTV content")
            
            # Parse XML
            root = ET.fromstring(xmltv_content)
            
            # Get namespace if any
            ns = ''
            if root.tag.startswith('{'):
                ns = root.tag.split('}')[0] + '}'
            
            # Process channels
            for channel in root.findall(f"{ns}channel"):
                channel_id = channel.get('id')
                if not channel_id:
                    continue
                
                # Store channel in map (without overwriting existing mappings)
                if channel_id not in self.channel_map:
                    self.channel_map[channel_id] = channel_id
            
            # Process programs
            with self.lock:
                for program in root.findall(f"{ns}programme"):
                    channel_id = program.get('channel')
                    if not channel_id:
                        continue
                    
                    # Get mapped channel ID
                    stb_channel_id = self.channel_map.get(channel_id)
                    if not stb_channel_id:
                        stb_channel_id = channel_id  # Use original ID if no mapping
                    
                    # Parse program
                    program_data = self._parse_program(program, ns)
                    if not program_data:
                        continue
                    
                    # Add to EPG data
                    if stb_channel_id not in self.epg_data:
                        self.epg_data[stb_channel_id] = []
                    
                    # Check if program already exists (by start time and title)
                    exists = False
                    for existing in self.epg_data[stb_channel_id]:
                        if (existing['start_time'] == program_data['start_time'] and
                            existing['title'] == program_data['title']):
                            exists = True
                            break
                    
                    if not exists:
                        self.epg_data[stb_channel_id].append(program_data)
            
            # Sort programs by start time for each channel
            with self.lock:
                for channel_id in self.epg_data:
                    self.epg_data[channel_id].sort(key=lambda p: p['start_time'])
            
            # Count programs
            program_count = sum(len(programs) for programs in self.epg_data.values())
            logger.info(f"Parsed XMLTV data with {len(self.epg_data)} channels and {program_count} programs")
        except Exception as e:
            logger.error(f"Error parsing XMLTV content: {str(e)}")
            
    def _parse_program(self, program_elem, ns: str) -> Optional[Dict]:
        """
        Parse a single program element.
        
        Args:
            program_elem: XML element for the program
            ns: Namespace prefix
            
        Returns:
            Program data as dictionary or None if failed
        """
        try:
            # Get start and stop times
            start = program_elem.get('start')
            stop = program_elem.get('stop')
            
            if not start or not stop:
                return None
            
            # Parse times (format: 20230701123000 +0000)
            start_time = self._parse_xmltv_time(start)
            stop_time = self._parse_xmltv_time(stop)
            
            if not start_time or not stop_time:
                return None
            
            # Get title
            title_elem = program_elem.find(f"{ns}title")
            title = title_elem.text if title_elem is not None else "Unknown"
            
            # Get description
            desc_elem = program_elem.find(f"{ns}desc")
            description = desc_elem.text if desc_elem is not None else ""
            
            # Get category
            category_elem = program_elem.find(f"{ns}category")
            category = category_elem.text if category_elem is not None else "Unknown"
            
            # Get language
            lang = ""
            if title_elem is not None:
                lang = title_elem.get('lang', '')
            
            # Generate a unique ID for the program
            program_id = f"prog_{start_time}_{hash(title)}"
            
            # Create program data
            program_data = {
                'id': program_id,
                'title': title,
                'description': description,
                'start_time': start_time,
                'end_time': stop_time,
                'duration': stop_time - start_time,
                'type': category,
                'language': lang
            }
            
            return program_data
        except Exception as e:
            logger.error(f"Error parsing program: {str(e)}")
            return None
            
    def _parse_xmltv_time(self, time_str: str) -> Optional[int]:
        """
        Parse XMLTV time string to timestamp.
        
        Args:
            time_str: Time string (format: 20230701123000 +0000)
            
        Returns:
            Timestamp or None if failed
        """
        try:
            # Remove timezone part
            time_str = time_str.split(' ')[0]
            
            # Convert to timestamp
            dt = datetime.strptime(time_str, "%Y%m%d%H%M%S")
            return int(dt.timestamp())
        except Exception as e:
            logger.error(f"Error parsing XMLTV time: {str(e)}")
            return None
            
    def map_channel(self, tvg_id: str, stb_channel_id: str) -> bool:
        """
        Map an EPG channel ID to an STB channel ID.
        
        Args:
            tvg_id: TVG ID from EPG source
            stb_channel_id: Channel ID in STB-ReStreamer
            
        Returns:
            True if mapped, False if failed
        """
        with self.lock:
            try:
                self.channel_map[tvg_id] = stb_channel_id
                self._save_epg_data()
                return True
            except Exception as e:
                logger.error(f"Error mapping channel: {str(e)}")
                return False
                
    def get_program(self, channel_id: str, timestamp: Optional[int] = None) -> Optional[Dict]:
        """
        Get the current or specific program for a channel.
        
        Args:
            channel_id: Channel ID
            timestamp: Timestamp to get program for, or None for current time
            
        Returns:
            Program data or None if not found
        """
        with self.lock:
            try:
                # Use current time if timestamp not provided
                if timestamp is None:
                    timestamp = int(time.time())
                
                # Check if channel exists in EPG data
                if channel_id not in self.epg_data:
                    return None
                
                # Find program for the given timestamp
                for program in self.epg_data[channel_id]:
                    if program['start_time'] <= timestamp < program['end_time']:
                        return program
                
                return None
            except Exception as e:
                logger.error(f"Error getting program: {str(e)}")
                return None
                
    def get_programs(self, channel_id: str, start_time: Optional[int] = None, 
                    end_time: Optional[int] = None) -> List[Dict]:
        """
        Get programs for a channel within a time range.
        
        Args:
            channel_id: Channel ID
            start_time: Start timestamp, or None for current time
            end_time: End timestamp, or None for 24 hours from start
            
        Returns:
            List of program data
        """
        with self.lock:
            try:
                # Use current time if start_time not provided
                if start_time is None:
                    start_time = int(time.time())
                
                # Use 24 hours from start if end_time not provided
                if end_time is None:
                    end_time = start_time + 24 * 3600
                
                # Check if channel exists in EPG data
                if channel_id not in self.epg_data:
                    return []
                
                # Find programs within the time range
                programs = []
                for program in self.epg_data[channel_id]:
                    # Include programs that overlap with the time range
                    if program['end_time'] > start_time and program['start_time'] < end_time:
                        programs.append(program)
                
                return programs
            except Exception as e:
                logger.error(f"Error getting programs: {str(e)}")
                return []
                
    def get_channel_ids(self) -> List[str]:
        """
        Get all channel IDs with EPG data.
        
        Returns:
            List of channel IDs
        """
        with self.lock:
            return list(self.epg_data.keys())
            
    def get_channel_map(self) -> Dict[str, str]:
        """
        Get the channel mapping.
        
        Returns:
            Dictionary mapping TVG IDs to STB channel IDs
        """
        with self.lock:
            return self.channel_map.copy()
            
    def clear_outdated_programs(self, max_age_days: int = 1) -> int:
        """
        Clear outdated programs from EPG data.
        
        Args:
            max_age_days: Maximum age of programs to keep (in days)
            
        Returns:
            Number of programs removed
        """
        with self.lock:
            try:
                # Calculate cutoff time
                cutoff_time = int(time.time()) - max_age_days * 24 * 3600
                
                removed_count = 0
                for channel_id in self.epg_data:
                    # Filter programs
                    original_count = len(self.epg_data[channel_id])
                    self.epg_data[channel_id] = [p for p in self.epg_data[channel_id] 
                                                 if p['end_time'] >= cutoff_time]
                    removed_count += original_count - len(self.epg_data[channel_id])
                
                # Save changes
                if removed_count > 0:
                    self._save_epg_data()
                    logger.info(f"Removed {removed_count} outdated programs from EPG data")
                
                return removed_count
            except Exception as e:
                logger.error(f"Error clearing outdated programs: {str(e)}")
                return 0
                
    def get_epg_stats(self) -> Dict[str, Any]:
        """
        Get EPG statistics.
        
        Returns:
            Dictionary with EPG statistics
        """
        with self.lock:
            try:
                # Count programs
                total_programs = sum(len(programs) for programs in self.epg_data.values())
                
                # Get time range
                min_time = float('inf')
                max_time = 0
                for channel_programs in self.epg_data.values():
                    if channel_programs:
                        min_time = min(min_time, min(p['start_time'] for p in channel_programs))
                        max_time = max(max_time, max(p['end_time'] for p in channel_programs))
                
                if min_time == float('inf'):
                    min_time = 0
                
                # Format times
                if min_time > 0 and max_time > 0:
                    min_time_str = datetime.fromtimestamp(min_time).strftime('%Y-%m-%d %H:%M:%S')
                    max_time_str = datetime.fromtimestamp(max_time).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    min_time_str = "N/A"
                    max_time_str = "N/A"
                
                # Last update time
                last_update_str = datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S') \
                                  if self.last_update > 0 else "Never"
                
                return {
                    'channel_count': len(self.epg_data),
                    'program_count': total_programs,
                    'mapping_count': len(self.channel_map),
                    'min_time': min_time,
                    'max_time': max_time,
                    'min_time_str': min_time_str,
                    'max_time_str': max_time_str,
                    'last_update': self.last_update,
                    'last_update_str': last_update_str
                }
            except Exception as e:
                logger.error(f"Error getting EPG stats: {str(e)}")
                return {
                    'error': str(e)
                }
                
    def shutdown(self):
        """Shutdown the EPG manager."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        self._save_epg_data()
        logger.info("EPG manager shutdown")

    def get_mappings(self) -> Dict[str, str]:
        """
        Get all channel mappings.
        
        Returns:
            Dict[str, str]: Channel mappings
        """
        return self.get_channel_map()