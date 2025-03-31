"""
HDHomeRun emulation route handlers for STB-ReStreamer.
Implements routes needed to emulate a HDHomeRun device for software like Plex.
"""
import os
import json
import uuid
import logging
import socket
from typing import Dict, List, Any
from flask import Blueprint, jsonify, request, current_app, abort

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
hdhr_bp = Blueprint('hdhr', __name__)

# Constants for HDHR emulation
HDHR_ID = '12345678'  # Default device ID
HDHR_VERSION = '20200225'
HDHR_TUNER_COUNT = 4  # Number of tuners to emulate

@hdhr_bp.route('/discover.json')
def hdhr_discover():
    """
    Handle HDHomeRun discover.json request.
    Returns information about the emulated HDHomeRun device.
    """
    # Get configuration manager
    config_manager = current_app.config_manager
    
    # Get server host and port
    server_host = request.host.split(':')[0]
    server_port = config_manager.get_setting("port", 8001)
    
    # Get device id from config or use default
    device_id = config_manager.get_setting("hdhr_device_id", HDHR_ID)
    
    # Construct device information
    device_info = {
        "FriendlyName": "STB-ReStreamer",
        "ModelNumber": "HDHR3-CC",
        "FirmwareName": "STB-ReStreamer",
        "FirmwareVersion": HDHR_VERSION,
        "DeviceID": device_id,
        "DeviceAuth": "STB-ReStreamer",
        "BaseURL": f"http://{server_host}:{server_port}",
        "LineupURL": f"http://{server_host}:{server_port}/lineup.json",
        "TunerCount": HDHR_TUNER_COUNT
    }
    
    logger.debug(f"HDHR discover request from {request.remote_addr}")
    return jsonify(device_info)

@hdhr_bp.route('/lineup_status.json')
def hdhr_lineup_status():
    """
    Handle HDHomeRun lineup_status.json request.
    Returns the status of the channel scan.
    """
    # There's no actual scan happening, just pretend it's complete
    status = {
        "ScanInProgress": 0,
        "ScanPossible": 1,
        "Source": "Cable",
        "SourceList": ["Cable"]
    }
    
    logger.debug(f"HDHR lineup status request from {request.remote_addr}")
    return jsonify(status)

@hdhr_bp.route('/lineup.json')
def hdhr_lineup():
    """
    Handle HDHomeRun lineup.json request.
    Returns the list of available channels.
    """
    try:
        # Get managers
        config_manager = current_app.config_manager
        portal_manager = current_app.portal_manager
        
        # Get server host and port
        server_host = request.host.split(':')[0]
        server_port = config_manager.get_setting("port", 8001)
        
        # Get enabled portals
        portals = portal_manager.get_enabled_portals()
        
        # Get channel groups manager
        channel_group_manager = current_app.channel_group_manager
        
        # Check if filtering by group is enabled
        hdhr_filter_groups = config_manager.get_setting("hdhr_filter_groups", False)
        hdhr_groups = config_manager.get_setting("hdhr_groups", [])
        
        # Get STB API service
        stb_api = current_app.stb_api
        
        # Build lineup
        lineup = []
        channel_number = 1
        
        for portal in portals:
            portal_id = portal.get('id')
            mac = portal.get('mac', '')
            
            # Skip if portal has no MAC
            if not mac:
                continue
                
            # Normalize MAC
            mac = mac.lower().replace(':', '').replace('-', '')
            
            # Get channels for this portal
            channels = stb_api.get_channels(portal_id, mac)
            
            for channel in channels:
                channel_id = channel.get('id')
                channel_name = channel.get('name', 'Unknown')
                channel_number_orig = channel.get('number', channel_number)
                
                # Skip if filtering by groups is enabled and channel not in selected groups
                if hdhr_filter_groups and hdhr_groups:
                    channel_groups = channel_group_manager.get_channel_in_groups(channel_id)
                    if not any(group in hdhr_groups for group in channel_groups):
                        continue
                
                # Add channel to lineup
                url = f"http://{server_host}:{server_port}/stream/{portal_id}/{mac}/{channel_id}"
                
                lineup.append({
                    "GuideNumber": str(channel_number_orig),
                    "GuideName": channel_name,
                    "URL": url,
                    "HD": 1,  # Assume HD
                    "Favorite": 0
                })
                
                channel_number += 1
        
        logger.debug(f"HDHR lineup request from {request.remote_addr}, returned {len(lineup)} channels")
        return jsonify(lineup)
        
    except Exception as e:
        logger.error(f"Error generating HDHR lineup: {str(e)}")
        return jsonify([])

@hdhr_bp.route('/device.xml')
def hdhr_device_xml():
    """
    Handle HDHomeRun device.xml request.
    Returns XML description of the emulated device.
    """
    # Get configuration manager
    config_manager = current_app.config_manager
    
    # Get server host and port
    server_host = request.host.split(':')[0]
    server_port = config_manager.get_setting("port", 8001)
    
    # Get device id from config or use default
    device_id = config_manager.get_setting("hdhr_device_id", HDHR_ID)
    
    # XML response
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
        <friendlyName>STB-ReStreamer</friendlyName>
        <manufacturer>STB-ReStreamer</manufacturer>
        <manufacturerURL>https://github.com/</manufacturerURL>
        <modelDescription>HDHomeRun Emulation</modelDescription>
        <modelName>HDHR3-CC</modelName>
        <modelNumber>{HDHR_VERSION}</modelNumber>
        <modelURL>https://github.com/</modelURL>
        <serialNumber>{device_id}</serialNumber>
        <UDN>uuid:{device_id}</UDN>
    </device>
</root>"""
    
    logger.debug(f"HDHR device.xml request from {request.remote_addr}")
    return xml, 200, {'Content-Type': 'text/xml'}

@hdhr_bp.route('/api/hdhr/device-status')
def api_hdhr_device_status():
    """
    API endpoint for HDHR device status.
    
    Returns:
        Dict: JSON response with device status
    """
    # Get configuration manager
    config_manager = current_app.config_manager
    
    # Get HDHR configuration
    hdhr_device_id = config_manager.get_setting("hdhr_device_id", HDHR_ID)
    hdhr_tuner_count = config_manager.get_setting("hdhr_tuner_count", HDHR_TUNER_COUNT)
    hdhr_filter_groups = config_manager.get_setting("hdhr_filter_groups", False)
    hdhr_groups = config_manager.get_setting("hdhr_groups", [])
    
    # Get local IP addresses
    local_ips = []
    try:
        hostname = socket.gethostname()
        local_ips = [ip for ip in socket.gethostbyname_ex(hostname)[2] if not ip.startswith("127.")]
    except Exception as e:
        logger.error(f"Error getting local IP addresses: {str(e)}")
    
    # Return device status
    return jsonify({
        "device_id": hdhr_device_id,
        "tuner_count": hdhr_tuner_count,
        "filter_groups": hdhr_filter_groups,
        "selected_groups": hdhr_groups,
        "local_ips": local_ips,
        "version": HDHR_VERSION
    })