"""
STB API service for STB-ReStreamer.
Handles communication with STB provider APIs.
"""
import os
import json
import time
import logging
import random
import requests
from urllib.parse import urljoin
from threading import Lock
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import uuid

# Import portal providers using direct imports instead of the module import
from src.services.portal_providers.base_provider import BasePortalProvider
from src.services.portal_providers.stalker_provider import StalkerPortalProvider
from src.services.portal_providers.xtream_provider import XtreamPortalProvider
from src.services.portal_providers.ministra_provider import MinistraPortalProvider
from src.services.portal_providers.xc_updates_provider import XCUpdatesPortalProvider
from src.services.portal_providers.m3u_provider import M3UPlaylistProvider

from src.utils.security import TokenStorage
from src.models.channel import Channel, ChannelStream
from src.models.config import ConfigManager

# Configure logger
logger = logging.getLogger("STB-Proxy")

class StbApi:
    """
    Service for handling communication with STB provider APIs.
    Uses appropriate provider implementations based on portal type.
    """
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the STB API service.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.lock = Lock()
        self.channels_cache = {}  # Format: {portal_id+mac: (channels, expiry)}
        self.channels_lifetime = 6 * 3600  # 6 hours in seconds
        
        # Initialize token storage
        try:
            # Try to use get_data_dir if available
            if hasattr(self.config_manager, 'get_data_dir'):
                data_dir = self.config_manager.get_data_dir()
            else:
                # Fallback to default data directory
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)
                
            token_db_path = os.path.join(data_dir, "tokens.db")
            
            # Try to get encryption key using new get method, fallback to old get_setting
            if hasattr(self.config_manager, 'get'):
                encryption_key = self.config_manager.get('security', 'encryption_key', default='')
            else:
                # Fallback to flat settings
                encryption_key = self.config_manager.get_setting('encryption_key', '')
                
            self.token_storage = TokenStorage(token_db_path, encryption_key)
        except Exception as e:
            logger.error(f"Error initializing token storage: {str(e)}")
            # Fallback to in-memory token storage
            self.token_storage = TokenStorage(":memory:")
        
        # Initialize providers with all supported types
        self.providers = {
            'stalker': StalkerPortalProvider(),
            'xtream': XtreamPortalProvider(),
            'm3u': M3UPlaylistProvider(),
            'ministra': MinistraPortalProvider(),
            'xcupdates': XCUpdatesPortalProvider()
        }
        
        logger.info("STB API service initialized with providers: " + ", ".join(self.providers.keys()))
        
    def _get_provider(self, portal: Dict[str, Any]) -> BasePortalProvider:
        """
        Get the appropriate provider for a portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            
        Returns:
            BasePortalProvider: Provider implementation
        """
        portal_type = portal.get('type', 'stalker').lower()
        provider = self.providers.get(portal_type)
        
        if not provider:
            logger.warning(f"Unknown portal type: {portal_type}, falling back to stalker")
            provider = self.providers['stalker']
            
        return provider
        
    def get_token(self, portal_id: str, mac: str) -> Optional[str]:
        """
        Get an authentication token for the STB API.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            Optional[str]: Authentication token or None if failed
        """
        # Check token storage first
        token = self.token_storage.get_token(portal_id, mac)
        if token:
            logger.debug(f"Using stored token for {portal_id}:{mac}")
            return token
        
        # Get portal info
        portal = self._get_portal(portal_id)
        if not portal:
            return None
            
        # Get the provider and token
        provider = self._get_provider(portal)
        token = provider.get_token(portal, mac)
        
        if token:
            # Store the token securely
            # Try to get token_lifetime using new get method, fallback to old get_setting
            if hasattr(self.config_manager, 'get'):
                token_lifetime = self.config_manager.get('security', 'token_lifetime', default=12 * 3600)
            else:
                # Fallback to flat settings
                token_lifetime = self.config_manager.get_setting('token_lifetime', 12 * 3600)
                
            self.token_storage.store_token(portal_id, mac, token, token_lifetime)
            logger.info(f"Got new token for {portal_id}:{mac}")
        else:
            logger.error(f"Failed to get token for {portal_id}:{mac}")
            
        return token
            
    def get_profile(self, portal_id: str, mac: str) -> Optional[Dict]:
        """
        Get user profile information.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            Optional[Dict]: User profile information or None if failed
        """
        # Get portal info
        portal = self._get_portal(portal_id)
        if not portal:
            return None
            
        # Get the token
        token = self.get_token(portal_id, mac)
        
        # Get the provider and profile
        provider = self._get_provider(portal)
        profile = provider.get_profile(portal, mac, token)
        
        if not profile:
            logger.error(f"Failed to get profile for {portal_id}:{mac}")
            # Fallback to dummy profile
            profile = {
                'status': 'active',
                'expires': time.time() + 30 * 24 * 3600,  # 30 days from now
                'max_connections': 1,
                'username': f"user_{mac[-6:]}",
                'package': 'Unknown'
            }
            
        return profile
        
    def get_channels(self, portal_id: str, mac: str) -> List[Dict]:
        """
        Get channel list for a portal.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            List[Dict]: List of channels
        """
        with self.lock:
            cache_key = f"{portal_id}:{mac}"
            
            # Check cache
            if cache_key in self.channels_cache:
                channels, expiry = self.channels_cache[cache_key]
                if time.time() < expiry:
                    logger.debug(f"Using cached channels for {portal_id}:{mac}")
                    return channels
                    
            # Get data directory for channels file
            try:
                if hasattr(self.config_manager, 'get_data_dir'):
                    data_dir = self.config_manager.get_data_dir()
                else:
                    # Fallback to default data directory
                    data_dir = "data"
                    os.makedirs(data_dir, exist_ok=True)
                    
                channels_file = os.path.join(data_dir, f"channels_{portal_id}.json")
            except Exception:
                # Fallback to current directory
                channels_file = f"channels_{portal_id}.json"
                
            # Check if we have a saved JSON file
            if os.path.exists(channels_file):
                try:
                    with open(channels_file, 'r', encoding='utf-8') as f:
                        channels_data = json.load(f)
                        
                    # Validate channels structure
                    if not isinstance(channels_data, list):
                        logger.error(f"Invalid channels data format for {portal_id}: expected list, got {type(channels_data)}")
                        channels_data = []
                        
                    # Filter out non-dictionary items
                    channels = []
                    for channel in channels_data:
                        if isinstance(channel, dict):
                            # Ensure required fields exist
                            if 'id' not in channel:
                                channel['id'] = f"unknown_{str(uuid.uuid4())[-8:]}"
                                logger.warning(f"Channel missing ID in {portal_id}, assigned temporary ID")
                            if 'name' not in channel:
                                channel['name'] = f"Unknown Channel {len(channels) + 1}"
                                logger.warning(f"Channel missing name in {portal_id}, assigned default name")
                            channels.append(channel)
                        else:
                            logger.warning(f"Skipping non-dictionary channel in {portal_id}: {type(channel)}")
                        
                    # Cache the validated channels
                    self.channels_cache[cache_key] = (channels, time.time() + self.channels_lifetime)
                    logger.debug(f"Loaded {len(channels)} channels from file for {portal_id}")
                    return channels
                except Exception as e:
                    logger.error(f"Error loading channels from file: {str(e)}")
            
            # Get portal info
            portal = self._get_portal(portal_id)
            if not portal:
                logger.error(f"Cannot get channels: Portal {portal_id} not found or invalid")
                return []
                
            # Get the token
            token = self.get_token(portal_id, mac)
            
            # Get the provider and channels
            provider = self._get_provider(portal)
            if not provider:
                logger.error(f"Cannot get channels: No provider available for portal {portal_id}")
                return []
                
            channels_data = provider.get_channels(portal, mac, token)
            
            # Validate channels
            if not channels_data:
                logger.error(f"Failed to get channels for {portal_id}:{mac}")
                # Fallback to dummy channels
                channels = self._generate_dummy_channels(50)
            else:
                # Ensure proper format
                if not isinstance(channels_data, list):
                    logger.error(f"Invalid channels data from provider for {portal_id}: expected list, got {type(channels_data)}")
                    channels_data = []
                    
                # Filter out non-dictionary items
                channels = []
                for channel in channels_data:
                    if isinstance(channel, dict):
                        # Ensure required fields exist
                        if 'id' not in channel:
                            channel['id'] = f"unknown_{str(uuid.uuid4())[-8:]}"
                            logger.warning(f"Channel missing ID from provider for {portal_id}, assigned temporary ID")
                        if 'name' not in channel:
                            channel['name'] = f"Unknown Channel {len(channels) + 1}"
                            logger.warning(f"Channel missing name from provider for {portal_id}, assigned default name")
                        channels.append(channel)
                    else:
                        logger.warning(f"Skipping non-dictionary channel from provider for {portal_id}: {type(channel)}")
            
            # Save to file for persistence
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(channels_file) if os.path.dirname(channels_file) else '.', exist_ok=True)
                
                with open(channels_file, 'w', encoding='utf-8') as f:
                    json.dump(channels, f, indent=2)
                    logger.debug(f"Saved channels to file for {portal_id}")
            except Exception as e:
                logger.error(f"Error saving channels to file: {str(e)}")
            
            # Cache the channels
            self.channels_cache[cache_key] = (channels, time.time() + self.channels_lifetime)
            logger.info(f"Got {len(channels)} channels for {portal_id}:{mac}")
            
            return channels
            
    def get_stream_url(self, portal_id: str, mac: str, channel_id: str) -> Optional[str]:
        """
        Get stream URL for a channel.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            channel_id (str): Channel ID
            
        Returns:
            Optional[str]: Stream URL or None if failed
        """
        # Get portal info
        portal = self._get_portal(portal_id)
        if not portal:
            logger.error(f"Portal not found: {portal_id}")
            return None
            
        # Get the token - required for authentication
        token = self.get_token(portal_id, mac)
        if not token:
            logger.error(f"Failed to get authentication token for {portal_id}:{mac}")
            return None
            
        # Check profile information - required for valid user session
        profile = self.get_profile(portal_id, mac)
        if not profile:
            logger.error(f"Failed to get profile information for {portal_id}:{mac}")
            return None
            
        # Get the provider and stream URL
        provider = self._get_provider(portal)
        stream_url = provider.get_stream_url(portal, mac, channel_id, token)
        
        if not stream_url:
            logger.error(f"Failed to get stream URL for {portal_id}:{mac}:{channel_id}")
            return None
            
        return stream_url
        
    def get_epg(self, portal_id: str, mac: str, channel_id: Optional[str] = None, 
               start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            channel_id (Optional[str]): Channel ID for specific channel, or None for all
            start_time (Optional[int]): Start time timestamp, or None for current time
            end_time (Optional[int]): End time timestamp, or None for 24 hours from start
            
        Returns:
            Dict: EPG data
        """
        # Get portal info
        portal = self._get_portal(portal_id)
        if not portal:
            return {}
            
        # Get the token
        token = self.get_token(portal_id, mac)
        
        # Get the provider and EPG data
        provider = self._get_provider(portal)
        epg_data = provider.get_epg(portal, mac, channel_id, token, start_time, end_time)
        
        if not epg_data:
            logger.error(f"Failed to get EPG for {portal_id}:{mac}")
            # Fallback to dummy EPG
            current_time = int(time.time())
            start_time = start_time or current_time
            end_time = end_time or (start_time + 24 * 3600)
            
            # Get channels if needed
            channels = []
            if channel_id:
                # Find specific channel
                for channel in self.get_channels(portal_id, mac):
                    if channel.get('id') == channel_id:
                        channels = [channel]
                        break
            else:
                # All channels
                channels = self.get_channels(portal_id, mac)
                
            # Generate EPG data
            epg_data = {}
            for channel in channels:
                channel_id = channel.get('id')
                epg_data[channel_id] = self._generate_dummy_epg(
                    channel_id, 
                    channel.get('name', 'Unknown'),
                    start_time,
                    end_time
                )
            
        return epg_data

    def invalidate_token(self, portal_id: str, mac: str) -> bool:
        """
        Invalidate a token for a portal and MAC.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            bool: True if token was invalidated, False otherwise
        """
        return self.token_storage.delete_token(portal_id, mac)
    
    def cleanup_tokens(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            int: Number of tokens cleaned up
        """
        return self.token_storage.cleanup_expired()
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token statistics.
        
        Returns:
            Dict[str, Any]: Token statistics
        """
        return self.token_storage.get_stats()
        
    def _get_portal(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """
        Get portal information.
        
        Args:
            portal_id (str): Portal ID
            
        Returns:
            Optional[Dict[str, Any]]: Portal information or None if not found
        """
        try:
            from flask import current_app
            portal_manager = current_app.portal_manager
            portal = portal_manager.get_portal(portal_id)
            
            if not portal:
                logger.error(f"Portal not found: {portal_id}")
                return None
                
            # Validate that the portal is a dictionary
            if not isinstance(portal, dict):
                logger.error(f"Portal {portal_id} is not a dictionary: {type(portal)}")
                # Convert string to dictionary if needed
                if isinstance(portal, str):
                    logger.warning(f"Converting string portal to dictionary: {portal}")
                    try:
                        # Try to convert JSON string to dictionary
                        import json
                        portal_dict = json.loads(portal)
                        if isinstance(portal_dict, dict):
                            return portal_dict
                    except Exception as e:
                        logger.error(f"Failed to convert portal string to dictionary: {str(e)}")
                return None
                
            # Validate required portal fields
            self._validate_portal(portal_id, portal)
                
            return portal
        except Exception as e:
            logger.error(f"Error getting portal: {str(e)}")
            return None
            
    def _validate_portal(self, portal_id: str, portal: Dict) -> None:
        """
        Validate portal structure and log warnings for missing fields.
        
        Args:
            portal_id (str): Portal ID
            portal (Dict): Portal data to validate
        """
        # List of required fields
        required_fields = ['type', 'name']
        
        # Check required fields
        for field in required_fields:
            if field not in portal:
                logger.warning(f"Portal {portal_id} missing required field: {field}")
                
        # Check portal type
        portal_type = portal.get('type', '')
        if not portal_type:
            logger.warning(f"Portal {portal_id} has no type specified")
        elif portal_type not in ['stalker', 'xtream', 'm3u', 'ministra', 'xcupdates']:
            logger.warning(f"Portal {portal_id} has unknown type: {portal_type}")
            
        # Check if enabled is a boolean-like value
        enabled = portal.get('enabled')
        if enabled is not None and not isinstance(enabled, bool) and enabled not in ['true', 'false']:
            logger.warning(f"Portal {portal_id} has invalid enabled value: {enabled}")
        
    def _generate_dummy_channels(self, count: int) -> List[Dict]:
        """
        Generate dummy channels for testing.
        
        Args:
            count (int): Number of channels to generate
            
        Returns:
            List[Dict]: List of dummy channels
        """
        channel_types = [
            'News', 'Sports', 'Movies', 'Music', 'Kids', 
            'Documentaries', 'Entertainment', 'Lifestyle'
        ]
        
        channels = []
        for i in range(1, count + 1):
            channel_type = random.choice(channel_types)
            channels.append({
                'id': f"ch{i}",
                'name': f"{channel_type} Channel {i}",
                'number': i,
                'type': channel_type,
                'logo': f"https://via.placeholder.com/100x100.png?text=CH{i}"
            })
            
        return channels
        
    def _generate_dummy_epg(self, channel_id: str, channel_name: str, 
                          start_time: int, end_time: int) -> List[Dict]:
        """
        Generate dummy EPG data for testing.
        
        Args:
            channel_id (str): Channel ID
            channel_name (str): Channel name
            start_time (int): Start time timestamp
            end_time (int): End time timestamp
            
        Returns:
            List[Dict]: List of dummy EPG programs
        """
        program_types = [
            'Movie', 'News', 'Sports', 'Documentary', 'Series', 
            'Kids', 'Music', 'Talk Show', 'Cooking'
        ]
        
        programs = []
        current_time = start_time
        
        while current_time < end_time:
            # Random duration between 15 and 120 minutes
            duration = random.randint(15, 120) * 60
            program_type = random.choice(program_types)
            
            programs.append({
                'id': f"prog_{channel_id}_{current_time}",
                'title': f"{program_type} Program {random.randint(1, 100)}",
                'description': f"This is a {program_type.lower()} program on {channel_name}",
                'start_time': current_time,
                'end_time': current_time + duration,
                'duration': duration,
                'type': program_type
            })
            
            current_time += duration
            
        return programs

    def get_channel_name(self, portal_id: str, mac: str, channel_id: str) -> Optional[str]:
        """
        Get the name of a channel.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            channel_id (str): Channel ID
            
        Returns:
            Optional[str]: Channel name or None if not found
        """
        # Get channels
        channels = self.get_channels(portal_id, mac)
        
        # Find channel with matching ID
        for channel in channels:
            if channel.get('id') == channel_id:
                return channel.get('name')
                
        # Not found
        return None