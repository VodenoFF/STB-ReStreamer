"""
XC Updates Provider for STB-ReStreamer.
An enhanced implementation of the Xtream Codes protocol with additional features.
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

class XCUpdatesPortalProvider(BasePortalProvider):
    """Implementation of the XC Updates API provider (enhanced Xtream)."""
    
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get authentication token from XC Updates portal.
        XC Updates typically uses username/password as token.
        
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
            
            if not portal_url or not username or not password:
                logger.error("Missing required portal configuration")
                return None
            
            # XC Updates uses username/password for API access
            # We'll create a combined token format: username:password
            token = f"{username}:{password}"
            
            # Verify credentials with a test API call
            player_api_url = self._build_player_api_url(portal_url, username, password)
            if not player_api_url:
                return None
                
            # Test with a simple "user" call
            test_url = f"{player_api_url}&action=user"
            response = requests.get(test_url, timeout=10)
            
            if not response.ok:
                logger.error(f"XC Updates authentication failed: {response.status_code} {response.text}")
                return None
                
            # Try to parse response
            try:
                data = response.json()
                # Check if response contains user data
                if 'user_info' not in data and 'username' not in data:
                    logger.error("Invalid XC Updates API response")
                    return None
            except Exception as e:
                logger.error(f"Error parsing XC Updates response: {str(e)}")
                return None
                
            # Success - return the token
            return token
            
        except Exception as e:
            logger.error(f"Error authenticating with XC Updates portal: {str(e)}")
            return None
            
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> Optional[Dict]:
        """
        Get user profile from XC Updates portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token (username:password)
            
        Returns:
            User profile dictionary or None if failed
        """
        if not token:
            logger.error("Missing token for XC Updates get_profile")
            return None
            
        try:
            # Extract credentials from token
            username, password = token.split(':', 1)
            
            # Build player API URL
            portal_url = portal.get('url', '')
            player_api_url = self._build_player_api_url(portal_url, username, password)
            if not player_api_url:
                return None
                
            # Get user profile info
            user_url = f"{player_api_url}&action=user"
            response = requests.get(user_url, timeout=10)
            
            if not response.ok:
                logger.error(f"XC Updates get_profile failed: {response.status_code} {response.text}")
                return None
                
            # Parse response
            try:
                data = response.json()
                
                # Check which format the response is in
                user_info = data.get('user_info', data)
                
                # Get current timestamp for comparison
                current_time = int(time.time())
                
                # Calculate expiry time
                exp_date = user_info.get('exp_date', 0)
                if exp_date:
                    try:
                        # Handle both timestamp and date string formats
                        if isinstance(exp_date, str) and not exp_date.isdigit():
                            # Parse date string like "2023-12-31" to timestamp
                            import datetime
                            dt = datetime.datetime.strptime(exp_date, "%Y-%m-%d")
                            exp_timestamp = int(dt.timestamp())
                        else:
                            exp_timestamp = int(exp_date)
                    except Exception:
                        exp_timestamp = current_time + 30 * 24 * 3600  # 30 days from now
                else:
                    exp_timestamp = current_time + 30 * 24 * 3600  # 30 days from now
                
                # Format profile data
                return {
                    'status': 'active' if user_info.get('status', '').lower() == 'active' else 'inactive',
                    'expires': exp_timestamp,
                    'max_connections': user_info.get('max_connections', 1),
                    'username': user_info.get('username', username),
                    'package': user_info.get('package', 'Unknown')
                }
                
            except Exception as e:
                logger.error(f"Error parsing XC Updates profile response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting profile from XC Updates portal: {str(e)}")
            return None
            
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str]) -> List[Dict]:
        """
        Get channel list from XC Updates portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            token: Authentication token (username:password)
            
        Returns:
            List of channel dictionaries
        """
        if not token:
            logger.error("Missing token for XC Updates get_channels")
            return []
            
        try:
            # Extract credentials from token
            username, password = token.split(':', 1)
            
            # Build player API URL
            portal_url = portal.get('url', '')
            player_api_url = self._build_player_api_url(portal_url, username, password)
            if not player_api_url:
                return []
                
            # Get categories first
            categories_url = f"{player_api_url}&action=get_live_categories"
            categories_response = requests.get(categories_url, timeout=10)
            
            if not categories_response.ok:
                logger.error(f"XC Updates get_live_categories failed: {categories_response.status_code}")
                categories = {}
            else:
                try:
                    categories_data = categories_response.json()
                    categories = {cat['category_id']: cat['category_name'] for cat in categories_data}
                except Exception:
                    categories = {}
            
            # Get live streams
            streams_url = f"{player_api_url}&action=get_live_streams"
            response = requests.get(streams_url, timeout=10)
            
            if not response.ok:
                logger.error(f"XC Updates get_live_streams failed: {response.status_code}")
                return []
                
            # Parse response
            try:
                channels_data = response.json()
                
                # Format channels
                channels = []
                for channel in channels_data:
                    # Skip inactive channels
                    if not channel.get('stream_status', 1):
                        continue
                        
                    channel_id = str(channel.get('stream_id', ''))
                    category_id = str(channel.get('category_id', '0'))
                    
                    # Enhanced XC protocol might contain additional fields
                    epg_channel_id = channel.get('epg_channel_id', '')
                    added = channel.get('added', 0)
                    is_adult = channel.get('is_adult', 0)
                    
                    # Create channel object with XC Updates specific fields
                    channel_obj = {
                        'id': channel_id,
                        'name': channel.get('name', f"Channel {channel_id}"),
                        'number': int(channel.get('num', 0)),
                        'type': categories.get(category_id, 'Unknown'),
                        'logo': channel.get('stream_icon', '')
                    }
                    
                    # Add enhanced fields if present
                    if epg_channel_id:
                        channel_obj['epg_channel_id'] = epg_channel_id
                    if added:
                        channel_obj['added'] = added
                    if is_adult:
                        channel_obj['is_adult'] = bool(is_adult)
                        
                    channels.append(channel_obj)
                
                return channels
                
            except Exception as e:
                logger.error(f"Error parsing XC Updates channels response: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting channels from XC Updates portal: {str(e)}")
            return []
            
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str]) -> Optional[str]:
        """
        Get stream URL for a channel from XC Updates portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID
            token: Authentication token (username:password)
            
        Returns:
            Stream URL or None if failed
        """
        if not token:
            logger.error("Missing token for XC Updates get_stream_url")
            return None
            
        try:
            # Extract credentials from token
            username, password = token.split(':', 1)
            
            # Extract portal URL
            portal_url = portal.get('url', '')
            if not portal_url:
                logger.error("Portal URL is missing")
                return None
                
            # Build stream URL directly
            # XC Updates uses the same URL format as Xtream but may have enhanced features
            if portal_url.endswith('/'):
                portal_url = portal_url[:-1]
                
            # XC Updates may support different stream formats
            stream_format = portal.get('stream_format', 'ts')  # Default to .ts format
            
            # Generate stream URL
            stream_url = f"{portal_url}/live/{username}/{password}/{channel_id}.{stream_format}"
            
            # Optional: You can test the URL with a HEAD request to validate it
            # We'll skip this for now to reduce load on the server
            
            return stream_url
                
        except Exception as e:
            logger.error(f"Error getting stream URL from XC Updates portal: {str(e)}")
            return None
            
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str], 
               token: Optional[str], start_time: Optional[int] = None, 
               end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data from XC Updates portal.
        
        Args:
            portal: Portal configuration dictionary
            mac: MAC address of the device
            channel_id: Channel ID for specific channel, or None for all
            token: Authentication token (username:password)
            start_time: Start time timestamp, or None for current time
            end_time: End time timestamp, or None for 24 hours from start
            
        Returns:
            Dictionary with EPG data
        """
        if not token:
            logger.error("Missing token for XC Updates get_epg")
            return {}
            
        try:
            # Extract credentials from token
            username, password = token.split(':', 1)
            
            # Build player API URL
            portal_url = portal.get('url', '')
            player_api_url = self._build_player_api_url(portal_url, username, password)
            if not player_api_url:
                return {}
                
            # First, we need to get channels to map stream_id to epg_channel_id
            channels = self.get_channels(portal, mac, token)
            
            # Map stream_id to epg_channel_id
            channel_epg_map = {}
            for ch in channels:
                ch_id = ch.get('id')
                epg_ch_id = ch.get('epg_channel_id', ch_id)
                channel_epg_map[ch_id] = epg_ch_id
            
            # Calculate time range if not provided
            current_time = int(time.time())
            start_time = start_time or current_time
            end_time = end_time or (start_time + 24 * 3600)  # 24 hours
            
            # Results dictionary
            epg_data = {}
            
            # If channel_id is provided, get EPG for that channel only
            if channel_id:
                # Get epg_channel_id
                epg_channel_id = channel_epg_map.get(channel_id, channel_id)
                
                # XC Updates specific EPG endpoint
                epg_url = f"{player_api_url}&action=get_short_epg&stream_id={channel_id}"
                
                # Some providers support timeshift feature
                if start_time and end_time:
                    epg_url += f"&from={start_time}&to={end_time}"
                
                response = requests.get(epg_url, timeout=10)
                if not response.ok:
                    logger.error(f"XC Updates get_short_epg failed for channel {channel_id}: {response.status_code}")
                    # Try alternative endpoint
                    alt_epg_url = f"{player_api_url}&action=get_simple_data_table&stream_id={channel_id}"
                    alt_response = requests.get(alt_epg_url, timeout=10)
                    
                    if not alt_response.ok:
                        logger.error(f"XC Updates alternative EPG endpoint failed: {alt_response.status_code}")
                        return {}
                        
                    response = alt_response
                
                # Parse response
                try:
                    data = response.json()
                    epg_list = data.get('epg_listings', [])
                    
                    # Format programs
                    formatted_programs = []
                    for program in epg_list:
                        # Parse start and end times
                        start = program.get('start', '0').strip()
                        end = program.get('end', '0').strip()
                        
                        # Convert to timestamps if they're not already
                        if start and not start.isdigit():
                            try:
                                # Parse formats like "2023-07-23 10:00:00"
                                import datetime
                                start_dt = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                                start_timestamp = int(start_dt.timestamp())
                            except Exception:
                                start_timestamp = 0
                        else:
                            start_timestamp = int(start) if start else 0
                            
                        if end and not end.isdigit():
                            try:
                                import datetime
                                end_dt = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                                end_timestamp = int(end_dt.timestamp())
                            except Exception:
                                # If end time parsing fails, estimate based on start time
                                end_timestamp = start_timestamp + 3600  # 1 hour default
                        else:
                            end_timestamp = int(end) if end else (start_timestamp + 3600)
                            
                        # Calculate duration
                        duration = end_timestamp - start_timestamp
                        
                        # Create program entry
                        formatted_programs.append({
                            'id': f"prog_{channel_id}_{start_timestamp}",
                            'title': program.get('title', 'Unknown'),
                            'description': program.get('description', ''),
                            'start_time': start_timestamp,
                            'end_time': end_timestamp,
                            'duration': duration,
                            'type': program.get('category', 'Unknown')
                        })
                    
                    epg_data[channel_id] = formatted_programs
                    
                except Exception as e:
                    logger.error(f"Error parsing XC Updates EPG response for channel {channel_id}: {str(e)}")
                
            else:
                # For all channels, use the full EPG API
                # Note: This could be heavy and might require pagination or channel-by-channel requests
                # Here we'll use a simplified approach with the multi-EPG endpoint
                
                # XC Updates API allows getting EPG for multiple channels, but it's better to do it 
                # in smaller batches to avoid timeouts
                batch_size = 10
                channel_batches = [list(channel_epg_map.keys())[i:i + batch_size] 
                                   for i in range(0, len(channel_epg_map), batch_size)]
                
                for batch in channel_batches:
                    # Build a comma-separated list of channel IDs
                    channels_str = ",".join(batch)
                    
                    # Get EPG for this batch
                    multi_epg_url = f"{player_api_url}&action=get_simple_data_table&stream_id={channels_str}"
                    response = requests.get(multi_epg_url, timeout=15)  # Increased timeout for batch
                    
                    if not response.ok:
                        logger.error(f"XC Updates multi EPG request failed: {response.status_code}")
                        continue
                        
                    # Parse response
                    try:
                        data = response.json()
                        
                        for ch_id in batch:
                            # The response structure may vary between providers
                            ch_epg = data.get(ch_id, data.get('epg_listings', {}).get(ch_id, []))
                            
                            if not ch_epg:
                                continue
                                
                            # Format programs for this channel
                            formatted_programs = []
                            for program in ch_epg:
                                # Similar processing as above
                                start = program.get('start', '0').strip()
                                end = program.get('end', '0').strip()
                                
                                # Convert to timestamps
                                if start and not start.isdigit():
                                    try:
                                        import datetime
                                        start_dt = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                                        start_timestamp = int(start_dt.timestamp())
                                    except Exception:
                                        start_timestamp = 0
                                else:
                                    start_timestamp = int(start) if start else 0
                                    
                                if end and not end.isdigit():
                                    try:
                                        import datetime
                                        end_dt = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                                        end_timestamp = int(end_dt.timestamp())
                                    except Exception:
                                        end_timestamp = start_timestamp + 3600
                                else:
                                    end_timestamp = int(end) if end else (start_timestamp + 3600)
                                    
                                # Calculate duration
                                duration = end_timestamp - start_timestamp
                                
                                # Create program entry
                                formatted_programs.append({
                                    'id': f"prog_{ch_id}_{start_timestamp}",
                                    'title': program.get('title', 'Unknown'),
                                    'description': program.get('description', ''),
                                    'start_time': start_timestamp,
                                    'end_time': end_timestamp,
                                    'duration': duration,
                                    'type': program.get('category', 'Unknown')
                                })
                                
                            # Add to EPG data
                            epg_data[ch_id] = formatted_programs
                            
                    except Exception as e:
                        logger.error(f"Error parsing XC Updates multi EPG response: {str(e)}")
            
            return epg_data
                
        except Exception as e:
            logger.error(f"Error getting EPG from XC Updates portal: {str(e)}")
            return {}
            
    def _build_player_api_url(self, portal_url: str, username: str, password: str) -> Optional[str]:
        """
        Build the player API URL for XC Updates.
        
        Args:
            portal_url: Base URL of the portal
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Player API URL or None if failed
        """
        if not portal_url or not username or not password:
            logger.error("Missing required parameters for building player API URL")
            return None
            
        try:
            # Normalize portal URL
            if portal_url.endswith('/'):
                portal_url = portal_url[:-1]
                
            # Build player API URL
            player_api_url = f"{portal_url}/player_api.php?username={username}&password={password}"
            
            return player_api_url
            
        except Exception as e:
            logger.error(f"Error building player API URL: {str(e)}")
            return None