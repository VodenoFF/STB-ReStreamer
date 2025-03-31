"""
Channel groups route handlers for STB-ReStreamer.
"""
import logging
from typing import Dict, List, Any
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, session

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/groups')
def list_groups():
    """
    Render the channel groups list page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get all groups
    groups = channel_group_manager.get_all_groups()
    
    # Render template
    return render_template(
        'groups/list.html',
        title='Channel Groups',
        groups=groups
    )

@groups_bp.route('/groups/add', methods=['GET', 'POST'])
def add_group():
    """
    Handle add group requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        channels = request.form.getlist('channels')
        
        # Validate required fields
        if not name:
            flash('Group name is required', 'danger')
            return render_template(
                'groups/add.html',
                title='Add Channel Group',
                form_data=request.form
            )
        
        # Get channel group manager
        channel_group_manager = current_app.channel_group_manager
        
        # Check if group already exists
        if channel_group_manager.get_group(name):
            flash(f'Group "{name}" already exists', 'danger')
            return render_template(
                'groups/add.html',
                title='Add Channel Group',
                form_data=request.form
            )
        
        # Add group
        channel_group_manager.add_group(name, channels)
        
        # Log and redirect
        logger.info(f"Added new channel group: {name} with {len(channels)} channels")
        flash(f'Channel group "{name}" added successfully', 'success')
        return redirect(url_for('groups.list_groups'))
    
    # GET request - render form
    # Get all channels from all portals
    stb_api = current_app.stb_api
    portal_manager = current_app.portal_manager
    
    all_channels = []
    for portal in portal_manager.get_enabled_portals():
        portal_id = portal.get('id')
        mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
        
        if mac:
            portal_channels = stb_api.get_channels(portal_id, mac)
            for channel in portal_channels:
                channel['portal_id'] = portal_id
                channel['portal_name'] = portal.get('name', 'Unknown')
                all_channels.append(channel)
    
    return render_template(
        'groups/add.html',
        title='Add Channel Group',
        channels=all_channels
    )

@groups_bp.route('/groups/edit/<group_name>', methods=['GET', 'POST'])
def edit_group(group_name):
    """
    Handle edit group requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get group
    group = channel_group_manager.get_group(group_name)
    if not group:
        flash('Channel group not found', 'danger')
        return redirect(url_for('groups.list_groups'))
    
    if request.method == 'POST':
        # Get form data
        new_name = request.form.get('name', '').strip()
        channels = request.form.getlist('channels')
        
        # Validate required fields
        if not new_name:
            flash('Group name is required', 'danger')
            return render_template(
                'groups/edit.html',
                title='Edit Channel Group',
                group_name=group_name,
                channels_in_group=group
            )
        
        # Check if new name already exists (if changed)
        if new_name != group_name and channel_group_manager.get_group(new_name):
            flash(f'Group "{new_name}" already exists', 'danger')
            return render_template(
                'groups/edit.html',
                title='Edit Channel Group',
                group_name=group_name,
                channels_in_group=group
            )
        
        # Update group
        if new_name != group_name:
            # Delete old group and add new one with updated name
            channel_group_manager.delete_group(group_name)
            channel_group_manager.add_group(new_name, channels)
        else:
            # Update existing group
            channel_group_manager.update_group(group_name, channels)
        
        # Log and redirect
        logger.info(f"Updated channel group: {new_name} with {len(channels)} channels")
        flash(f'Channel group "{new_name}" updated successfully', 'success')
        return redirect(url_for('groups.list_groups'))
    
    # GET request - render form
    # Get all channels from all portals
    stb_api = current_app.stb_api
    portal_manager = current_app.portal_manager
    
    all_channels = []
    for portal in portal_manager.get_enabled_portals():
        portal_id = portal.get('id')
        mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
        
        if mac:
            portal_channels = stb_api.get_channels(portal_id, mac)
            for channel in portal_channels:
                channel['portal_id'] = portal_id
                channel['portal_name'] = portal.get('name', 'Unknown')
                all_channels.append(channel)
    
    return render_template(
        'groups/edit.html',
        title='Edit Channel Group',
        group_name=group_name,
        channels_in_group=group,
        channels=all_channels
    )

@groups_bp.route('/groups/delete/<group_name>', methods=['POST'])
def delete_group(group_name):
    """
    Handle delete group requests.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Delete group
    channel_group_manager.delete_group(group_name)
    
    # Log and redirect
    logger.info(f"Deleted channel group: {group_name}")
    flash(f'Channel group "{group_name}" deleted successfully', 'success')
    return redirect(url_for('groups.list_groups'))

@groups_bp.route('/api/groups')
def api_groups():
    """
    API endpoint for channel groups list.
    
    Returns:
        Dict: JSON response with groups information
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
        
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get groups
    groups = channel_group_manager.get_all_groups()
    
    # Format as list
    groups_list = []
    for name, channels in groups.items():
        groups_list.append({
            'name': name,
            'channel_count': len(channels),
            'channels': channels
        })
    
    return jsonify({
        'groups': groups_list,
        'count': len(groups_list)
    })