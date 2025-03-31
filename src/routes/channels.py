"""
Channel route handlers for STB-ReStreamer.
"""
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, render_template, current_app, session, redirect, url_for, jsonify, request, abort

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
channels_bp = Blueprint('channels', __name__)

@channels_bp.route('/channels')
def list_channels():
    """
    Render the channel list page.
    
    Returns:
        Rendered template or redirect to login
    """
    # Check authentication
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    return render_template('channel_preview.html', title="Channel Preview")

@channels_bp.route('/api/channels/<portal_id>/<mac>')
def api_get_channels(portal_id: str, mac: str):
    """
    API endpoint to get channels for a portal.
    
    Args:
        portal_id (str): Portal ID
        mac (str): MAC address
    
    Returns:
        Dict: JSON response with channels
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
    
    # Format MAC address (normalize to lowercase without colons)
    mac = mac.lower().replace(':', '').replace('-', '')
    
    try:
        # Get StB API service
        stb_api = current_app.stb_api
        
        # Get channels
        channels = stb_api.get_channels(portal_id, mac)
        
        # Get categories for enriching channel data
        category_manager = current_app.category_manager
        categories = category_manager.get_categories()
        
        # Enrich channel data with category information
        for channel in channels:
            if isinstance(channel, dict) and 'id' in channel:
                channel_id = str(channel['id'])
                for category in categories:
                    if 'channels' in category and channel_id in category.get('channels', []):
                        channel['category'] = category.get('name')
                        break
        
        return jsonify({
            'channels': channels,
            'count': len(channels)
        })
    
    except Exception as e:
        logger.error(f"Error getting channels for {portal_id}:{mac}: {e}")
        return jsonify({
            'error': f"Failed to get channels: {str(e)}",
            'channels': [],
            'count': 0
        }), 500

@channels_bp.route('/api/channel/<portal_id>/<mac>/<channel_id>')
def api_get_channel(portal_id: str, mac: str, channel_id: str):
    """
    API endpoint to get a specific channel.
    
    Args:
        portal_id (str): Portal ID
        mac (str): MAC address
        channel_id (str): Channel ID
    
    Returns:
        Dict: JSON response with channel details
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
    
    # Format MAC address (normalize to lowercase without colons)
    mac = mac.lower().replace(':', '').replace('-', '')
    
    try:
        # Get StB API service
        stb_api = current_app.stb_api
        
        # Get channels and find the specific one
        channels = stb_api.get_channels(portal_id, mac)
        channel = next((c for c in channels if str(c.get('id')) == channel_id), None)
        
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get category for channel
        category_manager = current_app.category_manager
        categories = category_manager.get_categories()
        
        for category in categories:
            if 'channels' in category and channel_id in category.get('channels', []):
                channel['category'] = category.get('name')
                break
        
        # Get EPG data if available
        epg_manager = current_app.epg_manager
        now_playing = epg_manager.get_current_program(channel_id)
        
        if now_playing:
            channel['now_playing'] = now_playing
        
        return jsonify({
            'channel': channel
        })
    
    except Exception as e:
        logger.error(f"Error getting channel {channel_id} for {portal_id}:{mac}: {e}")
        return jsonify({
            'error': f"Failed to get channel: {str(e)}"
        }), 500

@channels_bp.route('/api/portals')
def api_get_portals():
    """
    API endpoint to get all portals.
    
    Returns:
        Dict: JSON response with portals
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Get portal manager
        portal_manager = current_app.portal_manager
        
        # Get portals
        portals = portal_manager.get_all_portals()
        
        # Clean sensitive data
        for portal in portals:
            if 'password' in portal:
                portal['password'] = '*******'
        
        return jsonify({
            'portals': portals,
            'count': len(portals)
        })
    
    except Exception as e:
        logger.error(f"Error getting portals: {e}")
        return jsonify({
            'error': f"Failed to get portals: {str(e)}",
            'portals': [],
            'count': 0
        }), 500 