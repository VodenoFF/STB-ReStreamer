"""
Channel editor route handlers for STB-ReStreamer.
Provides an integrated interface for managing channels across all portals.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, session

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
editor_bp = Blueprint('editor', __name__)

@editor_bp.route('/editor')
def editor():
    """
    Render the channel editor page.
    
    Returns:
        Rendered template or redirect to login
    """
    # Check authentication
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get channel group manager
    channel_group_manager = current_app.channel_group_manager
    
    # Get all groups
    groups = channel_group_manager.get_all_groups()
    
    # Get portal manager
    portal_manager = current_app.portal_manager
    
    # Get all portals
    portals = portal_manager.get_all_portals()
    
    # Render template
    return render_template(
        'editor/index.html',
        title='Channel Editor',
        channel_groups=groups,
        portals=portals
    )

@editor_bp.route('/editor_data')
def editor_data():
    """
    Get channel data for the editor.
    
    Returns:
        JSON response with channel data
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
    
    channels = []
    error_messages = []
    
    try:
        # Get managers
        logger.debug("Getting application managers")
        portal_manager = current_app.portal_manager
        channel_group_manager = current_app.channel_group_manager
        category_manager = current_app.category_manager
        stb_api = current_app.stb_api
        
        # Get all portals
        logger.debug("Retrieving all portals")
        portals = portal_manager.get_all_portals()
        if not portals:
            logger.warning("No portals found in the system")
            return jsonify({"data": [], "warnings": ["No portals found"]}), 200
        
        # Get all groups
        logger.debug("Retrieving all channel groups")
        channel_groups = channel_group_manager.get_all_groups()
        
        # Debug portal info
        logger.debug(f"Found {len(portals)} portals")
        
        # Iterate over enabled portals to get channels
        portal_count = 0
        for portal_id, portal in portals.items():
            try:
                # Check if portal is a dictionary before proceeding
                if not isinstance(portal, dict):
                    error_msg = f"Portal {portal_id} is not a dictionary: {type(portal)}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)
                    continue
                    
                # Debug portal being processed
                logger.debug(f"Processing portal: {portal_id}")
                    
                if portal.get('enabled', False):
                    portal_count += 1
                    logger.debug(f"Portal {portal_id} is enabled")
                    portal_id = portal.get('id', portal_id)  # Use the portal id from the portal or fallback to dictionary key
                    portal_name = portal.get('name', 'Unknown Portal')
                    
                    # Get MAC address
                    mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
                    if not mac:
                        # Use default MAC if not set
                        mac = '00:1A:79:00:00:00'.lower().replace(':', '').replace('-', '')
                    
                    logger.debug(f"Using MAC: {mac} for portal: {portal_id}")
                    
                    # Get custom settings from portal
                    enabled_channels = []
                    custom_channel_names = {}
                    custom_genres = {}
                    custom_channel_numbers = {}
                    custom_epg_ids = {}
                    
                    # Legacy format compatibility
                    if 'enabled channels' in portal:
                        enabled_channels = portal.get('enabled channels', [])
                    
                    if 'custom channel names' in portal:
                        custom_channel_names = portal.get('custom channel names', {})
                    
                    if 'custom genres' in portal:
                        custom_genres = portal.get('custom genres', {})
                    
                    if 'custom channel numbers' in portal:
                        custom_channel_numbers = portal.get('custom channel numbers', {})
                    
                    if 'custom epg ids' in portal:
                        custom_epg_ids = portal.get('custom epg ids', {})
                    
                    # Get channels for this portal
                    logger.debug(f"Retrieving channels for portal: {portal_id}")
                    try:
                        portal_channels = stb_api.get_channels(portal_id, mac)
                        logger.debug(f"Retrieved {len(portal_channels)} channels for portal: {portal_id}")
                    except Exception as channel_err:
                        error_msg = f"Error retrieving channels for portal {portal_id}: {str(channel_err)}"
                        logger.error(error_msg)
                        error_messages.append(error_msg)
                        portal_channels = []
                    
                    # Get genre data if available
                    genres = {}
                    try:
                        data_dir = current_app.config_manager.get_data_dir()
                        genre_path = os.path.join(data_dir, f"{portal_name}_genre.json")
                        if os.path.exists(genre_path):
                            with open(genre_path, 'r', encoding='utf-8') as f:
                                genres = json.load(f)
                            logger.debug(f"Loaded genre data for {portal_name}")
                    except Exception as e:
                        error_msg = f"Error loading genre data for {portal_name}: {str(e)}"
                        logger.error(error_msg)
                        error_messages.append(error_msg)
                    
                    # Process channels
                    channel_count = 0
                    for channel in portal_channels:
                        try:
                            # Check if channel is a dictionary before proceeding
                            if not isinstance(channel, dict):
                                error_msg = f"Channel in portal {portal_id} is not a dictionary: {type(channel)}"
                                logger.warning(error_msg)
                                error_messages.append(error_msg)
                                continue
                                
                            channel_id = str(channel.get('id', ''))
                            if not channel_id:
                                logger.warning(f"Skipping channel with no ID in portal {portal_id}")
                                continue
                            
                            channel_count += 1
                            
                            # Default values
                            channel_number = str(channel.get('number', ''))
                            channel_name = str(channel.get('name', ''))
                            
                            # Try to get genre from portal data
                            genre = ''
                            if 'tv_genre_id' in channel and str(channel['tv_genre_id']) in genres:
                                genre = genres[str(channel['tv_genre_id'])]
                            elif 'genre' in channel:
                                genre = channel['genre']
                            
                            # Determine if channel is enabled
                            # If 'enabled channels' list exists and has entries, check if this channel is in the list
                            # If list is empty or doesn't exist, consider all channels enabled
                            enabled = True
                            if 'enabled channels' in portal and len(enabled_channels) > 0:
                                enabled = channel_id in enabled_channels
                                
                            # Log the enabled status for debugging
                            logger.debug(f"Channel {channel_id} ({channel_name}) in portal {portal_id} enabled: {enabled}. " +
                                      f"'enabled channels' exists: {'enabled channels' in portal}, " +
                                      f"'enabled channels' length: {len(enabled_channels)}")
                            
                            # Get custom values if set
                            custom_channel_number = custom_channel_numbers.get(channel_id, '')
                            custom_channel_name = custom_channel_names.get(channel_id, '')
                            custom_genre = custom_genres.get(channel_id, '')
                            custom_epg_id = custom_epg_ids.get(channel_id, '')
                            
                            # Determine the group for this channel
                            group = ''
                            try:
                                for group_name, group_data in channel_groups.items():
                                    for ch in group_data:
                                        if isinstance(ch, dict) and ch.get('channelId') == channel_id and ch.get('portalId') == portal_id:
                                            group = group_name
                                            break
                                    if group:
                                        break
                            except Exception as group_err:
                                error_msg = f"Error determining group for channel {channel_id}: {str(group_err)}"
                                logger.error(error_msg)
                                error_messages.append(error_msg)
                            
                            # Build stream URL
                            host = request.host
                            stream_link = f"http://{host}/stream/{portal_id}/{mac}/{channel_id}"
                            preview_link = f"http://{host}/preview/{portal_id}/{mac}/{channel_id}"
                            
                            # Add channel to list
                            channels.append({
                                "portal": portal_id,
                                "portalName": portal_name,
                                "enabled": enabled,
                                "channelNumber": channel_number,
                                "customChannelNumber": custom_channel_number,
                                "channelName": channel_name,
                                "customChannelName": custom_channel_name,
                                "genre": genre,
                                "customGenre": custom_genre,
                                "channelId": channel_id,
                                "customEpgId": custom_epg_id,
                                "group": group,
                                "link": preview_link,
                                "streamLink": stream_link
                            })
                        except Exception as ch_err:
                            error_msg = f"Error processing channel in portal {portal_id}: {str(ch_err)}"
                            logger.error(error_msg)
                            error_messages.append(error_msg)
                    
                    logger.debug(f"Processed {channel_count} channels for portal {portal_id}")
                else:
                    logger.debug(f"Skipping disabled portal: {portal_id}")
            except Exception as p_err:
                error_msg = f"Error processing portal {portal_id}: {str(p_err)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                continue
        
        logger.info(f"Editor data: processed {portal_count} enabled portals with a total of {len(channels)} channels")
        if error_messages:
            logger.warning(f"Editor data: encountered {len(error_messages)} errors/warnings")
    
    except Exception as e:
        error_msg = f"Error generating editor data: {str(e)}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        return jsonify({"error": error_msg, "data": [], "errors": error_messages}), 500
    
    # Return the channel data with any error messages for debugging
    return jsonify({
        "data": channels,
        "totalChannels": len(channels),
        "warnings": error_messages if error_messages else None
    })

