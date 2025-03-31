"""
Stream status route handlers for STB-ReStreamer.
Includes WebSocket events for real-time stream and portal status updates.
"""
import logging
import time
import threading
from typing import Dict, Any, List
from flask import Blueprint, render_template, current_app, session, redirect, url_for, jsonify
from flask_socketio import emit

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
stream_status_bp = Blueprint('stream_status', __name__)

# Status update interval in seconds
UPDATE_INTERVAL = 2

# Global variable to store the update thread
update_thread = None
thread_lock = threading.Lock()

def background_status_thread():
    """
    Background thread that emits stream status updates to connected clients.
    """
    logger.info("Starting stream status update thread")
    while True:
        time.sleep(UPDATE_INTERVAL)
        with current_app.app_context():
            try:
                stream_manager = current_app.stream_manager
                active_streams = stream_manager.get_active_streams()
                
                # Emit the data to all connected clients
                current_app.socketio.emit('stream_status_update', {
                    'active_streams': active_streams,
                    'count': len(active_streams),
                    'timestamp': time.time()
                }, namespace='/stream_status')
            except Exception as e:
                logger.error(f"Error in stream status update thread: {str(e)}")

@stream_status_bp.route('/streams')
def streams_dashboard():
    """
    Render the streams dashboard page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get stream manager
    stream_manager = current_app.stream_manager
    active_streams = stream_manager.get_active_streams()
    
    return render_template(
        'streams.html', 
        title='Streams Dashboard',
        active_streams=active_streams
    )

@stream_status_bp.route('/status')
def status_page():
    """
    Render the stream status page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    return render_template(
        'status/status.html', 
        title='Stream Status'
    )

@stream_status_bp.route('/api/stream-stats')
def api_stream_stats():
    """
    API endpoint for stream statistics.
    
    Returns:
        Dict: JSON response with stream statistics
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get stream manager
    stream_manager = current_app.stream_manager
    active_streams = stream_manager.get_active_streams()
    
    # Calculate statistics
    stats = {
        'total_active': len(active_streams),
        'by_portal': {},
        'by_client': {}
    }
    
    # Group by portal
    for stream_id, stream in active_streams.items():
        portal_name = stream.get('portal_name', 'Unknown')
        if portal_name not in stats['by_portal']:
            stats['by_portal'][portal_name] = 0
        stats['by_portal'][portal_name] += 1
        
        # Group by client IP
        client_ip = stream.get('client_ip', 'Unknown')
        if client_ip not in stats['by_client']:
            stats['by_client'][client_ip] = 0
        stats['by_client'][client_ip] += 1
    
    return jsonify(stats)

# SocketIO event handlers
def register_socketio_events(socketio):
    """
    Register WebSocket event handlers for real-time status updates.
    
    Args:
        socketio: SocketIO instance
    """
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.debug('Client connected to WebSocket')
        
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.debug('Client disconnected from WebSocket')
        
    @socketio.on('request_status')
    def handle_request_status():
        """Handle request for current status."""
        # Get stream manager to get current status
        stream_manager = current_app.stream_manager
        active_streams = stream_manager.get_active_streams()
        
        # Broadcast active streams to the client
        for stream_id, stream_data in active_streams.items():
            stream_status = {
                'stream_id': stream_id,
                'status': stream_data.get('status', 'unknown'),
                'bitrate': stream_data.get('bitrate', 0),
                'clients': stream_data.get('clients', 0),
                'uptime': stream_data.get('uptime', 0)
            }
            socketio.emit('stream_status_update', stream_status)
            
        # Get portal status as well
        portal_manager = current_app.portal_manager
        mac_manager = current_app.mac_manager
        portals = portal_manager.get_all_portals()
        occupied_macs = mac_manager.get_occupied_macs()
        
        # Count active connections per portal
        portal_connections = {}
        for mac_info in occupied_macs.values():
            portal_id = mac_info.get('portal_id')
            if portal_id:
                portal_connections[portal_id] = portal_connections.get(portal_id, 0) + 1
                
        # Send portal status to client
        for portal_id, portal in portals.items():
            portal_status = {
                'portal_id': portal_id,
                'name': portal.get('name', 'Unknown Portal'),
                'status': 'disabled' if not portal.get('enabled', False) else 'up',  # Default to up if enabled (optimistic)
                'connections': portal_connections.get(portal_id, 0)
            }
            socketio.emit('portal_status_update', portal_status)
            
    @socketio.on('check_portal_status')
    def handle_check_portal(data):
        """
        Handle request to check a specific portal's status.
        
        Args:
            data: Dictionary with portal_id
        """
        portal_id = data.get('portal_id')
        if not portal_id:
            return
            
        # Get portal info
        portal_manager = current_app.portal_manager
        portal = portal_manager.get_portal(portal_id)
        
        if not portal:
            return
            
        # Get MAC manager for connection info
        mac_manager = current_app.mac_manager
        occupied_macs = mac_manager.get_occupied_macs()
        
        # Count connections for this portal
        connections = 0
        for mac_info in occupied_macs.values():
            if mac_info.get('portal_id') == portal_id:
                connections += 1
                
        # Get StbApi service to check if portal is up
        stb_api = current_app.stb_api
        
        # Check if portal is enabled
        if not portal.get('enabled', False):
            status = 'disabled'
        else:
            # Use a dummy MAC to test connection
            mac = portal.get('mac', '00:1A:79:00:00:00').lower().replace(':', '').replace('-', '')
            
            # Try to get a token - this will check if portal is reachable
            try:
                token = stb_api.get_token(portal_id, mac)
                status = 'up' if token else 'down'
            except Exception:
                status = 'down'
                
        # Send portal status to client
        portal_status = {
            'portal_id': portal_id,
            'name': portal.get('name', 'Unknown Portal'),
            'status': status,
            'connections': connections
        }
        
        socketio.emit('portal_status_update', portal_status) 