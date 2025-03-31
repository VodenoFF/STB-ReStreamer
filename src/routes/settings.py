"""
Settings route handlers for STB-ReStreamer.
"""
import logging
import os
import json
from typing import Dict, Any
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, session

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def general_settings():
    """
    Handle general settings page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get configuration manager
    config_manager = current_app.config_manager
    
    if request.method == 'POST':
        # Get form data
        port = int(request.form.get('port', 8001))
        admin_username = request.form.get('admin_username', 'admin').strip()
        admin_password = request.form.get('admin_password', '').strip()
        ffmpeg_path = request.form.get('ffmpeg_path', '').strip()
        cache_size = int(request.form.get('cache_size', 1000))
        cache_ttl = int(request.form.get('cache_ttl', 8))
        log_level = request.form.get('log_level', 'INFO').strip()
        stream_timeout = int(request.form.get('stream_timeout', 30))
        
        # Validate
        if port < 1 or port > 65535:
            flash('Port must be between 1 and 65535', 'danger')
            return redirect(url_for('settings.general_settings'))
            
        if not admin_username:
            flash('Admin username cannot be empty', 'danger')
            return redirect(url_for('settings.general_settings'))
            
        # Only update password if provided (don't overwrite with empty)
        current_settings = config_manager.get_all_settings()
        
        # Update settings
        settings = {
            'port': port,
            'admin_username': admin_username,
            'ffmpeg_path': ffmpeg_path,
            'cache_size': cache_size,
            'cache_ttl': cache_ttl,
            'log_level': log_level,
            'stream_timeout': stream_timeout
        }
        
        # Only update password if provided
        if admin_password:
            settings['admin_password'] = admin_password
        
        # Update settings
        for key, value in settings.items():
            config_manager.set_setting(key, value)
            
        # Save changes
        config_manager.save_settings()
        
        # Apply changes to runtime
        if cache_size != current_settings.get('cache_size', 1000) or cache_ttl != current_settings.get('cache_ttl', 8):
            # Update link cache settings
            current_app.link_cache.max_size = cache_size
            current_app.link_cache.default_ttl = cache_ttl * 3600  # Convert to seconds
        
        # Set log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        
        # Log and redirect
        logger.info("Settings updated")
        flash('Settings updated successfully', 'success')
        
        # Note about restart
        if port != current_settings.get('port', 8001) or ffmpeg_path != current_settings.get('ffmpeg_path', ''):
            flash('Some settings require a restart to take effect', 'warning')
            
        return redirect(url_for('settings.general_settings'))
    
    # GET request
    settings = config_manager.get_all_settings()
    
    return render_template(
        'settings/general.html',
        title='General Settings',
        settings=settings
    )

@settings_bp.route('/settings/hdhr', methods=['GET', 'POST'])
def hdhr_settings():
    """
    Handle HDHomeRun emulation settings.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get configuration manager
    config_manager = current_app.config_manager
    
    # Get channel groups manager
    channel_group_manager = current_app.channel_group_manager
    all_groups = channel_group_manager.get_all_groups()
    
    if request.method == 'POST':
        # Get form data
        hdhr_device_id = request.form.get('hdhr_device_id', '12345678').strip()
        hdhr_tuner_count = int(request.form.get('hdhr_tuner_count', 4))
        hdhr_filter_groups = request.form.get('hdhr_filter_groups') == 'on'
        
        # Get selected groups
        hdhr_groups = request.form.getlist('hdhr_groups')
        
        # Validate
        if len(hdhr_device_id) != 8 or not hdhr_device_id.isalnum():
            flash('Device ID must be 8 alphanumeric characters', 'danger')
            return redirect(url_for('settings.hdhr_settings'))
            
        if hdhr_tuner_count < 1 or hdhr_tuner_count > 16:
            flash('Tuner count must be between 1 and 16', 'danger')
            return redirect(url_for('settings.hdhr_settings'))
        
        # Update settings
        settings = {
            'hdhr_device_id': hdhr_device_id,
            'hdhr_tuner_count': hdhr_tuner_count,
            'hdhr_filter_groups': hdhr_filter_groups,
            'hdhr_groups': hdhr_groups
        }
        
        # Update settings
        for key, value in settings.items():
            config_manager.set_setting(key, value)
            
        # Save changes
        config_manager.save_settings()
        
        # Log and redirect
        logger.info("HDHR settings updated")
        flash('HDHR settings updated successfully', 'success')
        return redirect(url_for('settings.hdhr_settings'))
    
    # GET request
    settings = config_manager.get_all_settings()
    
    # Default values
    settings.setdefault('hdhr_device_id', '12345678')
    settings.setdefault('hdhr_tuner_count', 4)
    settings.setdefault('hdhr_filter_groups', False)
    settings.setdefault('hdhr_groups', [])
    
    return render_template(
        'settings/hdhr.html',
        title='HDHomeRun Settings',
        settings=settings,
        all_groups=all_groups
    )

