"""
EPG management routes for STB-ReStreamer.
"""
import os
import logging
import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
import uuid

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
epg_bp = Blueprint("epg", __name__, url_prefix="/epg")

@epg_bp.route("/", methods=["GET"])
def dashboard():
    """
    Display the EPG management dashboard.
    """
    epg_manager = current_app.epg_manager
    
    # Get settings and stats
    settings = {
        "enabled": epg_manager.get_epg_stats().get('enabled', False),
        "update_interval": epg_manager.get_epg_stats().get('update_interval', 6),
        "cache_days": epg_manager.get_epg_stats().get('cache_days', 3),
        "sources": epg_manager.get_epg_stats().get('sources', []),
    }
    
    stats = epg_manager.get_epg_stats()
    
    # Get a list of all channels to show mappings
    channels = []
    portal_manager = current_app.portal_manager
    portals = portal_manager.get_all_portals()
    
    for portal_id, portal in portals.items():
        try:
            # Use a default MAC address for accessing channels
            mac = "00:1A:79:00:00:00"
            stb_api = current_app.stb_api
            portal_channels = stb_api.get_channels(portal_id, mac)
            
            for channel in portal_channels:
                channel['portal_id'] = portal_id
                channel['portal_name'] = portal.get('name', 'Unknown Portal')
                channels.append(channel)
        except Exception as e:
            logger.error(f"Error getting channels for portal {portal_id}: {str(e)}")
    
    # Sort channels by name
    channels.sort(key=lambda c: c.get('name', '').lower())
    
    # Get current EPG program data for sample channels (first 10)
    sample_channels = channels[:10] if len(channels) > 10 else channels
    now = int(time.time())
    sample_programs = {}
    
    for channel in sample_channels:
        try:
            channel_id = channel.get('id')
            portal_id = channel.get('portal_id')
            
            # Build combined ID for EPG lookup
            epg_channel_id = f"{portal_id}:{channel_id}"
            
            # Get current program
            program = epg_manager.get_current_program(epg_channel_id)
            if program:
                program['channel_name'] = channel.get('name')
                program['channel_logo'] = channel.get('logo')
                sample_programs[epg_channel_id] = program
        except Exception as e:
            logger.error(f"Error getting program for channel {channel.get('name')}: {str(e)}")
    
    return render_template(
        "epg.html",
        settings=settings,
        stats=stats,
        channels=channels,
        sample_programs=sample_programs,
        epg_manager=epg_manager,
        now=now
    )

