"""
EPG management for STB-ReStreamer.
Handles loading, caching, and retrieval of Electronic Program Guide data.
"""
import os
import json
import time
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from urllib.parse import urlparse

import requests

# Configure logger
logger = logging.getLogger("STB-Proxy")

class EPGManager:
    """
    Manager for Electronic Program Guide (EPG) data.
    Supports both XMLTV format and provider-specific EPG data.
    """
    
    def __init__(self, config_manager, data_dir: str = "data/epg"):
        """
        Initialize the EPG manager.
        
        Args:
            config_manager: Configuration manager instance
            data_dir (str): Directory for EPG data files
        """
        self.config_manager = config_manager
        self.data_dir = data_dir
        self.lock = Lock()
        self.epg_data = {}  # Format: {source_id: {channel_id: [program_data]}}
        self.sources = {}  # Format: {source_id: {type, url, last_update, etc.}}
        self.channel_mappings = {}  # Format: {(source_id, source_channel_id): target_channel_id}
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load configuration
        self._load_config()
        
        # Start update thread
        self.update_thread = Thread(target=self._update_thread, daemon=True)
        self.update_thread.start()
        
        logger.info("EPG manager initialized")
    
    def _load_config(self) -> None:
        """
        Load EPG configuration.
        """
        try:
            config_file = os.path.join(self.data_dir, "epg_config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.sources = config.get('sources', {})
                    self.channel_mappings = config.get('channel_mappings', {})
                    logger.debug(f"Loaded {len(self.sources)} EPG sources and {len(self.channel_mappings)} channel mappings")
            
            # Load cached EPG data
            for source_id in self.sources:
                self._load_epg_data(source_id)
        
        except Exception as e:
            logger.error(f"Error loading EPG configuration: {str(e)}")
            self.sources = {}
            self.channel_mappings = {}
    
    def _save_config(self) -> None:
        """
        Save EPG configuration.
        """
        try:
            config_file = os.path.join(self.data_dir, "epg_config.json")
            config = {
                'sources': self.sources,
                'channel_mappings': self.channel_mappings
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
                logger.debug(f"Saved EPG configuration with {len(self.sources)} sources")
        
        except Exception as e:
            logger.error(f"Error saving EPG configuration: {str(e)}")
    
    def _load_epg_data(self, source_id: str) -> None:
        """
        Load EPG data from cache for a specific source.
        
        Args:
            source_id (str): Source ID
        """
        try:
            epg_file = os.path.join(self.data_dir, f"epg_{source_id}.json")
            if os.path.exists(epg_file):
                with open(epg_file, 'r', encoding='utf-8') as f:
                    self.epg_data[source_id] = json.load(f)
                    # Count total programs
                    program_count = sum(len(programs) for programs in self.epg_data[source_id].values())
                    logger.debug(f"Loaded EPG data for source {source_id}: {len(self.epg_data[source_id])} channels, {program_count} programs")
            else:
                self.epg_data[source_id] = {}
        
        except Exception as e:
            logger.error(f"Error loading EPG data for source {source_id}: {str(e)}")
            self.epg_data[source_id] = {}
    
    def _save_epg_data(self, source_id: str) -> None:
        """
        Save EPG data to cache for a specific source.
        
        Args:
            source_id (str): Source ID
        """
        try:
            epg_file = os.path.join(self.data_dir, f"epg_{source_id}.json")
            
            # Count total programs
            program_count = sum(len(programs) for programs in self.epg_data[source_id].values())
            
            with open(epg_file, 'w', encoding='utf-8') as f:
                json.dump(self.epg_data[source_id], f)
                logger.debug(f"Saved EPG data for source {source_id}: {len(self.epg_data[source_id])} channels, {program_count} programs")
        
        except Exception as e:
            logger.error(f"Error saving EPG data for source {source_id}: {str(e)}")
    
    def _update_thread(self) -> None:
        """
        Background thread for updating EPG data.
        """
        while True:
            try:
                # Check each source for updates
                with self.lock:
                    for source_id, source in self.sources.items():
                        # Check if update is needed
                        last_update = source.get('last_update', 0)
                        update_interval = source.get('update_interval', 24 * 3600)  # Default: 24 hours
                        
                        if time.time() - last_update > update_interval:
                            try:
                                # Update EPG data
                                self._update_epg_data(source_id)
                                
                                # Update last_update time
                                self.sources[source_id]['last_update'] = time.time()
                                self._save_config()
                            
                            except Exception as e:
                                logger.error(f"Error updating EPG data for source {source_id}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Error in EPG update thread: {str(e)}")
            
            # Sleep for 1 hour
            time.sleep(3600)
    
    def _update_epg_data(self, source_id: str) -> None:
        """
        Update EPG data for a specific source.
        
        Args:
            source_id (str): Source ID
        """
        source = self.sources.get(source_id)
        if not source:
            logger.error(f"Source not found: {source_id}")
            return
        
        source_type = source.get('type')
        source_url = source.get('url')
        
        if not source_url:
            logger.error(f"Source URL is empty for source {source_id}")
            return
        
        if source_type == 'xmltv':
            # Update from XMLTV
            self._update_from_xmltv(source_id, source_url)
        elif source_type == 'provider':
            # Update from provider
            # This is handled by the provider's EPG function
            pass
        else:
            logger.error(f"Unknown source type: {source_type}")
    
    def _update_from_xmltv(self, source_id: str, url: str) -> None:
        """
        Update EPG data from an XMLTV file.
        
        Args:
            source_id (str): Source ID
            url (str): URL or path to the XMLTV file
        """
        try:
            logger.info(f"Updating EPG data from XMLTV for source {source_id}")
            
            # Get XMLTV content
            content = self._get_xmltv_content(url)
            if not content:
                logger.error(f"Failed to get XMLTV content for source {source_id}")
                return
            
            # Parse XMLTV
            self._parse_xmltv(source_id, content)
            
            # Save EPG data
            self._save_epg_data(source_id)
            
            logger.info(f"EPG data updated for source {source_id}")
        
        except Exception as e:
            logger.error(f"Error updating EPG data from XMLTV for source {source_id}: {str(e)}")
    
    def _get_xmltv_content(self, url: str) -> Optional[str]:
        """
        Get XMLTV content from URL or file.
        
        Args:
            url (str): URL or path to the XMLTV file
            
        Returns:
            Optional[str]: XMLTV content or None if failed
        """
        try:
            # Check if it's a URL or a local file
            parsed_url = urlparse(url)
            
            if parsed_url.scheme in ('http', 'https'):
                # It's a URL, download it
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"Failed to download XMLTV: {response.status_code}")
                    return None
                
                return response.text
            
            else:
                # It's a local file, read it
                with open(url, 'r', encoding='utf-8') as f:
                    return f.read()
        
        except Exception as e:
            logger.error(f"Error getting XMLTV content: {str(e)}")
            return None
    
    def _parse_xmltv(self, source_id: str, content: str) -> None:
        """
        Parse XMLTV content.
        
        Args:
            source_id (str): Source ID
            content (str): XMLTV content
        """
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Initialize EPG data for this source
            epg_data = {}
            
            # Parse channels
            for channel_elem in root.findall('.//channel'):
                channel_id = channel_elem.get('id')
                if not channel_id:
                    continue
                
                # Initialize channel
                epg_data[channel_id] = []
            
            # Parse programs
            for program_elem in root.findall('.//programme'):
                channel_id = program_elem.get('channel')
                if not channel_id or channel_id not in epg_data:
                    continue
                
                # Parse program
                start_time = self._parse_xmltv_time(program_elem.get('start', ''))
                stop_time = self._parse_xmltv_time(program_elem.get('stop', ''))
                
                if not start_time or not stop_time:
                    continue
                
                title_elem = program_elem.find('title')
                title = title_elem.text if title_elem is not None else 'Unknown'
                
                desc_elem = program_elem.find('desc')
                description = desc_elem.text if desc_elem is not None else ''
                
                # Create program object
                program = {
                    'id': f"{source_id}_{channel_id}_{start_time}",
                    'title': title,
                    'description': description,
                    'start_time': start_time,
                    'end_time': stop_time,
                    'duration': stop_time - start_time
                }
                
                # Add program to channel
                epg_data[channel_id].append(program)
            
            # Sort programs by start time
            for channel_id in epg_data:
                epg_data[channel_id].sort(key=lambda x: x['start_time'])
            
            # Update EPG data
            self.epg_data[source_id] = epg_data
        
        except Exception as e:
            logger.error(f"Error parsing XMLTV content: {str(e)}")
    
    def _parse_xmltv_time(self, time_str: str) -> Optional[int]:
        """
        Parse XMLTV time string to timestamp.
        
        Args:
            time_str (str): XMLTV time string (YYYYMMDDHHMMSS +0000)
            
        Returns:
            Optional[int]: Timestamp or None if parsing failed
        """
        try:
            # Remove timezone
            time_str = time_str.split(' ')[0]
            
            # Parse datetime
            dt = datetime.strptime(time_str, '%Y%m%d%H%M%S')
            
            # Convert to timestamp
            return int(dt.timestamp())
        
        except Exception as e:
            logger.error(f"Error parsing XMLTV time: {str(e)}")
            return None
    
    def add_source(self, name: str, source_type: str, url: str, 
                  update_interval: int = 24 * 3600) -> str:
        """
        Add a new EPG source.
        
        Args:
            name (str): Source name
            source_type (str): Source type ('xmltv' or 'provider')
            url (str): Source URL or path
            update_interval (int): Update interval in seconds
            
        Returns:
            str: Source ID
        """
        with self.lock:
            # Generate source ID
            source_id = name.lower().replace(' ', '_')
            
            # Check if the source already exists
            if source_id in self.sources:
                # Update existing source
                self.sources[source_id].update({
                    'name': name,
                    'type': source_type,
                    'url': url,
                    'update_interval': update_interval
                })
            else:
                # Add new source
                self.sources[source_id] = {
                    'name': name,
                    'type': source_type,
                    'url': url,
                    'update_interval': update_interval,
                    'last_update': 0
                }
            
            # Initialize EPG data
            if source_id not in self.epg_data:
                self.epg_data[source_id] = {}
            
            # Save configuration
            self._save_config()
            
            # Trigger immediate update
            threading.Thread(target=self._update_epg_data, args=(source_id,)).start()
            
            logger.info(f"Added EPG source: {name} ({source_id})")
            return source_id
    
    def update_source(self, source_id: str, name: Optional[str] = None, 
                     url: Optional[str] = None, update_interval: Optional[int] = None) -> bool:
        """
        Update an EPG source.
        
        Args:
            source_id (str): Source ID
            name (Optional[str]): New source name
            url (Optional[str]): New source URL
            update_interval (Optional[int]): New update interval
            
        Returns:
            bool: True if the source was updated, False otherwise
        """
        with self.lock:
            # Check if the source exists
            if source_id not in self.sources:
                logger.error(f"Source not found: {source_id}")
                return False
            
            # Update source
            if name is not None:
                self.sources[source_id]['name'] = name
            
            if url is not None:
                self.sources[source_id]['url'] = url
            
            if update_interval is not None:
                self.sources[source_id]['update_interval'] = update_interval
            
            # Save configuration
            self._save_config()
            
            logger.info(f"Updated EPG source: {source_id}")
            return True
    
    def delete_source(self, source_id: str) -> bool:
        """
        Delete an EPG source.
        
        Args:
            source_id (str): Source ID
            
        Returns:
            bool: True if the source was deleted, False otherwise
        """
        with self.lock:
            # Check if the source exists
            if source_id not in self.sources:
                logger.error(f"Source not found: {source_id}")
                return False
            
            # Delete source
            del self.sources[source_id]
            
            # Delete EPG data
            if source_id in self.epg_data:
                del self.epg_data[source_id]
            
            # Delete channel mappings for this source
            for mapping_key in list(self.channel_mappings.keys()):
                if mapping_key[0] == source_id:
                    del self.channel_mappings[mapping_key]
            
            # Delete EPG data file
            epg_file = os.path.join(self.data_dir, f"epg_{source_id}.json")
            if os.path.exists(epg_file):
                try:
                    os.remove(epg_file)
                except Exception as e:
                    logger.error(f"Error deleting EPG data file: {str(e)}")
            
            # Save configuration
            self._save_config()
            
            logger.info(f"Deleted EPG source: {source_id}")
            return True
    
    def map_channel(self, source_id: str, source_channel_id: str, target_channel_id: str) -> bool:
        """
        Map a source channel to a target channel.
        
        Args:
            source_id (str): Source ID
            source_channel_id (str): Source channel ID
            target_channel_id (str): Target channel ID
            
        Returns:
            bool: True if the channel was mapped, False otherwise
        """
        with self.lock:
            # Check if the source exists
            if source_id not in self.sources:
                logger.error(f"Source not found: {source_id}")
                return False
            
            # Add mapping
            self.channel_mappings[(source_id, source_channel_id)] = target_channel_id
            
            # Save configuration
            self._save_config()
            
            logger.debug(f"Mapped channel {source_channel_id} from source {source_id} to {target_channel_id}")
            return True
    
    def unmap_channel(self, source_id: str, source_channel_id: str) -> bool:
        """
        Remove a channel mapping.
        
        Args:
            source_id (str): Source ID
            source_channel_id (str): Source channel ID
            
        Returns:
            bool: True if the mapping was removed, False otherwise
        """
        with self.lock:
            # Check if the mapping exists
            if (source_id, source_channel_id) not in self.channel_mappings:
                logger.error(f"Channel mapping not found: {source_id} / {source_channel_id}")
                return False
            
            # Remove mapping
            del self.channel_mappings[(source_id, source_channel_id)]
            
            # Save configuration
            self._save_config()
            
            logger.debug(f"Unmapped channel {source_channel_id} from source {source_id}")
            return True
    
    def get_epg(self, channel_id: str, start_time: Optional[int] = None, 
               end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get EPG data for a channel.
        
        Args:
            channel_id (str): Channel ID
            start_time (Optional[int]): Start time timestamp, or None for current time
            end_time (Optional[int]): End time timestamp, or None for 24 hours from start
            
        Returns:
            List[Dict[str, Any]]: List of EPG programs for the channel
        """
        with self.lock:
            # Set default time range
            if start_time is None:
                start_time = int(time.time())
            
            if end_time is None:
                end_time = start_time + 24 * 3600
            
            # Find mappings for this channel
            programs = []
            
            # Check direct mappings
            for (source_id, source_channel_id), target_channel_id in self.channel_mappings.items():
                if target_channel_id == channel_id:
                    # Found a mapping, get EPG data
                    if source_id in self.epg_data and source_channel_id in self.epg_data[source_id]:
                        # Filter programs by time range
                        for program in self.epg_data[source_id][source_channel_id]:
                            if program['end_time'] > start_time and program['start_time'] < end_time:
                                programs.append(program)
            
            # Sort programs by start time
            programs.sort(key=lambda x: x['start_time'])
            
            return programs
    
    def get_epg_for_channel_name(self, channel_name: str, start_time: Optional[int] = None,
                              end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get EPG data for a channel by name.
        Uses fuzzy matching to find the best source channel.
        
        Args:
            channel_name (str): Channel name
            start_time (Optional[int]): Start time timestamp, or None for current time
            end_time (Optional[int]): End time timestamp, or None for 24 hours from start
            
        Returns:
            List[Dict[str, Any]]: List of EPG programs for the channel
        """
        # This could be enhanced with actual fuzzy matching
        # For now, we just do a case-insensitive substring match
        channel_name_lower = channel_name.lower()
        
        best_match = None
        best_match_source_id = None
        best_match_channel_id = None
        
        with self.lock:
            # Find the best match
            for source_id, source_data in self.epg_data.items():
                for source_channel_id in source_data:
                    # Try to find matching channel name
                    # This is a placeholder - real implementation would be more sophisticated
                    if channel_name_lower in source_channel_id.lower():
                        best_match_source_id = source_id
                        best_match_channel_id = source_channel_id
                        best_match = source_data[source_channel_id]
                        break
            
            if best_match:
                # Set default time range
                if start_time is None:
                    start_time = int(time.time())
                
                if end_time is None:
                    end_time = start_time + 24 * 3600
                
                # Filter programs by time range
                programs = []
                for program in best_match:
                    if program['end_time'] > start_time and program['start_time'] < end_time:
                        programs.append(program)
                
                # Sort programs by start time
                programs.sort(key=lambda x: x['start_time'])
                
                return programs
            
            return []
    
    def get_all_sources(self) -> List[Dict[str, Any]]:
        """
        Get all EPG sources.
        
        Returns:
            List[Dict[str, Any]]: List of sources
        """
        with self.lock:
            return [
                {
                    'id': source_id,
                    'name': source['name'],
                    'type': source['type'],
                    'url': source['url'],
                    'update_interval': source['update_interval'],
                    'last_update': source['last_update'],
                    'channel_count': len(self.epg_data.get(source_id, {}))
                }
                for source_id, source in self.sources.items()
            ]
    
    def get_source_channels(self, source_id: str) -> List[str]:
        """
        Get all channels for a source.
        
        Args:
            source_id (str): Source ID
            
        Returns:
            List[str]: List of channel IDs
        """
        with self.lock:
            if source_id not in self.epg_data:
                return []
            
            return list(self.epg_data[source_id].keys())
    
    def get_all_channel_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Get all channel mappings.
        
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of mappings
        """
        with self.lock:
            # Group mappings by source ID
            mappings = {}
            
            for (source_id, source_channel_id), target_channel_id in self.channel_mappings.items():
                if source_id not in mappings:
                    mappings[source_id] = {}
                
                mappings[source_id][source_channel_id] = target_channel_id
            
            return mappings
    
    def update_now(self, source_id: Optional[str] = None) -> None:
        """
        Trigger an immediate update of EPG data.
        
        Args:
            source_id (Optional[str]): Source ID, or None for all sources
        """
        with self.lock:
            if source_id:
                # Update specific source
                if source_id in self.sources:
                    threading.Thread(target=self._update_epg_data, args=(source_id,)).start()
                else:
                    logger.error(f"Source not found: {source_id}")
            else:
                # Update all sources
                for source_id in self.sources:
                    threading.Thread(target=self._update_epg_data, args=(source_id,)).start()
    
    def get_current_program(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current program for a channel.
        
        Args:
            channel_id (str): Channel ID or mapping key (portal_id:channel_id)
            
        Returns:
            Optional[Dict[str, Any]]: Program information or None if not found
        """
        try:
            now = int(time.time())
            
            # Check if we have EPG data for this channel
            for source_id, source_data in self.epg_data.items():
                # First check if the channel ID is directly in our data
                if channel_id in source_data:
                    programs = source_data[channel_id]
                else:
                    # Check if we have a mapping for this channel
                    mapped_channel = self.channel_mappings.get(channel_id)
                    if not mapped_channel:
                        continue
                    
                    # Check if we have data for the mapped channel
                    if mapped_channel not in source_data:
                        continue
                    
                    programs = source_data[mapped_channel]
                
                # Find current program
                for program in programs:
                    start_time = program.get('start_time', 0)
                    end_time = program.get('end_time', 0)
                    
                    if start_time <= now < end_time:
                        return program
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting current program for channel {channel_id}: {str(e)}")
            return None
    
    def get_mappings(self) -> Dict[str, str]:
        """
        Get all channel mappings.
        
        Returns:
            Dict[str, str]: Channel mappings
        """
        return self.channel_mappings.copy()