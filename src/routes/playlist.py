"""
Playlist generation routes for STB-ReStreamer.
Provides M3U playlist generation functionality.
"""
import os
import logging
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, Response, current_app, jsonify, stream_with_context
from urllib.parse import quote

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
playlist_bp = Blueprint('playlist', __name__)

@playlist_bp.route('/playlist', methods=['GET'])
def generate_playlist():
    """
    Generate M3U playlist with all channels.
    
    Returns:
        M3U playlist as text/plain response
    """
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get all portals
    portals = portal_manager.get_enabled_portals()
    
    # Get config manager for settings
    config_manager = current_app.config_manager
    
    # Get settings
    sort_by_name = config_manager.get('playlist', 'sort_by_name', default=True)
    sort_by_number = config_manager.get('playlist', 'sort_by_number', default=False)
    sort_by_genre = config_manager.get('playlist', 'sort_by_genre', default=False)
    
    # Generate the playlist
    return Response(
        stream_with_context(_generate_playlist(portals, None, sort_by_name, sort_by_number, sort_by_genre)),
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=playlist.m3u'}
    )

@playlist_bp.route('/groups_playlist', methods=['GET'])
def generate_groups_playlist():
    """
    Generate M3U playlist organized by channel groups.
    
    Returns:
        M3U playlist as text/plain response
    """
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get all portals
    portals = portal_manager.get_enabled_portals()
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get all groups
    channel_groups = channel_group_manager.get_all_groups()
    
    # Get config manager for settings
    config_manager = current_app.config_manager
    
    # Get settings
    sort_by_name = config_manager.get('playlist', 'sort_by_name', default=True)
    sort_by_number = config_manager.get('playlist', 'sort_by_number', default=False)
    sort_by_genre = config_manager.get('playlist', 'sort_by_genre', default=False)
    
    # Generate the playlist with groups
    return Response(
        stream_with_context(_generate_playlist(portals, channel_groups, sort_by_name, sort_by_number, sort_by_genre)),
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=groups_playlist.m3u'}
    )

@playlist_bp.route('/api/playlist/status', methods=['GET'])
def playlist_status():
    """
    Get playlist generation status.
    
    Returns:
        JSON response with status
    """
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get enabled portals
    portals = portal_manager.get_enabled_portals()
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get all groups
    channel_groups = channel_group_manager.get_all_groups()
    
    # Count channels
    channel_count = 0
    for portal_id, portal in portals.items():
        try:
            # Get MAC address
            mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
            if not mac:
                # Use default MAC if not set
                mac = '00:1A:79:00:00:00'.lower().replace(':', '').replace('-', '')
                
            # Get channels
            portal_channels = current_app.stb_api.get_channels(portal_id, mac)
            channel_count += len(portal_channels)
        except Exception as e:
            logger.error(f"Error counting channels for portal {portal_id}: {str(e)}")
    
    return jsonify({
        'status': 'available',
        'channels': channel_count,
        'groups': len(channel_groups),
        'portals': len(portals)
    })

