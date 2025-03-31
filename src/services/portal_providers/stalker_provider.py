"""
Stalker Portal provider for STB-ReStreamer.
Implements Stalker Portal API.
"""
import os
import json
import time
import logging
import requests
from urllib.parse import urljoin, quote
from typing import Dict, List, Any, Optional, Tuple

from src.services.portal_providers.base_provider import BasePortalProvider

# Configure logger
logger = logging.getLogger("STB-Proxy")

class StalkerPortalProvider(BasePortalProvider):
    """
    Provider for Stalker Portal API.
    Implements methods to communicate with Stalker Middleware.
    """
    
    def __init__(self):
        """Initialize the Stalker Portal provider."""
        self.http_timeout = 10  # HTTP request timeout in seconds
    
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get an authentication token from Stalker Portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            
        Returns:
            Optional[str]: Authentication token or None if failed
        """
        try:
            # Format the MAC address for Stalker (remove colons)
            mac_formatted = mac.replace(':', '').lower()
            
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return None
                
            # Stalker portal auth URL
            auth_url = f"{base_url}/stalker_portal/server/load.php"
            
            # Build user agent and headers
            user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            
            # Initial headers
            headers = {
                'User-Agent': user_agent,
                'X-User-Agent': user_agent,
                'Cookie': ""
            }
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Step 1: Handshake
            params = {
                'type': 'stb',
                'action': 'handshake',
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(
                auth_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Handshake failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if 'js' not in data or not data['js'].get('token'):
                    logger.error(f"Handshake response missing token: {data}")
                    return None
                    
                # Get the token and update headers
                token = data['js']['token']
                
                # Get any cookies
                cookies = response.headers.get('Set-Cookie', '')
                headers['Cookie'] = cookies
                headers['Authorization'] = f"Bearer {token}"
                
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing handshake response: {str(e)}")
                return None
                
            # Step 2: Send device info
            params = {
                'type': 'stb',
                'action': 'get_profile',
                'hd': '1',
                'ver': 'ImageDescription: 0.2.18-r14-pub-250; ImageDate: Fri Jan 15 15:20:44 EET 2016',
                'num_banks': '1',
                'stb_type': 'MAG250',
                'client_type': 'STB',
                'image_version': '218',
                'auth_second_step': '1',
                'hw_version': '1.7-BD-00',
                'not_valid_token': '0',
                'API_VERSION': '128',
                'JsHttpRequest': '1-xml'
            }
            
            if token:
                params['token'] = token
                
            response = requests.get(
                auth_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Device info request failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if not data.get('js'):
                    logger.error(f"Device info response missing data: {data}")
                    return None
                    
                # Update cookies
                cookies = response.headers.get('Set-Cookie', '')
                if cookies:
                    headers['Cookie'] = cookies
                    
            except ValueError as e:
                logger.error(f"Error parsing device info response: {str(e)}")
                return None
                
            # Step 3: Authenticate with MAC
            params = {
                'type': 'stb',
                'action': 'do_auth',
                'JsHttpRequest': '1-xml'
            }
            
            # Check if username/password are provided in the portal config
            if portal.get('username') and portal.get('password'):
                # Use username/password authentication
                params['login'] = portal.get('username')
                params['password'] = portal.get('password')
                params['device_id'] = mac_formatted
                params['device_id2'] = mac_formatted
                logger.info(f"Using username/password authentication for MAC {mac_formatted}")
            else:
                # Fallback to MAC-only authentication
                params['login'] = mac_formatted
                params['password'] = ''
                params['device_id'] = ''
                params['device_id2'] = ''
                logger.info(f"Using MAC-only authentication for {mac_formatted}")
            
            if token:
                params['token'] = token
                
            response = requests.get(
                auth_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Authentication failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if not data.get('js') or not data['js'].get('token'):
                    logger.error(f"Authentication response missing token: {data}")
                    return None
                    
                # Update token and cookies
                token = data['js']['token']
                cookies = response.headers.get('Set-Cookie', '')
                if cookies:
                    headers['Cookie'] = cookies
                    
                logger.info(f"Successfully authenticated with Stalker Portal for MAC {mac_formatted}")
                return token
                
            except ValueError as e:
                logger.error(f"Error parsing authentication response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting token from Stalker Portal: {str(e)}")
            return None
            
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> Optional[Dict]:
        """
        Get user profile information from Stalker Portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[Dict]: User profile information or None if failed
        """
        try:
            # Get token if not provided
            if not token:
                token = self.get_token(portal, mac)
                if not token:
                    return None
                    
            # Format the MAC address
            mac_formatted = mac.replace(':', '').lower()
            
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return None
                
            # Stalker portal API URL
            api_url = f"{base_url}/stalker_portal/server/load.php"
            
            # Build headers
            user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            headers = {
                'User-Agent': user_agent,
                'X-User-Agent': user_agent,
                'Authorization': f"Bearer {token}"
            }
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Get user profile
            params = {
                'type': 'account_info',
                'action': 'get_main_info',
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get profile failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if not data.get('js'):
                    logger.error(f"Profile response missing data: {data}")
                    return None
                    
                # Extract profile info
                profile_data = data['js']
                
                # Format the response
                profile = {
                    'status': 'active' if profile_data.get('status') == 1 else 'inactive',
                    'expires': profile_data.get('expire_date', 0),
                    'max_connections': profile_data.get('max_devices', 1),
                    'username': profile_data.get('login', mac_formatted),
                    'package': profile_data.get('tariff_plan', '')
                }
                
                return profile
                
            except ValueError as e:
                logger.error(f"Error parsing profile response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting profile from Stalker Portal: {str(e)}")
            return None
            
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> List[Dict]:
        """
        Get channel list from Stalker Portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            List[Dict]: List of channels
        """
        try:
            # Get token if not provided
            if not token:
                token = self.get_token(portal, mac)
                if not token:
                    return []
                    
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return []
                
            # Stalker portal API URL
            api_url = f"{base_url}/stalker_portal/server/load.php"
            
            # Build headers
            user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            headers = {
                'User-Agent': user_agent,
                'X-User-Agent': user_agent,
                'Authorization': f"Bearer {token}"
            }
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Get channel list
            params = {
                'type': 'itv',
                'action': 'get_all_channels',
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get channels failed with status code {response.status_code}")
                return []
                
            # Parse response
            try:
                data = response.json()
                if not data.get('js') or not data['js'].get('data'):
                    logger.error(f"Channels response missing data: {data}")
                    return []
                    
                # Extract channels
                channels_data = data['js']['data']
                
                # Format channels
                channels = []
                for channel in channels_data:
                    # Skip non-working channels
                    if channel.get('status') != 1:
                        continue
                        
                    # Format channel
                    channels.append({
                        'id': str(channel.get('id', '')),
                        'name': channel.get('name', 'Unknown'),
                        'number': int(channel.get('number', 0)),
                        'type': channel.get('tv_genre_id', ''),
                        'logo': channel.get('logo', '')
                    })
                
                logger.info(f"Retrieved {len(channels)} channels from Stalker Portal")
                return channels
                
            except ValueError as e:
                logger.error(f"Error parsing channels response: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting channels from Stalker Portal: {str(e)}")
            return []
            
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str] = None) -> Optional[str]:
        """
        Get stream URL for a channel from Stalker Portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            channel_id (str): Channel ID
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[str]: Stream URL or None if failed
        """
        try:
            # Get token if not provided
            if not token:
                token = self.get_token(portal, mac)
                if not token:
                    return None
                    
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return None
                
            # Stalker portal API URL
            api_url = f"{base_url}/stalker_portal/server/load.php"
            
            # Build headers
            user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            headers = {
                'User-Agent': user_agent,
                'X-User-Agent': user_agent,
                'Authorization': f"Bearer {token}"
            }
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Get stream URL
            params = {
                'type': 'itv',
                'action': 'create_link',
                'cmd': f'ffmpeg http://localhost/ch/{channel_id}_',
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=self.http_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Get stream URL failed with status code {response.status_code}")
                return None
                
            # Parse response
            try:
                data = response.json()
                if not data.get('js') or not data['js'].get('cmd'):
                    logger.error(f"Stream URL response missing data: {data}")
                    return None
                    
                # Extract stream URL
                stream_url = data['js']['cmd']
                
                # Clean up URL if needed
                if stream_url.startswith('ffmpeg '):
                    stream_url = stream_url[7:]
                    
                logger.info(f"Retrieved stream URL for channel {channel_id}")
                return stream_url
                
            except ValueError as e:
                logger.error(f"Error parsing stream URL response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting stream URL from Stalker Portal: {str(e)}")
            return None
            
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str] = None, 
                token: Optional[str] = None, start_time: Optional[int] = None, 
                end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data from Stalker Portal.
        
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
            # Get token if not provided
            if not token:
                token = self.get_token(portal, mac)
                if not token:
                    return {}
                    
            # Set default time range
            current_time = int(time.time())
            start_time = start_time or current_time
            end_time = end_time or (start_time + 24 * 3600)
            
            # Build the URL
            base_url = portal.get('url', '').rstrip('/')
            if not base_url:
                logger.error("Portal URL is empty")
                return {}
                
            # Stalker portal API URL
            api_url = f"{base_url}/stalker_portal/server/load.php"
            
            # Build headers
            user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            headers = {
                'User-Agent': user_agent,
                'X-User-Agent': user_agent,
                'Authorization': f"Bearer {token}"
            }
            
            # Add proxy if configured
            proxies = {}
            if portal.get('proxy'):
                proxies = {
                    'http': portal['proxy'],
                    'https': portal['proxy']
                }
            
            # Get channel list if needed
            channels = []
            if channel_id:
                channels = [{'id': channel_id}]
            else:
                channels = self.get_channels(portal, mac, token)
                
            if not channels:
                return {}
                
            # Process each channel
            epg_data = {}
            for channel in channels:
                channel_id = channel.get('id')
                if not channel_id:
                    continue
                    
                # Get EPG for this channel
                params = {
                    'type': 'epg',
                    'action': 'get_simple_data_table',
                    'ch_id': channel_id,
                    'date': time.strftime('%Y-%m-%d', time.localtime(start_time)),
                    'JsHttpRequest': '1-xml'
                }
                
                response = requests.get(
                    api_url,
                    params=params,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.http_timeout
                )
                
                if response.status_code != 200:
                    logger.error(f"Get EPG failed with status code {response.status_code}")
                    continue
                    
                # Parse response
                try:
                    data = response.json()
                    if not data.get('js') or not data['js'].get('data'):
                        logger.error(f"EPG response missing data: {data}")
                        continue
                        
                    # Extract EPG data
                    epg_items = data['js']['data']
                    
                    # Format EPG data
                    epg_list = []
                    for item in epg_items:
                        # Parse timestamps
                        try:
                            start = int(item.get('start_timestamp', 0))
                            end = int(item.get('stop_timestamp', 0))
                        except (ValueError, TypeError):
                            continue
                            
                        # Skip items outside time range
                        if end < start_time or start > end_time:
                            continue
                            
                        epg_list.append({
                            'id': f"epg_{channel_id}_{start}",
                            'title': item.get('name', 'Unknown'),
                            'description': item.get('descr', ''),
                            'start_time': start,
                            'end_time': end,
                            'duration': end - start,
                            'category': item.get('category', '')
                        })
                    
                    epg_data[channel_id] = epg_list
                    
                except ValueError as e:
                    logger.error(f"Error parsing EPG response: {str(e)}")
                    continue
                    
            logger.info(f"Retrieved EPG data for {len(epg_data)} channels")
            return epg_data
                
        except Exception as e:
            logger.error(f"Error getting EPG from Stalker Portal: {str(e)}")
            return {}