"""
Ministra Portal Provider for STB-ReStreamer.
Ministra is the evolution of Stalker Portal with some API changes.
"""
import time
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

from src.services.portal_providers.base_provider import BasePortalProvider

# Configure logger
logger = logging.getLogger("STB-Proxy")

class MinistraPortalProvider(BasePortalProvider):
    """Implementation of the Ministra Portal API provider."""
    
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get authentication token from Ministra portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            
        Returns:
            Authentication token or None if failed
        """
        try:
            # Extract portal configuration
            portal_url = portal.get('url', '')
            username = portal.get('username', '')
            password = portal.get('password', '')
            
            if not portal_url:
                logger.error("Portal URL is missing")
                return None
                
            # Format MAC address for Ministra
            formatted_mac = mac.replace(':', '').lower()
            
            # Ministra login API
            login_url = urljoin(portal_url, 'stalker_portal/server/load.php')
            
            # Headers required for Ministra
            headers = {
                'User-Agent': 'Model: MAG250; Link: WiFi',
                'X-User-Agent': 'Model: MAG250; Link: WiFi',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Initial handshake
            params = {
                'type': 'stb',
                'action': 'handshake',
                'token': '',
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(login_url, params=params, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Ministra handshake failed: {response.status_code} {response.text}")
                return None
                
            # Parse response
            try:
                data = response.json()
                token = data.get('js', {}).get('token')
                if not token:
                    logger.error("No token in Ministra handshake response")
                    return None
            except Exception as e:
                logger.error(f"Error parsing Ministra handshake response: {str(e)}")
                return None
                
            # Authenticate with token
            auth_params = {
                'type': 'stb',
                'action': 'do_auth',
                'token': token,
                'login': username,
                'password': password,
                'device_id': formatted_mac,
                'device_id2': formatted_mac,
                'JsHttpRequest': '1-xml'
            }
            
            headers['Authorization'] = f'Bearer {token}'
            
            auth_response = requests.get(login_url, params=auth_params, headers=headers, timeout=10)
            if not auth_response.ok:
                logger.error(f"Ministra authentication failed: {auth_response.status_code} {auth_response.text}")
                return None
                
            # Success - return the token
            return token
            
        except Exception as e:
            logger.error(f"Error authenticating with Ministra portal: {str(e)}")
            return None
            
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> Optional[Dict]:
        """
        Get user profile from Ministra portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token
            
        Returns:
            User profile dictionary or None if failed
        """
        if not token:
            logger.error("Missing token for Ministra get_profile")
            return None
            
        try:
            # Extract portal configuration
            portal_url = portal.get('url', '')
            
            if not portal_url:
                logger.error("Portal URL is missing")
                return None
                
            # Format MAC address
            formatted_mac = mac.replace(':', '').lower()
            
            # Ministra profile API
            profile_url = urljoin(portal_url, 'stalker_portal/server/load.php')
            
            # Headers required for Ministra
            headers = {
                'User-Agent': 'Model: MAG250; Link: WiFi',
                'X-User-Agent': 'Model: MAG250; Link: WiFi',
                'Authorization': f'Bearer {token}',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Get profile info
            params = {
                'type': 'stb',
                'action': 'get_profile',
                'token': token,
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(profile_url, params=params, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Ministra get_profile failed: {response.status_code} {response.text}")
                return None
                
            # Parse response
            try:
                data = response.json()
                profile_data = data.get('js', {})
                
                # Format profile data
                return {
                    'status': 'active' if profile_data.get('status') == 1 else 'inactive',
                    'expires': profile_data.get('expire_date', 0),
                    'max_connections': profile_data.get('max_devices', 1),
                    'username': profile_data.get('login', ''),
                    'package': profile_data.get('tariff_plan', {}).get('name', 'Unknown')
                }
                
            except Exception as e:
                logger.error(f"Error parsing Ministra profile response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting profile from Ministra portal: {str(e)}")
            return None
            
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> List[Dict]:
        """
        Get channel list from Ministra portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token
            
        Returns:
            List of channel dictionaries
        """
        if not token:
            logger.error("Missing token for Ministra get_channels")
            return []
            
        try:
            # Extract portal configuration
            portal_url = portal.get('url', '')
            
            if not portal_url:
                logger.error("Portal URL is missing")
                return []
                
            # Format MAC address
            formatted_mac = mac.replace(':', '').lower()
            
            # Ministra channels API
            channels_url = urljoin(portal_url, 'stalker_portal/server/load.php')
            
            # Headers required for Ministra
            headers = {
                'User-Agent': 'Model: MAG250; Link: WiFi',
                'X-User-Agent': 'Model: MAG250; Link: WiFi',
                'Authorization': f'Bearer {token}',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Get genre categories first
            genre_params = {
                'type': 'itv',
                'action': 'get_genres',
                'token': token,
                'JsHttpRequest': '1-xml'
            }
            
            genre_response = requests.get(channels_url, params=genre_params, headers=headers, timeout=10)
            if not genre_response.ok:
                logger.error(f"Ministra get_genres failed: {genre_response.status_code} {genre_response.text}")
                genres = {}
            else:
                try:
                    genre_data = genre_response.json()
                    genres = {g['id']: g['title'] for g in genre_data.get('js', [])}
                except Exception:
                    genres = {}
            
            # Get channels
            params = {
                'type': 'itv',
                'action': 'get_all_channels',
                'token': token,
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(channels_url, params=params, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Ministra get_all_channels failed: {response.status_code} {response.text}")
                return []
                
            # Parse response
            try:
                data = response.json()
                channels_data = data.get('js', {}).get('data', [])
                
                # Format channels
                channels = []
                for channel in channels_data:
                    # Skip non-active channels
                    if not channel.get('cmd') or channel.get('status', 0) != 1:
                        continue
                        
                    channel_id = str(channel.get('id', ''))
                    genre_id = str(channel.get('tv_genre_id', '0'))
                    
                    channels.append({
                        'id': channel_id,
                        'name': channel.get('name', f"Channel {channel_id}"),
                        'number': channel.get('number', 0),
                        'type': genres.get(genre_id, 'Unknown'),
                        'logo': channel.get('logo', '')
                    })
                
                return channels
                
            except Exception as e:
                logger.error(f"Error parsing Ministra channels response: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting channels from Ministra portal: {str(e)}")
            return []
            
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str]) -> Optional[str]:
        """
        Get stream URL for a channel from Ministra portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID
            token: Authentication token
            
        Returns:
            Stream URL or None if failed
        """
        if not token:
            logger.error("Missing token for Ministra get_stream_url")
            return None
            
        try:
            # Extract portal configuration
            portal_url = portal.get('url', '')
            
            if not portal_url:
                logger.error("Portal URL is missing")
                return None
                
            # Format MAC address
            formatted_mac = mac.replace(':', '').lower()
            
            # Ministra stream URL API
            stream_url = urljoin(portal_url, 'stalker_portal/server/load.php')
            
            # Headers required for Ministra
            headers = {
                'User-Agent': 'Model: MAG250; Link: WiFi',
                'X-User-Agent': 'Model: MAG250; Link: WiFi',
                'Authorization': f'Bearer {token}',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Get stream URL
            params = {
                'type': 'itv',
                'action': 'create_link',
                'cmd': 'ffmpeg http://localhost/ch/{CHANNEL_ID}',
                'series': '',
                'forced_storage': '',
                'disable_ad': 0,
                'download': 0,
                'channel_id': channel_id,
                'token': token,
                'JsHttpRequest': '1-xml'
            }
            
            response = requests.get(stream_url, params=params, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Ministra create_link failed: {response.status_code} {response.text}")
                return None
                
            # Parse response
            try:
                data = response.json()
                cmd = data.get('js', {}).get('cmd', '')
                
                if not cmd:
                    logger.error(f"No stream URL in Ministra response for channel {channel_id}")
                    return None
                    
                # Format the command string to extract the URL
                if cmd.startswith('ffmpeg '):
                    # Extract the URL from ffmpeg command
                    return cmd.split(' ')[1]
                else:
                    # Otherwise, return the full command
                    return cmd
                
            except Exception as e:
                logger.error(f"Error parsing Ministra stream URL response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting stream URL from Ministra portal: {str(e)}")
            return None
            
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str], 
               token: Optional[str], start_time: Optional[int] = None, 
               end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data from Ministra portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID for specific channel, or None for all
            token: Authentication token
            start_time: Start time timestamp, or None for current time
            end_time: End time timestamp, or None for 24 hours from start
            
        Returns:
            Dictionary with EPG data
        """
        if not token:
            logger.error("Missing token for Ministra get_epg")
            return {}
            
        try:
            # Extract portal configuration
            portal_url = portal.get('url', '')
            
            if not portal_url:
                logger.error("Portal URL is missing")
                return {}
                
            # Format MAC address
            formatted_mac = mac.replace(':', '').lower()
            
            # Ministra EPG API
            epg_url = urljoin(portal_url, 'stalker_portal/server/load.php')
            
            # Headers required for Ministra
            headers = {
                'User-Agent': 'Model: MAG250; Link: WiFi',
                'X-User-Agent': 'Model: MAG250; Link: WiFi',
                'Authorization': f'Bearer {token}',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Calculate time range if not provided
            current_time = int(time.time())
            start_time = start_time or current_time
            end_time = end_time or (start_time + 24 * 3600)  # 24 hours
            
            # Results dictionary
            epg_data = {}
            
            # If channel_id is provided, get EPG for that channel only
            if channel_id:
                channels = [channel_id]
            else:
                # Otherwise, get all channels and their EPG
                channels_list = self.get_channels(portal, mac, token)
                channels = [ch['id'] for ch in channels_list]
            
            # Get EPG for each channel
            for ch_id in channels:
                # Get EPG for this channel
                params = {
                    'type': 'itv',
                    'action': 'get_epg_info',
                    'period': f"{start_time}:{end_time}",
                    'channel_id': ch_id,
                    'token': token,
                    'JsHttpRequest': '1-xml'
                }
                
                response = requests.get(epg_url, params=params, headers=headers, timeout=10)
                if not response.ok:
                    logger.error(f"Ministra get_epg_info failed for channel {ch_id}: {response.status_code}")
                    continue
                    
                # Parse response
                try:
                    data = response.json()
                    programs = data.get('js', {}).get('data', [])
                    
                    # Format programs
                    formatted_programs = []
                    for program in programs:
                        start = program.get('start_timestamp', 0)
                        end = program.get('stop_timestamp', 0)
                        
                        formatted_programs.append({
                            'id': f"prog_{ch_id}_{start}",
                            'title': program.get('name', 'Unknown'),
                            'description': program.get('descr', ''),
                            'start_time': start,
                            'end_time': end,
                            'duration': end - start,
                            'type': program.get('category', 'Unknown')
                        })
                    
                    epg_data[ch_id] = formatted_programs
                    
                except Exception as e:
                    logger.error(f"Error parsing Ministra EPG response for channel {ch_id}: {str(e)}")
                
            return epg_data
                
        except Exception as e:
            logger.error(f"Error getting EPG from Ministra portal: {str(e)}")
            return {}