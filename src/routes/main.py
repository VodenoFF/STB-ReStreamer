"""
Main route handlers for STB-ReStreamer.
"""
import logging
from typing import Dict, Any
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session

# Configure logger
logger = logging.getLogger("STB-Proxy")

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """
    Render the index page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get app instances
    config_manager = current_app.config_manager
    alert_manager = current_app.alert_manager
    portal_manager = current_app.portal_manager
    mac_manager = current_app.mac_manager
    stream_manager = current_app.stream_manager
    
    # Get dashboard data
    active_streams = stream_manager.get_active_streams()
    occupied_macs = mac_manager.get_occupied_macs()
    portals = portal_manager.get_all_portals()
    enabled_portals = portal_manager.get_enabled_portals()
    recent_alerts = alert_manager.get_alerts(limit=5)
    
    # Prepare statistics
    stats = {
        'active_streams': len(active_streams),
        'total_portals': len(portals),
        'enabled_portals': len(enabled_portals),
        'occupied_macs': len(occupied_macs)
    }
    
    # Render template
    return render_template(
        'index.html',
        title='Dashboard',
        stats=stats,
        active_streams=active_streams,
        recent_alerts=recent_alerts
    )

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle login requests.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Get client IP
        client_ip = request.remote_addr
        
        # Attempt login
        auth_manager = current_app.auth_manager
        success, token, error_message = auth_manager.login(username, password, client_ip)
        
        if success:
            # Store authentication in session
            session['authenticated'] = True
            session['username'] = username
            session['token'] = token
            
            # Redirect to dashboard
            logger.info(f"User {username} logged in from {client_ip}")
            return redirect(url_for('main.index'))
        else:
            # Show error message
            flash(error_message or 'Invalid username or password', 'danger')
            
    # Render login template
    return render_template('login.html', title='Login')

@main_bp.route('/logout')
def logout():
    """
    Handle logout requests.
    """
    if 'token' in session:
        # Invalidate token
        auth_manager = current_app.auth_manager
        auth_manager.logout(session['token'])
        
        # Log the logout
        logger.info(f"User {session.get('username')} logged out")
        
    # Clear session
    session.clear()
    
    # Redirect to login
    flash('You have been logged out', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/alerts')
def alerts():
    """
    Render the alerts page.
    """
    # Redirect to login if not authenticated
    if not session.get('authenticated'):
        return redirect(url_for('main.login'))
    
    # Get alert manager
    alert_manager = current_app.alert_manager
    
    # Get alerts
    all_alerts = alert_manager.get_alerts()
    
    # Render template
    return render_template(
        'alerts.html',
        title='System Alerts',
        alerts=all_alerts
    )

@main_bp.route('/api/stats')
def api_stats():
    """
    API endpoint for system statistics.
    """
    # Get app instances
    config_manager = current_app.config_manager
    portal_manager = current_app.portal_manager
    mac_manager = current_app.mac_manager
    stream_manager = current_app.stream_manager
    link_cache = current_app.link_cache
    rate_limiter = current_app.rate_limiter
    
    # Gather statistics
    active_streams = stream_manager.get_active_streams()
    occupied_macs = mac_manager.get_occupied_macs()
    portals = portal_manager.get_all_portals()
    enabled_portals = portal_manager.get_enabled_portals()
    
    # Prepare response
    stats = {
        'system': {
            'active_streams': len(active_streams),
            'total_portals': len(portals),
            'enabled_portals': len(enabled_portals),
            'occupied_macs': len(occupied_macs)
        },
        'cache': link_cache.get_stats(),
        'rate_limiter': rate_limiter.get_stats()
    }
    
    return stats