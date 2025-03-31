"""
Xtream Codes provider for STB-ReStreamer.
Implements Xtream Codes API v2.
"""
import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple

# Configure logger
logger = logging.getLogger("STB-Proxy")

from src.services.portal_providers.base_provider import BasePortalProvider

class XtreamPortalProvider(BasePortalProvider):
    """
    Provider for Xtream Codes API.
    Implements methods to communicate with Xtream Codes servers.
    """
    
    def __init__(self):
        """Initialize the Xtream Codes provider."""
        self.http_timeout = 10  # HTTP request timeout in seconds
    
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get an authentication token from Xtream Codes.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            
        Returns:
            Optional[str]: Authentication token or None if failed
        """
        try:
            # Extract credentials
            username = portal.get('username')
            password = portal.get('password')
            
            if not username or not password:
                logger.error("Missing Xtream credentials in portal configuration")
                return None
                
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return None
                
            # Xtream uses username:password as the token
            # We'll store it in a format that is easily retrievable
            token = f"{username}:{password}"
            return token
            
        except Exception as e:
            logger.error(f"Error getting token from Xtream Codes: {str(e)}")
            return None
            
    def _build_api_url(self, portal: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """
        Build the Xtream API URL from portal configuration.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            
        Returns:
            Optional[Tuple[str, str, str]]: Tuple of (base_url, username, password) or None if failed
        """
        # Extract credentials
        username = portal.get('username')
        password = portal.get('password')
        
        if not username or not password:
            logger.error("Missing Xtream credentials in portal configuration")
            return None
            
        # Build the URL
        base_url = portal.get('url', '').rstrip('/')
        if not base_url:
            logger.error("Portal URL is empty")
            return None
            
        return (base_url, username, password)
    
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> Optional[Dict]:
        """
        Get user profile information from Xtream Codes.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[Dict]: User profile information or None if failed
        """
        try:
            # Build API URL
            url_data = self._build_api_url(portal)
            if not url_data:
                return None
                
            base_url, username, password = url_data
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Build user info URL
            user_info_url = f"{base_url}/player_api.php?username={username}&password={password}&action=user"
            
            # Make request
            response = requests.get(
                user_info_url,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get profile failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if not data.get('user_info'):
                    logger.error(f"Profile response missing data: {data}")
                    return None
                    
                # Extract profile info
                user_info = data['user_info']
                
                # Format the response
                profile = {
                    'status': 'active' if user_info.get('status') == 'Active' else 'inactive',
                    'expires': int(user_info.get('exp_date', 0)),
                    'max_connections': int(user_info.get('max_connections', 1)),
                    'username': user_info.get('username', username),
                    'package': user_info.get('package', '')
                }
                
                return profile
                
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing profile response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting profile from Xtream Codes: {str(e)}")
            return None
            
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> List[Dict]:
        """
        Get channel list from Xtream Codes.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            List[Dict]: List of channels
        """
        try:
            # Build API URL
            url_data = self._build_api_url(portal)
            if not url_data:
                return []
                
            base_url, username, password = url_data
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Build channel list URL
            channels_url = f"{base_url}/player_api.php?username={username}&password={password}&action=get_live_streams"
            
            # Make request
            response = requests.get(
                channels_url,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get channels failed with status code {response.status_code}")
                return []
                
            # Parse response
            try:
                channels_data = response.json()
                if not isinstance(channels_data, list):
                    logger.error(f"Channels response is not a list: {channels_data}")
                    return []
                    
                # Format channels
                channels = []
                for channel in channels_data:
                    # Format channel
                    channels.append({
                        'id': str(channel.get('stream_id', '')),
                        'name': channel.get('name', 'Unknown'),
                        'number': int(channel.get('num', 0) or 0),
                        'type': channel.get('category_id', ''),
                        'logo': channel.get('stream_icon', '')
                    })
                
                logger.info(f"Retrieved {len(channels)} channels from Xtream Codes")
                return channels
                
            except ValueError as e:
                logger.error(f"Error parsing channels response: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting channels from Xtream Codes: {str(e)}")
            return []
            
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str] = None) -> Optional[str]:
        """
        Get stream URL for a channel from Xtream Codes.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            channel_id (str): Channel ID
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[str]: Stream URL or None if failed
        """
        try:
            # Build API URL
            url_data = self._build_api_url(portal)
            if not url_data:
                return None
                
            base_url, username, password = url_data
            
            # Build stream URL
            stream_url = f"{base_url}/live/{username}/{password}/{channel_id}.ts"
            
            logger.info(f"Generated stream URL for channel {channel_id}")
            return stream_url
                
        except Exception as e:
            logger.error(f"Error getting stream URL from Xtream Codes: {str(e)}")
            return None
            
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str] = None, 
                token: Optional[str] = None, start_time: Optional[int] = None, 
                end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data from Xtream Codes.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            channel_id (Optional[str]): Channel ID for specific channel, or None for all
            token (Optional[str]): Authentication token
            start_time (Optional[int]): Start time timestamp, or None for current time
            end_time (Optional[int]): End time timestamp, or None for 24 hours from start
            
        Returns:
            Dict: EPG data
        """
        try:
            # Build API URL
            url_data = self._build_api_url(portal)
            if not url_data:
                return {}
                
            base_url, username, password = url_data
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Set default time range
            current_time = int(time.time())
            start_time = start_time or current_time
            end_time = end_time or (start_time + 24 * 3600)
            
            # Build EPG URL
            epg_url = f"{base_url}/player_api.php?username={username}&password={password}&action=get_simple_data_table"
            
            # If channel_id is provided, get EPG for that channel only
            if channel_id:
                epg_url += f"&stream_id={channel_id}"
                
            # Make request
            response = requests.get(
                epg_url,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get EPG failed with status code {response.status_code}")
                return {}
                
            # Parse response
            try:
                data = response.json()
                if not isinstance(data, dict):
                    logger.error(f"EPG response is not a dictionary: {data}")
                    return {}
                    
                # Format EPG data
                epg_data = {}
                for channel_id, epg_items in data.items():
                    if not isinstance(epg_items, list):
                        continue
                        
                    epg_list = []
                    for item in epg_items:
                        # Parse timestamps
                        try:
                            start = int(item.get('start', 0))
                            end = int(item.get('end', 0))
                        except (ValueError, TypeError):
                            continue
                            
                        # Skip items outside time range
                        if end < start_time or start > end_time:
                            continue
                            
                        epg_list.append({
                            'id': f"epg_{channel_id}_{start}",
                            'title': item.get('title', 'Unknown'),
                            'description': item.get('description', ''),
                            'start_time': start,
                            'end_time': end,
                            'duration': end - start,
                            'category': item.get('category', '')
                        })
                    
                    if epg_list:
                        epg_data[channel_id] = epg_list
                
                logger.info(f"Retrieved EPG data for {len(epg_data)} channels")
                return epg_data
                
            except ValueError as e:
                logger.error(f"Error parsing EPG response: {str(e)}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting EPG from Xtream Codes: {str(e)}")
            return {}