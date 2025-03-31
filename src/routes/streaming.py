"""
Streaming route handlers for STB-ReStreamer.
"""
import logging
from typing import Dict, Any, Optional
from flask import Blueprint, Response, request, current_app, abort, jsonify, session, redirect, url_for
from werkzeug.exceptions import BadRequest, NotFound, TooManyRequests

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
streaming_bp = Blueprint('streaming', __name__)

@streaming_bp.route('/stream/<portal_id>/<mac>/<channel_id>')
def stream(portal_id: str, mac: str, channel_id: str):
    """
    Stream a channel from a portal.
    
    Args:
        portal_id (str): Portal ID
        mac (str): MAC address
        channel_id (str): Channel ID
    
    Returns:
        Response: Streaming response
    """
    # Get managers
    portal_manager = current_app.portal_manager
    stream_manager = current_app.stream_manager
    rate_limiter = current_app.rate_limiter
    
    # Check if portal exists
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        logger.warning(f"Stream request for unknown portal: {portal_id}")
        abort(404, description="Portal not found")
        
    # Check if portal is enabled
    if not portal.get('enabled', False):
        logger.warning(f"Stream request for disabled portal: {portal_id}")
        abort(403, description="Portal is disabled")
    
    # Get client IP
    client_ip = request.remote_addr
    rate_key = f"stream:{client_ip}"
    
    # Apply rate limiting
    if not rate_limiter.is_allowed(rate_key):
        retry_after = int(rate_limiter.get_retry_after(rate_key))
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return abort(429, description=f"Rate limit exceeded. Try again in {retry_after} seconds.")
    
    # Format MAC address (normalize to lowercase without colons)
    mac = mac.lower().replace(':', '').replace('-', '')
    
    try:
        # Check if we have a valid URL from cache
        link_cache = current_app.link_cache
        cached_url, ffmpeg_cmd = link_cache.get(f"{portal_id}:{mac}:{channel_id}")
        
        if cached_url and ffmpeg_cmd:
            logger.info(f"Using cached stream for {portal_id}:{mac}:{channel_id}")
            
            # Get client IP
            client_ip = request.remote_addr
            
            # Get portal name
            portal_name = portal.get('name', 'Unknown Portal')
            
            # Get channel details if available
            stb_api = current_app.stb_api
            channel_name = stb_api.get_channel_name(portal_id, mac, channel_id) or channel_id
            
            # Return the streaming response using cached command
            return Response(
                stream_manager.stream_generator(
                    ffmpeg_cmd, 
                    portal_id, 
                    channel_id,
                    mac, 
                    channel_name,
                    client_ip,
                    portal_name
                ),
                mimetype='video/mp2t'
            )
        
        # Get stream URL from STB API service
        stb_api = current_app.stb_api
        stream_url = stb_api.get_stream_url(portal_id, mac, channel_id)
        
        if not stream_url:
            logger.error(f"Failed to get stream URL for {portal_id}:{mac}:{channel_id}")
            abort(500, description="Failed to get stream URL. Authentication or profile information may be missing.")
        
        # Prepare FFmpeg command
        ffmpeg_cmd = stream_manager.prepare_ffmpeg_command(stream_url, portal.get('proxy'))
        
        # Cache the URL and command
        link_cache.set(f"{portal_id}:{mac}:{channel_id}", stream_url, ffmpeg_cmd)
        
        # Get client IP
        client_ip = request.remote_addr
        
        # Get portal name
        portal_name = portal.get('name', 'Unknown Portal')
        
        # Get channel details if available
        channel_name = stb_api.get_channel_name(portal_id, mac, channel_id) or channel_id
        
        # Return the streaming response
        logger.info(f"Streaming {portal_id}:{mac}:{channel_id}")
        return Response(
            stream_manager.stream_generator(
                ffmpeg_cmd, 
                portal_id, 
                channel_id,
                mac, 
                channel_name,
                client_ip,
                portal_name
            ),
            mimetype='video/mp2t'
        )
    
    except Exception as e:
        logger.error(f"Error streaming {portal_id}:{mac}:{channel_id}: {e}")
        abort(500, description=f"Streaming error: {str(e)}")

@streaming_bp.route('/preview/<portal_id>/<mac>/<channel_id>')
def preview(portal_id: str, mac: str, channel_id: str):
    """
    Preview a channel in the web interface.
    
    Args:
        portal_id (str): Portal ID
        mac (str): MAC address
        channel_id (str): Channel ID
    
    Returns:
        Response: Streaming response or redirect to login
    """
    # Check authentication for preview
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
        
    # Get managers
    portal_manager = current_app.portal_manager
    stream_manager = current_app.stream_manager
    
    # Check if portal exists
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        logger.warning(f"Preview request for unknown portal: {portal_id}")
        abort(404, description="Portal not found")
        
    # Check if portal is enabled
    if not portal.get('enabled', False):
        logger.warning(f"Preview request for disabled portal: {portal_id}")
        abort(403, description="Portal is disabled")
    
    # Format MAC address (normalize to lowercase without colons)
    mac = mac.lower().replace(':', '').replace('-', '')
    
    try:
        # Get stream URL from STB API service
        stb_api = current_app.stb_api
        stream_url = stb_api.get_stream_url(portal_id, mac, channel_id)
        
        if not stream_url:
            logger.error(f"Failed to get preview URL for {portal_id}:{mac}:{channel_id}")
            abort(500, description="Failed to get stream URL. Authentication or profile information may be missing.")
        
        # Prepare FFmpeg command for preview (lower quality)
        ffmpeg_cmd = stream_manager.prepare_ffmpeg_command(
            stream_url, 
            portal.get('proxy'),
            is_preview=True
        )
        
        # Get client IP
        client_ip = request.remote_addr
        
        # Get portal name
        portal_name = portal.get('name', 'Unknown Portal')
        
        # Get channel details if available
        channel_name = stb_api.get_channel_name(portal_id, mac, channel_id) or channel_id
        
        # Return the streaming response
        logger.info(f"Previewing {portal_id}:{mac}:{channel_id}")
        return Response(
            stream_manager.stream_generator(
                ffmpeg_cmd, 
                portal_id, 
                channel_id,
                mac, 
                channel_name,
                client_ip,
                portal_name
            ),
            mimetype='video/mp2t'
        )
    
    except Exception as e:
        logger.error(f"Error previewing {portal_id}:{mac}:{channel_id}: {e}")
        abort(500, description=f"Preview error: {str(e)}")

@streaming_bp.route('/api/active-streams')
def api_active_streams():
    """
    API endpoint for active streams.
    
    Returns:
        Dict: JSON response with active streams information
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
        
    # Get active streams
    stream_manager = current_app.stream_manager
    active_streams = stream_manager.get_active_streams()
    
    return jsonify({
        'active_streams': active_streams,
        'count': len(active_streams)
    })