@epg_bp.route("/toggle", methods=["POST"])
def toggle_epg():
    """
    Toggle EPG enabled/disabled state.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get current state
    current_state = epg_manager.get_epg_stats().get('enabled', False)
    
    # New state is the opposite of current state
    new_state = not current_state
    
    # Update config directly instead of using set_enabled()
    if hasattr(config_manager, 'set'):
        config_manager.set('epg', 'enabled', new_state)
    else:
        # Fallback to simpler config structure
        config = config_manager.get_config()
        if 'epg' not in config:
            config['epg'] = {}
        config['epg']['enabled'] = new_state
        config_manager.save_config()
    
    flash(f"EPG {'enabled' if new_state else 'disabled'}", "success")
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/settings", methods=["POST"])
def update_settings():
    """
    Update EPG settings.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get form data
    update_interval = request.form.get("update_interval", "12")
    cache_days = request.form.get("cache_days", "3")
    
    try:
        update_interval = int(update_interval)
        cache_days = int(cache_days)
        
        # Update config directly instead of using non-existent methods
        if hasattr(config_manager, 'set'):
            config_manager.set('epg', 'update_interval', update_interval)
            config_manager.set('epg', 'cache_days', cache_days)
        else:
            # Fallback to simpler config structure
            config = config_manager.get_config()
            if 'epg' not in config:
                config['epg'] = {}
            config['epg']['update_interval'] = update_interval
            config['epg']['cache_days'] = cache_days
            config_manager.save_config()
        
        flash("EPG settings updated successfully", "success")
    except ValueError:
        flash("Invalid values for update interval or cache days", "error")
    
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/sources/add", methods=["POST"])
def add_source():
    """
    Add a new EPG source.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get form data
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    
    if not name or not url:
        flash("Name and URL are required", "error")
        return redirect(url_for("epg.dashboard"))
    
    # Get existing sources from stats
    sources = epg_manager.get_epg_stats().get('sources', [])
    
    # Create a new source with a unique ID
    new_source = {
        "id": str(uuid.uuid4()),
        "name": name,
        "url": url
    }
    
    # Add to sources list
    sources.append(new_source)
    
    # Update config
    if hasattr(config_manager, 'set'):
        config_manager.set('epg', 'sources', sources)
    else:
        # Fallback to simpler config structure
        config = config_manager.get_config()
        if 'epg' not in config:
            config['epg'] = {}
        config['epg']['sources'] = sources
        config_manager.save_config()
    
    flash(f"EPG source '{name}' added successfully", "success")
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/sources/delete/<source_id>", methods=["POST"])
def delete_source(source_id):
    """
    Delete an EPG source.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get existing sources
    sources = epg_manager.get_epg_stats().get('sources', [])
    
    # Remove source with matching ID
    sources = [s for s in sources if s.get('id') != source_id]
    
    # Update config
    if hasattr(config_manager, 'set'):
        config_manager.set('epg', 'sources', sources)
    else:
        # Fallback to simpler config structure
        config = config_manager.get_config()
        if 'epg' not in config:
            config['epg'] = {}
        config['epg']['sources'] = sources
        config_manager.save_config()
    
    flash("EPG source deleted successfully", "success")
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/update", methods=["POST"])
def update_epg():
    """
    Trigger an immediate EPG update.
    """
    epg_manager = current_app.epg_manager
    
    # Get EPG sources from stats
    sources = epg_manager.get_epg_stats().get('sources', [])
    
    # Try to update from each source
    updated = False
    errors = []
    
    for source in sources:
        source_url = source.get('url')
        if source_url:
            try:
                # Use the update_epg_from_source method which we know exists
                success = epg_manager.update_epg_from_source(source_url)
                if success:
                    updated = True
            except Exception as e:
                errors.append(f"Error updating from {source.get('name')}: {str(e)}")
                logger.error(f"Error updating EPG from source {source_url}: {str(e)}")
    
    if updated:
        flash("EPG update triggered successfully", "success")
    elif errors:
        for error in errors:
            flash(error, "error")
    else:
        flash("No EPG sources to update", "warning")
    
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/map", methods=["POST"])
def map_channel():
    """
    Map a channel to an EPG channel ID.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get form data
    channel_id = request.form.get("channel_id", "")
    epg_channel_id = request.form.get("epg_channel_id", "").strip()
    
    if not channel_id or not epg_channel_id:
        flash("Channel ID and EPG Channel ID are required", "error")
        return redirect(url_for("epg.dashboard"))
    
    # Split combined channel ID (portal_id:channel_id)
    parts = channel_id.split(":")
    if len(parts) != 2:
        flash("Invalid channel ID format", "error")
        return redirect(url_for("epg.dashboard"))
    
    portal_id, ch_id = parts
    
    # Get existing channel mappings from stats
    mappings = epg_manager.get_epg_stats().get('mappings', {})
    
    # Create the mapping key
    mapping_key = f"{portal_id}:{ch_id}"
    
    # Update the mapping
    mappings[mapping_key] = epg_channel_id
    
    # Update config
    if hasattr(config_manager, 'set'):
        config_manager.set('epg', 'mappings', mappings)
    else:
        # Fallback to simpler config structure
        config = config_manager.get_config()
        if 'epg' not in config:
            config['epg'] = {}
        config['epg']['mappings'] = mappings
        config_manager.save_config()
    
    flash(f"Channel mapped to EPG ID '{epg_channel_id}'", "success")
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/unmap/<portal_id>/<channel_id>", methods=["POST"])
def unmap_channel(portal_id, channel_id):
    """
    Remove a channel mapping.
    """
    epg_manager = current_app.epg_manager
    config_manager = current_app.config_manager
    
    # Get existing channel mappings from stats
    mappings = epg_manager.get_epg_stats().get('mappings', {})
    
    # Create the mapping key
    mapping_key = f"{portal_id}:{channel_id}"
    
    # Remove the mapping if it exists
    if mapping_key in mappings:
        del mappings[mapping_key]
    
    # Update config
    if hasattr(config_manager, 'set'):
        config_manager.set('epg', 'mappings', mappings)
    else:
        # Fallback to simpler config structure
        config = config_manager.get_config()
        if 'epg' not in config:
            config['epg'] = {}
        config['epg']['mappings'] = mappings
        config_manager.save_config()
    
    flash("Channel mapping removed", "success")
    return redirect(url_for("epg.dashboard"))

@epg_bp.route("/clear", methods=["POST"])
def clear_epg():
    """
    Clear all EPG data.
    """
    epg_manager = current_app.epg_manager
    
    # Since there's no clear_epg method, we'll need a workaround
    # This is a basic implementation assuming the EPG manager has some form of data storage
    # that we can access and clear
    
    try:
        # If the EPG manager has epg_data attribute, clear it
        if hasattr(epg_manager, 'epg_data'):
            epg_manager.epg_data = {}
            
        # Try to save the empty data
        if hasattr(epg_manager, '_save_epg_data'):
            for source_id in epg_manager.get_epg_stats().get('sources', []):
                source_id = source_id.get('id') if isinstance(source_id, dict) else source_id
                if source_id:
                    epg_manager._save_epg_data(source_id)
        
        flash("EPG data cleared successfully", "success")
    except Exception as e:
        logger.error(f"Error clearing EPG data: {str(e)}")
        flash(f"Error clearing EPG data: {str(e)}", "error")
        
    return redirect(url_for("epg.dashboard"))

# API Routes for frontend AJAX calls

@epg_bp.route("/api/stats", methods=["GET"])
def api_get_stats():
    """
    Get EPG statistics as JSON.
    """
    epg_manager = current_app.epg_manager
    stats = epg_manager.get_epg_stats()
    return jsonify(stats)

@epg_bp.route("/api/program/<portal_id>/<channel_id>", methods=["GET"])
def api_get_current_program(portal_id, channel_id):
    """
    Get current program for a channel as JSON.
    """
    epg_manager = current_app.epg_manager
    
    # Build combined ID for EPG lookup
    epg_channel_id = f"{portal_id}:{channel_id}"
    
    # Get current program
    program = epg_manager.get_current_program(epg_channel_id)
    
    if not program:
        return jsonify({"error": "No program found"})
    
    return jsonify(program)

@epg_bp.route("/api/schedule/<portal_id>/<channel_id>/<day>", methods=["GET"])
def api_get_schedule(portal_id, channel_id, day):
    """
    Get EPG schedule for a specific day.
    
    Args:
        portal_id: Portal ID
        channel_id: Channel ID
        day: Day offset (0 = today, 1 = tomorrow, etc.)
    """
    epg_manager = current_app.epg_manager
    
    try:
        day_offset = int(day)
    except ValueError:
        return jsonify({"error": "Invalid day parameter"})
    
    # Calculate start and end times for the requested day
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today + timedelta(days=day_offset)
    end_date = start_date + timedelta(days=1)
    
    start_time = int(start_date.timestamp())
    end_time = int(end_date.timestamp())
    
    # Build combined ID for EPG lookup
    epg_channel_id = f"{portal_id}:{channel_id}"
    
    # Get programs for the day
    programs = epg_manager.get_programs(epg_channel_id, start_time, end_time)
    
    return jsonify({"programs": programs})