@editor_bp.route('/editor/save', methods=['POST'])
def editor_save():
    """
    Save changes from the editor.
    
    Returns:
        Redirect to editor page
    """
    # Check authentication
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    try:
        # Parse form data
        enabled_edits = json.loads(request.form.get("enabledEdits", "[]"))
        number_edits = json.loads(request.form.get("numberEdits", "[]"))
        name_edits = json.loads(request.form.get("nameEdits", "[]"))
        genre_edits = json.loads(request.form.get("genreEdits", "[]"))
        epg_edits = json.loads(request.form.get("epgEdits", "[]"))
        group_edits = json.loads(request.form.get("groupEdits", "[]"))
        
        # Get managers
        portal_manager = current_app.portal_manager
        channel_group_manager = current_app.channel_group_manager
        
        # Get all portals and groups
        portals = {}
        for portal in portal_manager.get_all_portals():
            portals[portal.get('id')] = portal
        
        channel_groups = channel_group_manager.get_all_groups()
        
        # Helper function to update portal settings
        def update_portal(portal_id, key, value, channel_id):
            if portal_id not in portals:
                return
                
            portal = portals[portal_id]
            
            if key == "enabled":
                # Get current portal channels
                mac = portal.get('mac', '').lower().replace(':', '').replace('-', '')
                if not mac:
                    mac = '00:1A:79:00:00:00'.lower().replace(':', '').replace('-', '')
                    
                portal_channels = []
                try:
                    portal_channels = stb_api.get_channels(portal_id, mac)
                except Exception as e:
                    logger.error(f"Error getting channels for portal {portal_id}: {e}")
                
                # Initialize enabled channels list if needed
                if "enabled channels" not in portal:
                    portal["enabled channels"] = []
                
                if value:  # Enable this channel
                    if channel_id not in portal["enabled channels"]:
                        portal["enabled channels"].append(channel_id)
                else:  # Disable this channel
                    if channel_id in portal["enabled channels"]:
                        portal["enabled channels"].remove(channel_id)
                
                # If all channels are enabled, remove the list entirely for better performance
                if len(portal_channels) > 0 and len(portal["enabled channels"]) == len(portal_channels):
                    del portal["enabled channels"]
                    logger.debug(f"All channels enabled for portal {portal_id}, removed 'enabled channels' list")
            
            elif key == "custom_number":
                if "custom channel numbers" not in portal:
                    portal["custom channel numbers"] = {}
                
                if value:
                    portal["custom channel numbers"][channel_id] = value
                else:
                    if channel_id in portal["custom channel numbers"]:
                        del portal["custom channel numbers"][channel_id]
            
            elif key == "custom_name":
                if "custom channel names" not in portal:
                    portal["custom channel names"] = {}
                
                if value:
                    portal["custom channel names"][channel_id] = value
                else:
                    if channel_id in portal["custom channel names"]:
                        del portal["custom channel names"][channel_id]
            
            elif key == "custom_genre":
                if "custom genres" not in portal:
                    portal["custom genres"] = {}
                
                if value:
                    portal["custom genres"][channel_id] = value
                else:
                    if channel_id in portal["custom genres"]:
                        del portal["custom genres"][channel_id]
            
            elif key == "custom_epg_id":
                if "custom epg ids" not in portal:
                    portal["custom epg ids"] = {}
                
                if value:
                    portal["custom epg ids"][channel_id] = value
                else:
                    if channel_id in portal["custom epg ids"]:
                        del portal["custom epg ids"][channel_id]
        
        # Process enabled/disabled edits
        for edit in enabled_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            enabled = edit.get("enabled")
            update_portal(portal_id, "enabled", enabled, channel_id)
        
        # Process custom number edits
        for edit in number_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            custom_number = edit.get("custom number")
            update_portal(portal_id, "custom_number", custom_number, channel_id)
        
        # Process custom name edits
        for edit in name_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            custom_name = edit.get("custom name")
            update_portal(portal_id, "custom_name", custom_name, channel_id)
        
        # Process custom genre edits
        for edit in genre_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            custom_genre = edit.get("custom genre")
            update_portal(portal_id, "custom_genre", custom_genre, channel_id)
        
        # Process custom EPG ID edits
        for edit in epg_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            custom_epg_id = edit.get("custom epg id")
            update_portal(portal_id, "custom_epg_id", custom_epg_id, channel_id)
        
        # Process group edits
        for edit in group_edits:
            portal_id = edit.get("portal")
            channel_id = edit.get("channel id")
            group_name = edit.get("group")
            
            # Remove channel from all existing groups first
            for g_name, g_channels in channel_groups.items():
                channel_groups[g_name] = [
                    ch for ch in g_channels
                    if not (isinstance(ch, dict) and
                            ch.get("channelId") == channel_id and
                            ch.get("portalId") == portal_id)
                ]
            
            # Add to new group if one is selected
            if group_name:
                if group_name not in channel_groups:
                    channel_groups[group_name] = []
                
                # Add as dict with both channelId and portalId
                channel_entry = {
                    "channelId": channel_id,
                    "portalId": portal_id
                }
                
                if channel_entry not in channel_groups[group_name]:
                    channel_groups[group_name].append(channel_entry)
        
        # Save changes to portals
        for portal_id, portal in portals.items():
            portal_manager.add_portal(portal_id, portal)
        
        # Save changes to channel groups
        for group_name, group_channels in channel_groups.items():
            channel_group_manager.update_group(group_name, group_channels)
        
        # Log success
        logger.info("Channel editor changes saved successfully")
        flash("Channel editor changes saved successfully", "success")
    
    except Exception as e:
        logger.error(f"Error saving editor changes: {str(e)}")
        flash(f"Error saving changes: {str(e)}", "danger")
    
    return redirect(url_for('editor.editor'))

@editor_bp.route('/editor/reset', methods=['POST'])
def editor_reset():
    """
    Reset all channel customizations.
    
    Returns:
        Redirect to editor page
    """
    # Check authentication
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    try:
        # Get all portals
        portal_manager = current_app.portal_manager
        
        for portal in portal_manager.get_all_portals():
            portal_id = portal.get('id')
            
            # Reset customizations
            if 'enabled channels' in portal:
                del portal['enabled channels']
            
            if 'custom channel names' in portal:
                portal['custom channel names'] = {}
            
            if 'custom genres' in portal:
                portal['custom genres'] = {}
            
            if 'custom channel numbers' in portal:
                portal['custom channel numbers'] = {}
            
            if 'custom epg ids' in portal:
                portal['custom epg ids'] = {}
            
            # Save changes
            portal_manager.add_portal(portal_id, portal)
        
        # Log success
        logger.info("Channel editor reset successful")
        flash("All channel customizations have been reset", "success")
    
    except Exception as e:
        logger.error(f"Error resetting editor changes: {str(e)}")
        flash(f"Error resetting changes: {str(e)}", "danger")
    
    return redirect(url_for('editor.editor')) 