@settings_bp.route('/settings/backup', methods=['GET'])
def backup_settings():
    """
    Create a backup of all settings.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    try:
        # Get managers
        config_manager = current_app.config_manager
        portal_manager = current_app.portal_manager
        channel_group_manager = current_app.channel_group_manager
        
        # Create backup object
        backup = {
            'settings': config_manager.get_all_settings(),
            'portals': portal_manager.get_all_portals(),
            'channel_groups': channel_group_manager.get_all_groups()
        }
        
        # Convert to JSON
        backup_json = json.dumps(backup, indent=2)
        
        # Return as download
        return backup_json, 200, {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename=stb-restreamer-backup.json'
        }
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        flash(f'Error creating backup: {str(e)}', 'danger')
        return redirect(url_for('settings.general_settings'))

@settings_bp.route('/settings/restore', methods=['POST'])
def restore_settings():
    """
    Restore settings from a backup file.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    try:
        # Check if file was uploaded
        if 'backup_file' not in request.files:
            flash('No backup file provided', 'danger')
            return redirect(url_for('settings.general_settings'))
            
        backup_file = request.files['backup_file']
        
        # Check if file is empty
        if backup_file.filename == '':
            flash('No backup file selected', 'danger')
            return redirect(url_for('settings.general_settings'))
            
        # Read and parse JSON
        backup_data = json.loads(backup_file.read())
        
        # Validate backup data
        if not isinstance(backup_data, dict):
            flash('Invalid backup file format', 'danger')
            return redirect(url_for('settings.general_settings'))
            
        # Get managers
        config_manager = current_app.config_manager
        portal_manager = current_app.portal_manager
        channel_group_manager = current_app.channel_group_manager
        
        # Restore settings
        if 'settings' in backup_data and isinstance(backup_data['settings'], dict):
            for key, value in backup_data['settings'].items():
                config_manager.set_setting(key, value)
            config_manager.save_settings()
            
        # Restore portals
        if 'portals' in backup_data and isinstance(backup_data['portals'], list):
            portal_manager.set_all_portals(backup_data['portals'])
            
        # Restore channel groups
        if 'channel_groups' in backup_data and isinstance(backup_data['channel_groups'], dict):
            channel_group_manager.set_all_groups(backup_data['channel_groups'])
            
        # Log and redirect
        logger.info("Settings restored from backup")
        flash('Settings restored successfully', 'success')
        flash('Please restart the application for all settings to take effect', 'warning')
        return redirect(url_for('settings.general_settings'))
        
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        flash(f'Error restoring backup: {str(e)}', 'danger')
        return redirect(url_for('settings.general_settings'))

@settings_bp.route('/api/settings')
def api_settings():
    """
    API endpoint for settings.
    
    Returns:
        Dict: JSON response with settings information
    """
    # Check authentication
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'}), 401
        
    # Get configuration manager
    config_manager = current_app.config_manager
    
    # Get settings
    settings = config_manager.get_all_settings()
    
    # Remove sensitive information
    if 'admin_password' in settings:
        settings['admin_password'] = '********'
    
    return jsonify({
        'settings': settings
    })