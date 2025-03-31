"""
STB-ReStreamer: A powerful IPTV streaming proxy server.
"""
import os
import json
import logging
import secrets
from datetime import datetime, timezone
from flask import Flask, session
import waitress
from flask_socketio import SocketIO

# Import models
from src.models.alerts import AlertManager
from src.models.config import ConfigManager
from src.models.portals import PortalManager
from src.models.channel_groups import ChannelGroupManager

# Import services
from src.services.mac_manager import MacManager
from src.services.streaming import StreamManager
from src.services.stb_api import StbApi
from src.services.category_manager import CategoryManager
from src.services.epg_manager import EPGManager

# Import utilities
from src.utils.caching import LinkCache
from src.utils.rate_limiting import RateLimiter
from src.utils.auth import AuthManager

# Import routes
from src.routes.main import main_bp
from src.routes.streaming import streaming_bp
from src.routes.hdhr import hdhr_bp
from src.routes.portals import portals_bp
from src.routes.settings import settings_bp
from src.routes.channel_groups import groups_bp
from src.routes.categories import categories_bp
from src.routes.epg import epg_bp
from src.routes.stream_status import stream_status_bp, register_socketio_events
from src.routes.channels import channels_bp
from src.routes.editor import editor_bp
from src.routes.playlist import playlist_bp

def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application
    """
    # Create Flask app
    app = Flask(__name__, 
                template_folder="templates_new",
                static_folder="static")
    
    # Configure app
    app.secret_key = secrets.token_urlsafe(32)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    app.socketio = socketio
    
    # Add custom template filters
    @app.template_filter('now')
    def template_now(format_string):
        """Get current time in specified format"""
        return datetime.now().strftime(format_string)
    
    @app.template_filter('timestamp_to_time')
    def timestamp_to_time(timestamp):
        """Convert Unix timestamp to formatted time"""
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime("%H:%M")
        return "N/A"
    
    @app.template_filter('datetime')
    def format_datetime(timestamp, format_string="%Y-%m-%d %H:%M:%S"):
        """Format a timestamp as a datetime with a given format"""
        if not timestamp:
            return "N/A"
        
        try:
            # Handle integer timestamps (unix timestamps)
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).strftime(format_string)
            # Handle string timestamps that contain only digits (unix timestamps as strings)
            elif isinstance(timestamp, str) and timestamp.isdigit():
                return datetime.fromtimestamp(int(timestamp)).strftime(format_string)
            # Handle string timestamps in ISO format
            elif isinstance(timestamp, str):
                try:
                    # Try to parse as ISO format
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return dt.strftime(format_string)
                except ValueError:
                    # If that fails, just return the string as is
                    return timestamp
            else:
                return str(timestamp)
        except Exception as e:
            # Fall back to returning the original input if conversion fails
            return str(timestamp)
    
    # Configure logging
    configure_logging()
    logger = logging.getLogger("STB-Proxy")
    logger.info("Starting STB-ReStreamer")
    
    # Initialize managers
    logger.info("Initializing managers")
    config_manager = ConfigManager("config.json")
    alert_manager = AlertManager("alerts.json")
    portal_manager = PortalManager("portals.json")
    channel_group_manager = ChannelGroupManager("channel_groups.json")
    mac_manager = MacManager()
    category_manager = CategoryManager(config_manager)
    epg_manager = EPGManager(config_manager)
    
    # Initialize utilities
    logger.info("Initializing utilities")
    link_cache = LinkCache(
        max_size=int(config_manager.get_setting("cache size", 1000)),
        default_ttl=int(config_manager.get_setting("cache ttl", 8))
    )
    rate_limiter = RateLimiter(
        rate=float(config_manager.get_setting("rate limit", 5.0)),
        capacity=int(config_manager.get_setting("rate limit capacity", 10))
    )
    auth_manager = AuthManager(config_manager)
    
    # Initialize stream manager and StB API
    logger.info("Initializing stream manager and STB API")
    stream_manager = StreamManager(config_manager, mac_manager)
    stb_api = StbApi(config_manager)
    
    # Add managers to app context
    app.config_manager = config_manager
    app.alert_manager = alert_manager
    app.portal_manager = portal_manager
    app.channel_group_manager = channel_group_manager
    app.mac_manager = mac_manager
    app.category_manager = category_manager
    app.epg_manager = epg_manager
    app.link_cache = link_cache
    app.rate_limiter = rate_limiter
    app.auth_manager = auth_manager
    app.stream_manager = stream_manager
    app.stb_api = stb_api
    
    # Register blueprints
    logger.info("Registering route blueprints")
    app.register_blueprint(main_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(hdhr_bp)
    app.register_blueprint(portals_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(epg_bp)
    app.register_blueprint(stream_status_bp)
    app.register_blueprint(channels_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(playlist_bp)
    
    # Register SocketIO events
    register_socketio_events(socketio)
    
    logger.info("Application initialized successfully")
    return app, socketio

def configure_logging():
    """
    Configure logging for the application.
    """
    logger = logging.getLogger("STB-Proxy")
    logger.setLevel(logging.INFO)
    
    # Define log format
    log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    # File handler for logging to STB-Proxy.log
    file_handler = logging.FileHandler("STB-Proxy.log")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Console handler for logging to stdout
    console_format = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

def main():
    """
    Main entry point for the application.
    """
    app, socketio = create_app()
    
    # Get port from configuration
    port = app.config_manager.get_setting("port", 8001)
    
    # Run with socketio instead of waitress for WebSocket support
    print(f"Starting STB-ReStreamer on port {port}")
    socketio.run(app, host="0.0.0.0", port=int(port), allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main() 