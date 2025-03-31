"""
Category management routes for STB-ReStreamer.
"""
import logging
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
categories_bp = Blueprint("categories", __name__, url_prefix="/categories")

@categories_bp.route("/", methods=["GET"])
def list_categories():
    """
    Display the category management page.
    """
    category_manager = current_app.category_manager
    categories = category_manager.get_categories()
    
    # Get all channels from all portals to show in category assignment
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
    
    return render_template(
        "categories.html",
        categories=categories,
        channels=channels,
        channel_count=len(channels)
    )

@categories_bp.route("/add", methods=["POST"])
def add_category():
    """
    Add a new category.
    """
    category_manager = current_app.category_manager
    
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Check if category exists
    categories = category_manager.get_categories()
    if any(c.get("name") == name for c in categories):
        flash(f"Category '{name}' already exists", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Create category
    category_id = category_manager.add_category(name)
    flash(f"Category '{name}' created successfully", "success")
    
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/delete/<category_id>", methods=["POST"])
def delete_category(category_id):
    """
    Delete a category.
    """
    category_manager = current_app.category_manager
    
    # Check if category exists
    category = category_manager.get_category(category_id)
    if not category:
        flash(f"Category not found", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Don't allow deletion of default category
    if category.get("is_default", False):
        flash(f"Cannot delete default category", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Delete category
    category_manager.delete_category(category_id)
    flash(f"Category '{category.get('name')}' deleted successfully", "success")
    
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/update/<category_id>", methods=["POST"])
def update_category(category_id):
    """
    Update a category.
    """
    category_manager = current_app.category_manager
    
    # Check if category exists
    category = category_manager.get_category(category_id)
    if not category:
        flash(f"Category not found", "error")
        return redirect(url_for("categories.list_categories"))
    
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Update category
    category_manager.update_category(category_id, name)
    flash(f"Category updated successfully", "success")
    
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/assign", methods=["POST"])
def assign_channels():
    """
    Assign channels to a category.
    """
    category_manager = current_app.category_manager
    
    category_id = request.form.get("category_id")
    if not category_id:
        flash("Category is required", "error")
        return redirect(url_for("categories.list_categories"))
        
    # Check if category exists
    category = category_manager.get_category(category_id)
    if not category:
        flash(f"Category not found", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Get channel IDs from form
    channel_ids = request.form.getlist("channel_ids")
    
    # Assign channels
    for channel_id in channel_ids:
        parts = channel_id.split("|")
        if len(parts) == 2:
            portal_id, ch_id = parts
            category_manager.assign_channel(portal_id, ch_id, category_id)
    
    flash(f"{len(channel_ids)} channels assigned to '{category.get('name')}'", "success")
    
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/unassign/<portal_id>/<channel_id>/<category_id>", methods=["POST"])
def unassign_channel(portal_id, channel_id, category_id):
    """
    Remove a channel from a category.
    """
    category_manager = current_app.category_manager
    
    # Check if category exists
    category = category_manager.get_category(category_id)
    if not category:
        flash(f"Category not found", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Unassign channel
    category_manager.unassign_channel(portal_id, channel_id, category_id)
    flash(f"Channel removed from '{category.get('name')}'", "success")
    
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/set-default/<category_id>", methods=["POST"])
def set_default_category(category_id):
    """
    Set a category as the default for new channels.
    """
    category_manager = current_app.category_manager
    
    # Check if category exists
    category = category_manager.get_category(category_id)
    if not category:
        flash(f"Category not found", "error")
        return redirect(url_for("categories.list_categories"))
    
    # Set as default
    category_manager.set_default_category(category_id)
    flash(f"'{category.get('name')}' set as default category", "success")
    
    return redirect(url_for("categories.list_categories"))

# API Routes for frontend AJAX calls

@categories_bp.route("/api/list", methods=["GET"])
def api_list_categories():
    """
    Get all categories as JSON.
    """
    category_manager = current_app.category_manager
    categories = category_manager.get_categories()
    return jsonify({"categories": categories})

@categories_bp.route("/api/channels/<category_id>", methods=["GET"])
def api_list_category_channels(category_id):
    """
    Get all channels in a category as JSON.
    """
    category_manager = current_app.category_manager
    channels = category_manager.get_category_channels(category_id)
    
    # Get full channel details from STB API
    detailed_channels = []
    for channel in channels:
        portal_id = channel.get("portal_id")
        channel_id = channel.get("channel_id")
        
        try:
            # Get portal info
            portal_manager = current_app.portal_manager
            portal = portal_manager.get_portal(portal_id)
            
            # Use a default MAC address for accessing channels
            mac = "00:1A:79:00:00:00"
            stb_api = current_app.stb_api
            portal_channels = stb_api.get_channels(portal_id, mac)
            
            # Find the specific channel
            for ch in portal_channels:
                if ch.get("id") == channel_id:
                    ch["portal_id"] = portal_id
                    ch["portal_name"] = portal.get("name", "Unknown Portal")
                    detailed_channels.append(ch)
                    break
        except Exception as e:
            logger.error(f"Error getting channel details: {str(e)}")
    
    return jsonify({"channels": detailed_channels})