def _generate_playlist(portals: Dict, channel_groups: Optional[Dict] = None, 
                      sort_by_name: bool = True, sort_by_number: bool = False, 
                      sort_by_genre: bool = False) -> str:
    """
    Generate an M3U playlist.
    
    Args:
        portals: Dictionary of portals
        channel_groups: Optional dictionary of channel groups
        sort_by_name: Sort channels by name
        sort_by_number: Sort channels by number
        sort_by_genre: Sort channels by genre
        
    Yields:
        Lines of the M3U playlist
    """
    # Start with the M3U header
    yield "#EXTM3U\n"
    
    # Host for stream URLs
    host = request.host
    
    # All channels from all portals to be included in the playlist
    all_channels = []
    
    # Process all portals to get channels
    for portal_id, portal in portals.items():
        try:
            # Get MAC address
            mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
            if not mac:
                # Use default MAC if not set
                mac = '00:1A:79:00:00:00'.lower().replace(':', '').replace('-', '')
                
            # Get channels
            portal_channels = current_app.stb_api.get_channels(portal_id, mac)
            
            # Get custom settings from portal
            enabled_channels = []
            custom_channel_names = {}
            custom_genres = {}
            custom_channel_numbers = {}
            
            # Legacy format compatibility
            if 'enabled channels' in portal:
                enabled_channels = portal.get('enabled channels', [])
            
            if 'custom channel names' in portal:
                custom_channel_names = portal.get('custom channel names', {})
            
            if 'custom genres' in portal:
                custom_genres = portal.get('custom genres', {})
            
            if 'custom channel numbers' in portal:
                custom_channel_numbers = portal.get('custom channel numbers', {})
            
            # Process channels
            for channel in portal_channels:
                # Skip if not a dictionary
                if not isinstance(channel, dict):
                    continue
                    
                channel_id = str(channel.get('id', ''))
                if not channel_id:
                    continue
                    
                # Handle enabled channels logic
                # If 'enabled channels' list exists and has entries, only include listed channels
                # If list is empty or doesn't exist, include all channels
                should_include = True
                if 'enabled channels' in portal and len(enabled_channels) > 0:
                    should_include = channel_id in enabled_channels
                
                if not should_include:
                    continue
                
                # Get channel details
                channel_number = custom_channel_numbers.get(channel_id, str(channel.get('number', '')))
                channel_name = custom_channel_names.get(channel_id, str(channel.get('name', '')))
                genre = custom_genres.get(channel_id, str(channel.get('genre', '')))
                
                # Find group for this channel if groups are provided
                group = ""
                if channel_groups:
                    for group_name, group_data in channel_groups.items():
                        for ch in group_data:
                            if isinstance(ch, dict) and ch.get('channelId') == channel_id and ch.get('portalId') == portal_id:
                                group = group_name
                                break
                        if group:
                            break
                
                # Build stream URL
                stream_url = f"http://{host}/stream/{portal_id}/{mac}/{channel_id}"
                
                # Add to all channels
                all_channels.append({
                    'name': channel_name,
                    'number': channel_number,
                    'genre': genre,
                    'group': group,
                    'url': stream_url
                })
        except Exception as e:
            logger.error(f"Error processing portal {portal_id} for playlist: {str(e)}")
    
    # Sort channels based on settings
    if sort_by_number:
        # Try to sort by number, fall back to name if non-numeric
        def get_number(channel):
            try:
                return int(channel['number'])
            except (ValueError, TypeError):
                return float('inf')  # Place non-numeric at the end
        
        all_channels.sort(key=get_number)
    
    if sort_by_name:
        all_channels.sort(key=lambda c: c['name'].lower())
    
    if sort_by_genre:
        all_channels.sort(key=lambda c: c['genre'].lower())
    
    # Group channels if needed
    if channel_groups:
        # First output channels with groups
        for channel in all_channels:
            if channel['group']:
                # Output channel entry
                yield f"#EXTINF:-1 tvg-id=\"{channel['number']}\" tvg-name=\"{channel['name']}\" " \
                      f"tvg-logo=\"\" group-title=\"{channel['group']}\",{channel['name']}\n"
                yield f"{channel['url']}\n"
        
        # Then output channels without groups
        for channel in all_channels:
            if not channel['group']:
                # Output channel entry
                yield f"#EXTINF:-1 tvg-id=\"{channel['number']}\" tvg-name=\"{channel['name']}\" " \
                      f"tvg-logo=\"\" group-title=\"No Group\",{channel['name']}\n"
                yield f"{channel['url']}\n"
    else:
        # Output all channels without grouping
        for channel in all_channels:
            # Output channel entry
            yield f"#EXTINF:-1 tvg-id=\"{channel['number']}\" tvg-name=\"{channel['name']}\" " \
                  f"tvg-logo=\"\",{channel['name']}\n"
            yield f"{channel['url']}\n" 