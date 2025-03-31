"""
Portal management route handlers for STB-ReStreamer.
"""
import logging
import uuid
from typing import Dict, List, Any, Optional
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, session, abort

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
portals_bp = Blueprint('portals', __name__)

@portals_bp.route('/portals')
def list_portals():
    """
    Render the portals list page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get all portals
    portals = portal_manager.get_all_portals()
    
    # Get MAC manager for usage info
    mac_manager = current_app.mac_manager
    occupied_macs = mac_manager.get_occupied_macs()
    
    # Count active connections per portal
    portal_connections = {}
    for mac_info in occupied_macs.values():
        portal_id = mac_info.get('portal_id')
        if portal_id:
            portal_connections[portal_id] = portal_connections.get(portal_id, 0) + 1
    
    # Render template
    return render_template(
        'portals/list.html',
        title='IPTV Portals',
        portals=portals,
        portal_connections=portal_connections
    )

@portals_bp.route('/portals/add', methods=['GET', 'POST'])
def add_portal():
    """
    Handle add portal requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        url = request.form.get('url', '').strip()
        portal_type = request.form.get('type', 'stalker').strip().lower()
        mac = request.form.get('mac', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        proxy = request.form.get('proxy', '').strip()
        enabled = request.form.get('enabled') == 'on'
        max_connections = int(request.form.get('max_connections', 1))
        
        # Get type-specific fields
        epg_url = request.form.get('epg_url', '').strip()
        refresh_interval = int(request.form.get('refresh_interval', 24))
        use_catchup = request.form.get('use_catchup') == 'on'
        use_dvr = request.form.get('use_dvr') == 'on'
        
        # Validate required fields
        if not name or not url:
            flash('Name and URL are required', 'danger')
            return render_template(
                'portals/add.html',
                title='Add Portal',
                form_data=request.form
            )
        
        # Create portal object
        portal = {
            'id': str(uuid.uuid4()),
            'name': name,
            'url': url,
            'type': portal_type,  # Add portal type
            'mac': mac,
            'username': username,
            'password': password,
            'proxy': proxy if proxy else None,
            'enabled': enabled,
            'max_connections': max_connections
        }
        
        # Add type-specific fields
        if portal_type == 'm3u':
            portal['epg_url'] = epg_url
            portal['refresh_interval'] = refresh_interval
        elif portal_type == 'xcupdates':
            portal['use_catchup'] = use_catchup
            portal['use_dvr'] = use_dvr
        
        # Add portal
        portal_manager = current_app.portal_manager
        portal_id = portal['id']  # Extract the portal ID
        portal_manager.add_portal(portal_id, portal)  # Pass the ID and portal data separately
        
        # Log and redirect
        logger.info(f"Added new {portal_type} portal: {name}")
        flash(f'Portal "{name}" added successfully', 'success')
        return redirect(url_for('portals.list_portals'))
    
    # GET request - render form
    return render_template(
        'portals/add.html',
        title='Add Portal',
        form_data={}  # Add empty form_data dictionary to prevent template errors
    )

@portals_bp.route('/portals/edit/<portal_id>', methods=['GET', 'POST'])
def edit_portal(portal_id):
    """
    Handle edit portal requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get portal
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        flash('Portal not found', 'danger')
        return redirect(url_for('portals.list_portals'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        url = request.form.get('url', '').strip()
        portal_type = request.form.get('type', 'stalker').strip().lower()
        mac = request.form.get('mac', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        proxy = request.form.get('proxy', '').strip()
        enabled = request.form.get('enabled') == 'on'
        max_connections = int(request.form.get('max_connections', 1))
        
        # Get type-specific fields
        epg_url = request.form.get('epg_url', '').strip()
        refresh_interval = int(request.form.get('refresh_interval', 24))
        use_catchup = request.form.get('use_catchup') == 'on'
        use_dvr = request.form.get('use_dvr') == 'on'
        
        # Validate required fields
        if not name or not url:
            flash('Name and URL are required', 'danger')
            return render_template(
                'portals/edit.html',
                title='Edit Portal',
                portal=portal
            )
        
        # Update portal object
        portal['name'] = name
        portal['url'] = url
        portal['type'] = portal_type  # Update portal type
        portal['mac'] = mac
        portal['username'] = username
        portal['password'] = password
        portal['proxy'] = proxy if proxy else None
        portal['enabled'] = enabled
        portal['max_connections'] = max_connections
        
        # Update type-specific fields
        if portal_type == 'm3u':
            portal['epg_url'] = epg_url
            portal['refresh_interval'] = refresh_interval
        elif portal_type == 'xcupdates':
            portal['use_catchup'] = use_catchup
            portal['use_dvr'] = use_dvr
        
        # Update portal
        portal_manager.add_portal(portal_id, portal)  # Use add_portal method instead of update_portal
        
        # Log and redirect
        logger.info(f"Updated {portal_type} portal: {name}")
        flash(f'Portal "{name}" updated successfully', 'success')
        return redirect(url_for('portals.list_portals'))
    
    # GET request - render form
    return render_template(
        'portals/edit.html',
        title='Edit Portal',
        portal=portal
    )

@portals_bp.route('/portals/delete/<portal_id>', methods=['POST'])
def delete_portal(portal_id):
    """
    Handle delete portal requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get portal
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        flash('Portal not found', 'danger')
        return redirect(url_for('portals.list_portals'))
    
    # Delete portal
    portal_manager.delete_portal(portal_id)
    
    # Log and redirect
    logger.info(f"Deleted portal: {portal['name']}")
    flash(f'Portal "{portal["name"]}" deleted successfully', 'success')
    return redirect(url_for('portals.list_portals'))

@portals_bp.route('/portals/toggle/<portal_id>', methods=['POST'])
def toggle_portal(portal_id):
    """
    Toggle portal enabled/disabled status.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get portal
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        flash('Portal not found', 'danger')
        return redirect(url_for('portals.list_portals'))
    
    # Toggle enabled status
    portal['enabled'] = not portal.get('enabled', False)
    portal_manager.add_portal(portal_id, portal)  # Use add_portal method instead of update_portal
    
    # Log and redirect
    status = "enabled" if portal['enabled'] else "disabled"
    logger.info(f"Portal {portal['name']} {status}")
    flash(f'Portal "{portal["name"]}" {status}', 'success')
    return redirect(url_for('portals.list_portals'))

@portals_bp.route('/portals/test/<portal_id>', methods=['POST'])
def test_portal(portal_id):
    """
    Test portal connection.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get portal
    portal = portal_manager.get_portal(portal_id)
    if not portal:
        return jsonify({'success': False, 'error': 'Portal not found'}), 404
    
    # Get STB API service
    stb_api = current_app.stb_api
    
    try:
        # Test getting a token
        mac = portal.get('mac', '00:1A:79:00:00:00').lower().replace(':', '').replace('-', '')
            
        # Test authentication
        token = stb_api.get_token(portal_id, mac)
        if not token:
            return jsonify({'success': False, 'error': 'Failed to authenticate with portal'}), 400
            
        # Try to get profile and channels
        profile = stb_api.get_profile(portal_id, mac)
        channels = stb_api.get_channels(portal_id, mac)
        
        # Build response with info
        portal_type = portal.get('type', 'stalker')
        channel_count = len(channels) if channels else 0
        
        message = f"Successfully connected to {portal_type.title()} portal. "
        if profile:
            message += f"Account status: {profile.get('status', 'unknown')}. "
        message += f"Found {channel_count} channels."
        
        return jsonify({
            'success': True, 
            'message': message,
            'channelCount': channel_count,
            'profile': profile
        })
    except Exception as e:
        logger.error(f"Error testing portal {portal_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@portals_bp.route('/api/portals')
def api_portals():
    """
    API endpoint for portals list.
    
    Returns:
        Dict: JSON response with portals information
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
        
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get portals
    portals_dict = portal_manager.get_all_portals()
    
    # Get active connections per portal
    mac_manager = current_app.mac_manager
    occupied_macs = mac_manager.get_occupied_macs()
    
    portal_connections = {}
    for mac_info in occupied_macs.values():
        portal_id = mac_info.get('portal_id')
        if portal_id:
            portal_connections[portal_id] = portal_connections.get(portal_id, 0) + 1
    
    # Convert to list and add connection info to portals
    portals_list = []
    for portal_id, portal in portals_dict.items():
        portal_copy = portal.copy()
        portal_copy['active_connections'] = portal_connections.get(portal_id, 0)
        portals_list.append(portal_copy)
    
    return jsonify({
        'portals': portals_list,
        'count': len(portals_list)
    })