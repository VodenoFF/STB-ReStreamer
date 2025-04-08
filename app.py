import os
import json
import subprocess
import uuid
import logging
import time
from datetime import datetime, timezone
from functools import wraps
import secrets
import flask
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    Response,
    make_response,
    flash,
    jsonify,
)
import stb
import waitress
import xml.etree.cElementTree as ET
from werkzeug.utils import secure_filename
from collections import OrderedDict
from threading import Lock
import hashlib
import threading
import urllib.parse

def fix_screenshot_urls(items, portal_url):
    """
    Fix screenshot URLs by replacing relative paths with absolute paths.
    
    Args:
        items (list): List of items with screenshot_uri, poster_path, etc.
        portal_url (str): Portal URL to use for creating absolute URLs.
        
    Returns:
        list: List of items with fixed screenshot URLs.
    """
    if not items:
        return items
        
    # Extract base URL from portal URL
    # First remove any query parameters
    base_url = portal_url.split('?')[0] if '?' in portal_url else portal_url
    
    # Handle common patterns in portal URLs
    if '/c/' in base_url:
        base_url = base_url.split('/c/')[0]
    elif '/client/' in base_url:
        base_url = base_url.split('/client/')[0]
    elif '/stalker_portal/server/' in base_url:
        base_url = base_url.split('/stalker_portal/server/')[0]
    elif '/stalker_portal/' in base_url:
        base_url = base_url.split('/stalker_portal/')[0]
    elif '/server/load.php' in base_url:
        base_url = base_url.split('/server/load.php')[0]
    elif '/load.php' in base_url:
        base_url = base_url.split('/load.php')[0]
        
    # Remove trailing slashes
    base_url = base_url.rstrip('/')
    
    # Debug log the base URL
    logger.debug(f"Base URL for fixing screenshot URLs: {base_url}")
    
    image_fields = [
        "screenshot_uri", "poster_path", "cover_big", "logo", 
        "cover", "poster", "backdrop_path", "icon", "image"
    ]
    
    for item in items:
        if not isinstance(item, dict):
            continue
            
        # Process all image fields
        for field in image_fields:
            if field in item and item[field] and isinstance(item[field], str):
                image_url = item[field].strip()
                if image_url and not image_url.startswith(('http://', 'https://')):
                    # Handle relative paths
                    if image_url.startswith('/'):
                        item[field] = base_url + image_url
                    else:
                        item[field] = base_url + '/' + image_url
                        
                    # Debug log the fixed URL
                    logger.debug(f"Fixed {field} URL: {item[field]}")
    
    return items

#region Caching and Rate Limiting Classes

class LinkCache:
    """
    Cache for storing streaming links and associated ffmpeg commands to reduce redundant link generation.
    Uses an OrderedDict for LRU eviction.
    """
    def __init__(self, max_size=1000, default_ttl=8):
        """
        Initializes the LinkCache.

        Args:
            max_size (int): Maximum number of items to store in the cache.
            default_ttl (int): Default time-to-live (in seconds) for cached links.
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock() # Thread lock to ensure thread-safe access to the cache

    def get(self, key):
        """
        Retrieves a link and ffmpeg command from the cache if available and not expired.

        Args:
            key (str): The cache key (e.g., portalId:channelId).

        Returns:
            tuple: (link, ffmpegcmd) if found and valid, (None, None) otherwise.
        """
        with self.lock:
            if key in self.cache:
                data = self.cache[key]
                if time.time() - data['timestamp'] < self.default_ttl:
                    self.cache.move_to_end(key) # Move to end to mark as recently used (LRU)
                    return data['link'], data.get('ffmpegcmd')
                else:
                    del self.cache[key] # Remove expired entry
            return None, None

    def set(self, key, link, ffmpegcmd=None):
        """
        Stores a link and optionally an ffmpeg command in the cache.

        Args:
            key (str): The cache key (e.g., portalId:channelId).
            link (str): The streaming link to cache.
            ffmpegcmd (list, optional): The ffmpeg command associated with the link. Defaults to None.
        """
        with self.lock:
            while len(self.cache) >= self.max_size: # Evict oldest items if cache is full (LRU)
                self.cache.popitem(last=False)

            self.cache[key] = {
                'link': link,
                'ffmpegcmd': ffmpegcmd,
                'timestamp': time.time()
            }
            self.cache.move_to_end(key) # Move to end to mark as recently used (LRU)

    def cleanup(self):
        """
        Removes expired entries from the cache.
        """
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items()
                      if now - v['timestamp'] > self.default_ttl]
            for k in expired:
                del self.cache[k]


class RateLimiter:
    """
    Rate limiter to prevent excessive requests for the same channel, using a cooldown period.
    """
    def __init__(self, default_limit=30, cleanup_interval=300):
        """
        Initializes the RateLimiter.

        Args:
            default_limit (int): Default cooldown duration (in seconds).
            cleanup_interval (int): Interval (in seconds) to cleanup expired cooldown entries.
        """
        self.cooldowns = {}  # {key: {'timestamp': time, 'count': n}} - Stores cooldown info per key
        self.default_limit = default_limit
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self.lock = Lock() # Thread lock for thread-safe access to cooldowns

    def check_rate(self, key, duration=None):
        """
        Checks if a key is rate limited.

        Args:
            key (str): The key to check (e.g., portalId:channelId).
            duration (int, optional): Cooldown duration to check against. Defaults to default_limit.

        Returns:
            tuple: (can_access, remaining_time) - can_access is True if access is allowed, False otherwise.
                                                 remaining_time is the time left in the cooldown if rate limited.
        """
        if duration is None:
            duration = self.default_limit

        with self.lock:
            self._cleanup_if_needed() # Clean up expired entries before checking

            now = time.time()
            if key in self.cooldowns:
                last_access = self.cooldowns[key]['timestamp']
                time_elapsed = now - last_access
                if time_elapsed < duration:
                    return False, duration - time_elapsed # Rate limited, return remaining time
            return True, 0 # Not rate limited, access allowed

    def update_rate(self, key):
        """
        Updates the rate limit timestamp for a key, effectively starting or resetting the cooldown.

        Args:
            key (str): The key to update (e.g., portalId:channelId).
        """
        with self.lock:
            now = time.time()
            self.cooldowns[key] = {
                'timestamp': now,
                'count': self.cooldowns.get(key, {}).get('count', 0) + 1
            }

    def _cleanup_if_needed(self):
        """
        Cleans up expired cooldown entries if the cleanup interval has passed.
        """
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            expired = [k for k, v in self.cooldowns.items()
                      if now - v['timestamp'] > self.default_limit]
            for k in expired:
                del self.cooldowns[k]
            self.last_cleanup = now

# Initialize caching and rate limiting instances
link_cache = LinkCache(max_size=1000, default_ttl=8)
rate_limiter = RateLimiter(default_limit=30, cleanup_interval=300)

# Dictionary to store stream proxy information
stream_proxies = {}

# Cache for VOD/Series items
class VodCache:
    """
    Cache for storing VOD and Series data with efficient memory usage and automatic expiration.
    Uses an OrderedDict for LRU eviction and thread safety.
    """
    def __init__(self, max_size=500, default_ttl=3600):  # 1 hour TTL by default
        """
        Initializes the VodCache.

        Args:
            max_size (int): Maximum number of items to store in the cache.
            default_ttl (int): Default time-to-live (in seconds) for cached items.
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock()  # Thread lock to ensure thread-safe access to the cache

    def get(self, key):
        """
        Retrieves an item from the cache if available and not expired.

        Args:
            key (str): The cache key (e.g., vod:portalId:categoryId).

        Returns:
            Any: The cached value if found and valid, None otherwise.
        """
        with self.lock:
            if key in self.cache:
                data = self.cache[key]
                if time.time() - data['timestamp'] < self.default_ttl:
                    self.cache.move_to_end(key)  # Move to end to mark as recently used (LRU)
                    return data['value']
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None

    def set(self, key, value):
        """
        Stores a value in the cache.

        Args:
            key (str): The cache key (e.g., vod:portalId:categoryId).
            value (Any): The value to cache.
        """
        with self.lock:
            # Evict oldest items if cache is full (LRU)
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            self.cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            self.cache.move_to_end(key)  # Move to end to mark as recently used (LRU)

    def invalidate(self, key_prefix=None):
        """
        Invalidates cache items that start with the given prefix.

        Args:
            key_prefix (str, optional): Prefix for keys to invalidate. If None, invalidates all items.
        """
        with self.lock:
            if key_prefix is None:
                # Invalidate all items
                self.cache.clear()
            else:
                # Invalidate items that start with the given prefix
                keys_to_remove = [k for k in self.cache.keys() if k.startswith(key_prefix)]
                for key in keys_to_remove:
                    del self.cache[key]

    def cleanup(self):
        """
        Removes expired entries from the cache.
        """
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items()
                      if now - v['timestamp'] > self.default_ttl]
            for k in expired:
                del self.cache[k]

# Initialize the VOD/Series items cache
vod_series_cache = VodCache(max_size=500, default_ttl=3600)  # Cache up to 500 items for 1 hour

# Dictionary to store movie details for playlist generation
movie_details_cache = {}

#endregion

#region Flask Application Setup

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32) # Secret key for Flask sessions and CSRF protection

#endregion

#region Logging Configuration

logger = logging.getLogger("STB-Proxy")
logger.setLevel(logging.INFO) # Set logging level to INFO

# Define log format
logFormat = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# File handler for logging to STB-Proxy.log
fileHandler = logging.FileHandler("STB-Proxy.log")
fileHandler.setFormatter(logFormat)
logger.addHandler(fileHandler)

# Console handler for logging to stdout
consoleFormat = logging.Formatter("[%(levelname)s] %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleFormat)
logger.addHandler(consoleHandler)

#endregion

#region Configuration and Data Paths

basePath = os.path.abspath(os.getcwd()) # Get the absolute path of the current working directory
parent_folder = os.path.join(basePath, "portals") # Path to the portals data folder
content_folder = os.path.join(parent_folder, "content") # Path to store prefetched content

host = os.getenv("HOST", "localhost:8001") # Host address for the proxy, default to localhost:8001, configurable via environment variable HOST
configFile = os.getenv("CONFIG", os.path.join(basePath, "config.json")) # Path to the config file, default to config.json in basePath, configurable via environment variable CONFIG
alerts_file = os.path.join(basePath, "alerts.json") # Path to the alerts file

#endregion

#region Global Variables

occupied = {} # Dictionary to track occupied MAC addresses and streaming clients. {portalId: [{mac, channel_id, channel_name, client, portal_name, start_time}, ...]}
config = {} # Global config dictionary, loaded from config.json
portalsdata = {} # Not used currently? Consider removing if unused.
portalmacids = {} # Not used currently? Consider removing if unused.
d_ffmpegcmd = "ffmpeg -re -http_proxy <proxy> -timeout <timeout> -i <url> -map 0 -codec copy -f mpegts pipe:" # Default ffmpeg command template

# Default settings dictionary. Used when creating a new config file or when a setting is missing.
defaultSettings = {
    "stream method": "ffmpeg",
    "ffmpeg command": "ffmpeg -re -http_proxy <proxy> -timeout <timeout> -i <url> -map 0 -codec copy -f mpegts pipe:",
    "ffmpeg timeout": "5",
    "test streams": "true",
    "try all macs": "false",
    "use channel genres": "true",
    "use channel numbers": "true",
    "sort playlist by channel genre": "false",
    "sort playlist by channel number": "false",
    "sort playlist by channel name": "false",
    "enable security": "false",
    "username": "admin",
    "password": "12345",
    "enable hdhr": "false",
    "hdhr name": "STB-Proxy",
    "hdhr id": str(uuid.uuid4().hex),
    "hdhr tuners": "1",
}

# Default portal settings dictionary. Used when creating a new portal or when a portal setting is missing.
defaultPortal = {
    "enabled": "true",
    "name": "",
    "url": "",
    "macs": {},
    "ids": {},
    "streams per mac": "1",
    "proxy": "",
    "enabled channels": [],
    "custom channel names": {},
    "custom channel numbers": {},
    "custom genres": {},
    "custom epg ids": {},
    "enabled vod": [],
    "enabled series": [],
    "custom vod names": {},
    "custom series names": {},
}

# Add after the imports at the top
def get_ffmpeg_path():
    """
    Get the path to the ffmpeg executable, checking common locations.
    Returns the full path if found, or just 'ffmpeg' if not found in common locations.
    """
    # Check if ffmpeg is in the system path
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
            if result.returncode == 0:
                return 'ffmpeg'  # ffmpeg is in PATH
            
            # Check common Windows install locations
            common_paths = [
                os.path.join(os.environ.get('ProgramFiles', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(basePath, 'ffmpeg', 'bin', 'ffmpeg.exe'),  # Local to the application
                os.path.join(basePath, 'ffmpeg.exe'),  # Direct in application directory
                r'C:\ffmpeg\bin\ffmpeg.exe',  # Common Windows installation path
            ]
        else:  # Linux/Unix
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
            if result.returncode == 0:
                return 'ffmpeg'  # ffmpeg is in PATH
            
            # Check common Unix install locations
            common_paths = [
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                os.path.join(basePath, 'ffmpeg'),  # Local to the application
            ]

        # Check each path
        for path in common_paths:
            if os.path.isfile(path):
                return path

    except Exception as e:
        logger.error(f"Error checking ffmpeg path: {e}")

    return 'ffmpeg'  # Default to just the command name

# Add to the global variables section
ffmpeg_path = get_ffmpeg_path()  # Get ffmpeg path once at startup

#endregion

#region Alert Management Functions

def load_alerts():
    """
    Loads alerts from alerts.json file.

    Returns:
        list: List of alert dictionaries.
    """
    try:
        with open(alerts_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return [] # Return empty list if file not found

def save_alerts(alerts):
    """
    Saves alerts to alerts.json file.

    Args:
        alerts (list): List of alert dictionaries to save.
    """
    with open(alerts_file, "w") as f:
        json.dump(alerts, f, indent=4) # Save with indentation for readability

def add_alert(alert_type, source, message, status="active"):
    """
    Adds a new alert to the alerts.json file.

    Args:
        alert_type (str): Type of alert (e.g., "error", "warning").
        source (str): Source of the alert (e.g., "Portal: PortalName").
        message (str): Alert message.
        status (str, optional): Status of the alert ("active", "resolved"). Defaults to "active".

    Returns:
        dict: The newly created alert dictionary.
    """
    alerts = load_alerts()
    alert = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Timestamp in YYYY-MM-DD HH:MM:SS format
        "type": alert_type,
        "source": source,
        "message": message,
        "status": status
    }
    alerts.append(alert)
    save_alerts(alerts)
    return alert

#endregion

#region Configuration File Management Functions

def save_json(file_path, data, message):
    """
    Saves data to a JSON file and prints a message to the console.

    Args:
        file_path (str): Path to the JSON file.
        data (dict or list): Data to be saved as JSON.
        message (str): Message to print to the console after saving.
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4) # Save with indentation for readability
        print(message)

def ensure_cache_directory(portal_id, portal_name):
    """
    Ensures that the cache directory structure exists for a given portal.
    
    Args:
        portal_id (str): ID of the portal.
        portal_name (str): Name of the portal (used for file naming).
        
    Returns:
        str: Path to the portal's cache directory.
    """
    try:
        # Define cache paths relative to application root
        basePath = os.path.abspath(os.getcwd())
        main_cache_dir = os.path.join(basePath, "cache")
        portal_cache_path = os.path.join(main_cache_dir, portal_id)
        
        # Create main cache directory if it doesn't exist
        if not os.path.exists(main_cache_dir):
            os.makedirs(main_cache_dir)
            logger.info(f"Created main cache directory: {main_cache_dir}")
            
        # Create portal-specific cache directory if it doesn't exist
        if not os.path.exists(portal_cache_path):
            os.makedirs(portal_cache_path)
            logger.info(f"Created cache directory for portal {portal_name} ({portal_id}): {portal_cache_path}")
            
        logger.debug(f"Using cache directory: {portal_cache_path}")
        return portal_cache_path
    except Exception as e:
        logger.error(f"Error creating cache directory: {e}")
        # Fall back to a simple path if there's an error
        return os.path.join(basePath, "cache", portal_id)

def savePortalData(name, allChannels, allGenre, vodCategories=None, seriesCategories=None, portalId=None):
    """
    Saves portal channel, genre, VOD, and Series data to JSON files.

    Args:
        name (str): Portal name (used for file naming).
        allChannels (list): List of channel dictionaries.
        allGenre (dict): Dictionary of genre IDs to genre names.
        vodCategories (list, optional): List of VOD category dictionaries. Defaults to None.
        seriesCategories (list, optional): List of Series category dictionaries. Defaults to None.
        portalId (str, optional): Portal ID for cache invalidation. Defaults to None.
    """
    save_json(os.path.join(parent_folder, f"{name}.json"), allChannels, f"Channels '{name}.json' saved")
    save_json(os.path.join(parent_folder, f"{name}_genre.json"), allGenre, f"Genres '{name}_genre.json' saved")

    # Save VOD categories if provided
    if vodCategories:
        save_json(os.path.join(parent_folder, f"{name}_vod_categories.json"), vodCategories, f"VOD Categories '{name}_vod_categories.json' saved")

    # Save Series categories if provided
    if seriesCategories:
        save_json(os.path.join(parent_folder, f"{name}_series_categories.json"), seriesCategories, f"Series Categories '{name}_series_categories.json' saved")

    # Invalidate cache if portal ID is provided
    if portalId:
        logger.info(f"Invalidating cache for portal {portalId}")
        vod_series_cache.invalidate(f"vod_categories:{portalId}")
        vod_series_cache.invalidate(f"series_categories:{portalId}")
        # vod_series_cache.invalidate(f"seasons:{portalId}:")
        # vod_series_cache.invalidate(f"episodes:{portalId}:")

def loadConfig():
    """
    Loads configuration from config.json file. Creates a new config file with defaults if not found.

    Returns:
        dict: Configuration dictionary.
    """
    try:
        with open(configFile) as f:
            data = json.load(f) # Load JSON data from config file
    except FileNotFoundError:
        logger.warning("No existing config found. Creating a new one")
        data = {} # Initialize empty config if file not found

    # Ensure 'portals' and 'settings' keys exist in the config, initialize with empty dict if not
    data.setdefault("portals", {})
    data.setdefault("settings", {})

    # Apply default settings for any missing settings in the loaded config
    settings = data["settings"]
    settingsOut = {setting: settings.get(setting, default) for setting, default in defaultSettings.items()}
    data["settings"] = settingsOut

    # Apply default portal settings for any missing settings in each portal
    portals = data["portals"]
    portalsOut = {portal: {setting: portals[portal].get(setting, default) for setting, default in defaultPortal.items()} for portal in portals}
    data["portals"] = portalsOut

    save_json(configFile, data, "Config saved") # Save the updated config back to file

    global config # Update the global config variable
    config = data
    return data

def getPortals():
    """
    Returns the portals configuration from the global config.

    Returns:
        dict: Dictionary of portal configurations.
    """
    return config["portals"]

def savePortals(portals):
    """
    Saves portal configurations to the global config and config.json file.

    Args:
        portals (dict): Dictionary of portal configurations to save.
    """
    config["portals"] = portals # Update global config
    save_json(configFile, config, "Portals saved") # Save to file

def getSettings():
    """
    Returns the settings configuration from the global config.

    Returns:
        dict: Dictionary of settings.
    """
    return config["settings"]

def saveSettings(settings):
    """
    Saves settings configuration to the global config and config.json file.

    Args:
        settings (dict): Dictionary of settings to save.
    """
    config["settings"] = settings # Update global config
    save_json(configFile, config, "Settings saved") # Save to file

#endregion

#region Channel Group Management Functions

def getChannelGroups():
    """
    Loads channel groups from channel_groups.json file. Handles legacy format and missing channel names.

    Returns:
        dict: Dictionary of channel groups.
    """
    try:
        with open(os.path.join(basePath, "channel_groups.json")) as f:
            groups = json.load(f)

            # Convert old format to new format if needed
            if groups and isinstance(next(iter(groups.values())), list):
                new_groups = {}
                for group_name, channels in groups.items():
                    new_groups[group_name] = {
                        "channels": channels,
                        "logo": "",
                        "order": len(new_groups) + 1
                    }
                groups = new_groups
                saveChannelGroups(groups) # Save in new format

            # Add channel names to existing channels if missing
            portals = getPortals()
            for group_name, group_data in groups.items():
                if "channels" in group_data:
                    for channel in group_data["channels"]:
                        if isinstance(channel, dict) and "channelName" not in channel:
                            portal_id = channel.get("portalId")
                            if portal_id in portals:
                                portal = portals[portal_id]
                                try:
                                    name_path = os.path.join(parent_folder, f"{portal['name']}.json")
                                    with open(name_path, 'r') as file:
                                        all_channels = json.load(file)
                                        channel_lookup = {str(ch["id"]): ch["name"] for ch in all_channels}
                                        channel["channelName"] = channel_lookup.get(channel["channelId"], "Unknown Channel")
                                except:
                                    channel["channelName"] = "Unknown Channel"

            saveChannelGroups(groups) # Save with updated channel names
    except FileNotFoundError:
        # Create default group if file doesn't exist
        groups = {
            "Default Group": {
                "channels": [],
                "logo": "",
                "order": 1
            }
        }
        saveChannelGroups(groups) # Save default groups

    return groups

def saveChannelGroups(channel_groups):
    """
    Saves channel groups to channel_groups.json file.

    Args:
        channel_groups (dict): Dictionary of channel groups to save.
    """
    with open(os.path.join(basePath, "channel_groups.json"), "w") as f:
        json.dump(channel_groups, f, indent=4) # Save with indentation for readability

#endregion

#region Authentication Decorator

def authorise(f):
    """
    Decorator to enforce basic HTTP authentication for routes.

    Args:
        f (function): The function to be decorated (route handler).

    Returns:
        function: Decorated function that performs authentication.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        if security == "false" or (auth and auth.username == username and auth.password == password):
            return f(*args, **kwargs) # Authentication successful, proceed to route handler
        return make_response("Could not verify your login!", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'}) # Authentication failed, return 401
    return decorated

#endregion

#region Utility Functions

def moveMac(portalId, mac):
    """
    Moves a MAC address within the MAC list of a portal. Effectively reordering it to the end.

    Args:
        portalId (str): ID of the portal.
        mac (str): MAC address to move.
    """
    try:
        portals = getPortals()
        macs = portals[portalId]["macs"]
        macs[mac] = macs.pop(mac) # Move MAC to the end in OrderedDict
        portals[portalId]["macs"] = macs
        savePortals(portals) # Save updated portal config
    except Exception as e:
        add_alert("error", f"Portal {portalId}", f"Error moving MAC {mac}: {str(e)}")
        raise # Re-raise the exception after logging the alert

#endregion

#region Route Handlers - Web UI

@app.route("/", methods=["GET"])
@authorise
def home():
    """
    Redirects the root path to the /portals route.
    """
    return redirect("/portals", code=302) # Redirect to portals page

@app.route("/portals", methods=["GET"])
@authorise
def portals():
    """
    Renders the portals.html template, displaying a list of configured portals.
    """
    return render_template("portals.html", portals=getPortals()) # Render the portals template with portal data

@app.route("/movies", methods=["GET"])
@authorise
def movies():
    """
    Renders the movies page for browsing VOD content.
    """
    portals = getPortals()
    return render_template("movies.html", portals=portals)

@app.route("/series", methods=["GET"])
@authorise
def series():
    """
    Renders the series page for browsing TV Series content.
    """
    portals = getPortals()
    return render_template("series.html", portals=portals)

@app.route("/portal/add", methods=["POST"])
@authorise
def portalsAdd():
    """
    Handles adding a new portal from form data. Tests MAC addresses, retrieves channel data, and saves the portal config.
    """
    id = uuid.uuid4().hex # Generate a unique ID for the new portal
    enabled = "true"
    name = request.form["name"]
    url = request.form["url"]
    macs = list(set(request.form["macs"].split(","))) # Split MACs from form, remove duplicates
    streamsPerMac = request.form["streams per mac"]
    proxy = request.form["proxy"]

    # Ensure URL ends with .php, if not, attempt to retrieve it using stb.getUrl
    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error(f"Error getting URL for Portal({name})")
            flash(f"Error getting URL for Portal({name})", "danger") # Flash error message to UI
            return redirect("/portals", code=302)

    macsd = {} # Dictionary to store successful MACs and their expiry dates
    ids = {} # Dictionary to store device IDs and signatures for each MAC
    gotchannels = False # Flag to indicate if channel data has been retrieved

    for mac in macs:
        token = stb.getToken(url, mac, proxy) # Get token for MAC address
        if token:
            device_id = stb.generate_device_id(mac) # Generate device IDs
            device_id2 = device_id
            timestamp = int(time.time())
            signature = stb.generate_signature(mac, token, [str(timestamp)]) # Generate signature
            profile = stb.getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy) # Get profile data
            print(profile) # Print profile data for debugging
            if 'block_msg' in profile and profile['block_msg']:
                logger.info(profile['block_msg']) # Log block message if present
            expiry = stb.getExpires(url, mac, token, proxy) # Get expiry date
            if 'expire_billing_date' in profile and profile['expire_billing_date'] and not expiry:
                expiry = profile['expire_billing_date'] # Use profile expiry if available and not expiry from getExpires
            if 'created' in profile and profile['created'] and not expiry:
                expiry = "Never" # Set expiry to "Never" if created date is present and no expiry
            if expiry:
                macsd[mac] = expiry # Store MAC and expiry
                ids[mac] = { # Store device IDs and signature
                    "device_id": device_id,
                    "device_id2": device_id2,
                    "signature": signature,
                    "timestamp": timestamp
                }
                if not gotchannels:
                    # Get all channels and genres
                    allChannels = stb.getAllChannels(url, mac, token, proxy) # Get all channels for the first successful MAC
                    allGenre = stb.getGenreNames(url, mac, token, proxy) # Get genre names

                    # Get VOD and Series categories
                    vodCategories = stb.getVodCategories(url, mac, token, proxy) # Get VOD categories
                    seriesCategories = stb.getSeriesCategories(url, mac, token, proxy) # Get Series categories

                    # Save all data to files and invalidate cache
                    savePortalData(name, allChannels, allGenre, vodCategories, seriesCategories, portalId=id) # Save channel, genre, VOD, and Series data to files
                    gotchannels = True
                logger.info(f"Successfully tested MAC({mac}) for Portal({name})")
                flash(f"Successfully tested MAC({mac}) for Portal({name})", "success") # Flash success message
                continue # Continue to next MAC

        logger.error(f"Error testing MAC({mac}) for Portal({name})")
        flash(f"Error testing MAC({mac}) for Portal({name})", "danger") # Flash error message

    if macsd: # If at least one MAC was successful
        portal = {
            "enabled": enabled,
            "name": name,
            "url": url,
            "macs": macsd,
            "ids": ids,
            "streams per mac": streamsPerMac,
            "proxy": proxy,
        }

        # Apply default portal settings if any are missing
        for setting, default in defaultPortal.items():
            portal.setdefault(setting, default)

        portals = getPortals()
        portals[id] = portal # Add new portal to config
        savePortals(portals) # Save updated portal config
        logger.info(f"Portal({portal['name']}) added!")
    else:
        logger.error(f"None of the MACs tested OK for Portal({name}). Adding not successful")

    return redirect("/portals", code=302) # Redirect back to portals page

@app.route("/portal/refresh-token/<portalId>", methods=["GET"])
@authorise
def refreshPortalToken(portalId):
    """
    Manually refreshes the token for a portal.

    Args:
        portalId (str): ID of the portal.

    Returns:
        Response: Redirect to the portals page with a success or error message.
    """
    portals = getPortals()
    if portalId not in portals:
        flash(f"Portal not found", "danger")
        return redirect("/portals", code=302)

    portal = portals[portalId]
    name = portal.get("name")
    url = portal.get("url")
    macs = list(portal["macs"].keys())
    proxy = portal.get("proxy")

    if not macs:
        flash(f"No MACs found for portal {name}", "danger")
        return redirect("/portals", code=302)

    # Try to refresh the token for each MAC
    success = False
    for mac in macs:
        # Get device IDs and signature
        if mac in portal.get("ids", {}):
            ids = portal["ids"][mac]
            device_id = ids.get("device_id")
            device_id2 = ids.get("device_id2")
            signature = ids.get("signature")
            timestamp = ids.get("timestamp")

            # Refresh the token
            token = stb.refreshToken(url, mac, proxy, device_id, device_id2, signature, timestamp)
            if token:
                # Token refreshed successfully
                logger.info(f"Token refreshed successfully for MAC {mac} on portal {name}")
                success = True
                break

    if success:
        # Invalidate cache for this portal
        logger.info(f"Invalidating cache for portal {portalId} after token refresh")
        vod_series_cache.invalidate(f"vod_categories:{portalId}")
        vod_series_cache.invalidate(f"series_categories:{portalId}")
        # vod_series_cache.invalidate(f"seasons:{portalId}:")
        # vod_series_cache.invalidate(f"episodes:{portalId}:")

        flash(f"Token refreshed successfully for portal {name}", "success")
    else:
        flash(f"Failed to refresh token for portal {name}", "danger")

    return redirect("/portals", code=302)


@app.route("/portal/update", methods=["POST"])
@authorise
def portalUpdate():
    """
    Handles updating an existing portal from form data. Retests MAC addresses if requested, updates portal config.
    """
    id = request.form["id"]
    enabled = request.form.get("enabled", "false") # Get enabled status, default to "false" if not provided
    name = request.form["name"]
    url = request.form["url"]
    newmacs = list(set(request.form["macs"].split(","))) # Split MACs from form, remove duplicates
    streamsPerMac = request.form["streams per mac"]
    proxy = request.form["proxy"]
    retest = request.form.get("retest", None) # Check if retest was requested

    # Ensure URL ends with .php, if not, attempt to retrieve it using stb.getUrl
    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error(f"Error getting URL for Portal({name})")
            flash(f"Error getting URL for Portal({name})", "danger") # Flash error message
            return redirect("/portals", code=302)

    portals = getPortals()
    oldmacs = portals[id]["macs"] # Get existing MACs for the portal

    macsout = {} # Dictionary to store updated MACs and their expiry dates
    deadmacs = [] # List to store MACs that failed testing
    gotchannels = False # Flag to indicate if channel data has been retrieved

    for mac in newmacs:
        if retest or mac not in oldmacs.keys(): # Retest MAC if requested or if it's a new MAC
            token = stb.getToken(url, mac, proxy) # Get token for MAC
            if token:
                ids = portals[id]["ids"][mac] # Get stored device IDs and signature for MAC
                stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy) # Get profile (primarily to keep session alive)
                expiry = stb.getExpires(url, mac, token, proxy) # Get expiry date
                if expiry:
                    macsout[mac] = expiry # Store MAC and expiry

                    # If retest is requested, fetch and save channel, VOD, and Series data
                    if retest and not gotchannels:
                        # Get all channels and genres
                        allChannels = stb.getAllChannels(url, mac, token, proxy) # Get all channels for the first successful MAC
                        allGenre = stb.getGenreNames(url, mac, token, proxy) # Get genre names

                        # Get VOD and Series categories
                        vodCategories = stb.getVodCategories(url, mac, token, proxy) # Get VOD categories
                        seriesCategories = stb.getSeriesCategories(url, mac, token, proxy) # Get Series categories

                        # Save all data to files
                        savePortalData(name, allChannels, allGenre, vodCategories, seriesCategories) # Save channel, genre, VOD, and Series data to files
                        gotchannels = True

                    logger.info(f"Successfully tested MAC({mac}) for Portal({name})")
                    flash(f"Successfully tested MAC({mac}) for Portal({name})", "success") # Flash success message

            if mac not in macsout: # If MAC test failed
                deadmacs.append(mac) # Add to dead MACs list

        if mac in oldmacs and mac not in deadmacs: # Keep old MAC if it was working and not marked as dead
            macsout[mac] = oldmacs[mac] # Copy expiry from old MACs

        if mac not in macsout: # If MAC test failed or was not kept from old MACs
            logger.error(f"Error testing MAC({mac}) for Portal({name})")
            flash(f"Error testing MAC({mac}) for Portal({name})", "danger") # Flash error message

    if macsout: # If at least one MAC is working
        portals[id].update({ # Update portal config with new data
            "enabled": enabled,
            "name": name,
            "url": url,
            "macs": macsout,
            "streams per mac": streamsPerMac,
            "proxy": proxy,
        })
        savePortals(portals) # Save updated portal config
        logger.info(f"Portal({name}) updated!")
        flash(f"Portal({name}) updated!", "success") # Flash success message
    else:
        logger.error(f"None of the MACs tested OK for Portal({name}). Adding not successful")

    return redirect("/portals", code=302) # Redirect back to portals page

@app.route("/portal/remove", methods=["POST"])
@authorise
def portalRemove():
    """
    Handles removing a portal from the configuration.
    """
    id = request.form["deleteId"] # Get portal ID to delete from form
    portals = getPortals()
    name = portals[id]["name"] # Get portal name for logging
    del portals[id] # Delete portal from config
    savePortals(portals) # Save updated portal config
    logger.info(f"Portal ({name}) removed!")
    flash(f"Portal ({name}) removed!", "success") # Flash success message
    return redirect("/portals", code=302) # Redirect back to portals page

@app.route("/api/portal/<portalId>/vod/categories", methods=["GET"])
@authorise
def getPortalVodCategories(portalId):
    """
<<<<<<< Updated upstream
    Renders the channel editor page (editor.html) with channel group data.
    """
    channel_groups = getChannelGroups()
    portals = getPortals()
    return render_template("editor.html", channel_groups=channel_groups, portals=portals) # Pass both channel_groups and portals

@app.route("/editor_data", methods=["GET"])
@authorise
def editor_data():
    """
    Returns channel data for the channel editor in JSON format.
    Fetches channel lists from enabled portals and prepares data for the editor table.
    """
    channels = [] # List to store channel data
    portals = getPortals()
    channel_groups = getChannelGroups()

    for portal in portals:
        if portals[portal]["enabled"] == "true": # Process only enabled portals
            portalName = portals[portal]["name"]
            url = portals[portal]["url"]
            macs = list(portals[portal]["macs"].keys())
            proxy = portals[portal]["proxy"]
            enabledChannels = portals[portal].get("enabled channels", [])
            customChannelNames = portals[portal].get("custom channel names", {})
            customGenres = portals[portal].get("custom genres", {})
            customChannelNumbers = portals[portal].get("custom channel numbers", {})
            customEpgIds = portals[portal].get("custom epg ids", {})

            # Load channel and genre data from files for the first available MAC
            for mac in macs:
                try:
                    name_path = os.path.join(parent_folder, f"{portalName}.json")
                    genre_path = os.path.join(parent_folder, f"{portalName}_genre.json")
                    with open(name_path, 'r') as file:
                        allChannels = json.load(file)
                    with open(genre_path, 'r') as file:
                        genres = json.load(file)
                    break # Break after loading data for the first MAC
                except:
                    allChannels = None
                    genres = None

            if allChannels and genres: # If channel and genre data loaded successfully
                for channel in allChannels:
                    channelId = str(channel["id"])
                    channelName = str(channel["name"])
                    channelNumber = str(channel["number"])
                    genre = str(genres.get(str(channel["tv_genre_id"]))) # Get genre name from genre ID
                    enabled = channelId in enabledChannels # Check if channel is enabled
                    customChannelNumber = customChannelNumbers.get(channelId, "") # Get custom channel number if set
                    customChannelName = customChannelNames.get(channelId, "") # Get custom channel name if set
                    customGenre = customGenres.get(channelId, "") # Get custom genre if set
                    customEpgId = customEpgIds.get(channelId, "") # Get custom EPG ID if set

                    # Determine the group for this channel
                    group = ""
                    for group_name, group_data in channel_groups.items():
                        if "channels" in group_data:
                            for ch in group_data["channels"]:
                                if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portal:
                                    group = group_name # Found group for the channel
                                    break
                        if group:
                            break # Break if group found

                    channels.append({ # Append channel data for the editor table
                        "portal": portal,
                        "portalName": portalName,
                        "enabled": enabled,
                        "channelNumber": channelNumber,
                        "customChannelNumber": customChannelNumber,
                        "channelName": channelName,
                        "customChannelName": customChannelName,
                        "genre": genre,
                        "customGenre": customGenre,
                        "channelId": channelId,
                        "customEpgId": customEpgId,
                        "group": group,
                        "link": f"http://{host}/play/{portal}/{channelId}?web=true", # Web preview link
                    })
            else:
                logger.error(f"Error getting channel data for {portalName}, skipping")
                flash(f"Error getting channel data for {portalName}, skipping", "danger") # Flash error message

    return jsonify({"data": channels}) # Return channel data as JSON

@app.route("/editor/save", methods=["POST"])
@authorise
def editorSave():
    """
    Saves channel editor changes to the portal configurations.
    Handles enabled/disabled status, custom channel numbers, names, genres, EPG IDs, and channel groups.
    """
    enabledEdits = json.loads(request.form["enabledEdits"]) # Load edits from form data as JSON
    numberEdits = json.loads(request.form["numberEdits"])
    nameEdits = json.loads(request.form["nameEdits"])
    genreEdits = json.loads(request.form["genreEdits"])
    epgEdits = json.loads(request.form["epgEdits"])
    groupEdits = json.loads(request.form["groupEdits"])
    portals = getPortals()
    channel_groups = getChannelGroups()

    def update_portal(edit, key, subkey):
        """
        Helper function to update portal settings based on editor changes.

        Args:
            edit (dict): Edit data for a channel.
            key (str): Key in edit data (e.g., "custom number").
            subkey (str): Subkey in portal config (e.g., "custom channel numbers").
        """
        portal = edit["portal"]
        channelId = edit["channel id"]
        value = edit[key]
        if value:
            portals[portal].setdefault(subkey, {}) # Create subkey if not exists
            portals[portal][subkey].update({channelId: value}) # Update with new value
        else:
            portals[portal][subkey].pop(channelId, None) # Remove if value is empty

    # Process enabled/disabled edits
    for edit in enabledEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        enabled = edit["enabled"]
        if enabled:
            portals[portal].setdefault("enabled channels", []) # Create enabled channels list if not exists
            portals[portal]["enabled channels"].append(channelId) # Add channel ID to enabled list
        else:
            portals[portal]["enabled channels"] = list(filter((channelId).__ne__, portals[portal]["enabled channels"])) # Remove channel ID from enabled list

    # Process custom number edits
    for edit in numberEdits:
        update_portal(edit, "custom number", "custom channel numbers")

    # Process custom name edits
    for edit in nameEdits:
        update_portal(edit, "custom name", "custom channel names")

    # Process custom genre edits
    for edit in genreEdits:
        update_portal(edit, "custom genre", "custom genres")

    # Process custom EPG ID edits
    for edit in epgEdits:
        update_portal(edit, "custom epg id", "custom epg ids")

    # Process group edits
    for edit in groupEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        group = edit["group"]

        # Remove channel from all existing groups first
        for group_name, group_data in channel_groups.items():
            if "channels" in group_data:
                group_data["channels"] = [
                    ch for ch in group_data["channels"]
                    if not (isinstance(ch, dict) and
                           ch.get("channelId") == channelId and
                           ch.get("portalId") == portal)
                ]

        # Add to new group if one is selected
        if group:
            if group not in channel_groups:
                channel_groups[group] = { # Create new group if not exists
                    "channels": [],
                    "logo": "",
                    "order": max([g.get("order", 0) for g in channel_groups.values()], default=0) + 1 # Determine next order number
                }

            # Add as dict with both channelId and portalId
            channel_entry = {
                "channelId": channelId,
                "portalId": portal
            }
            if channel_entry not in channel_groups[group]["channels"]: # Avoid duplicates
                channel_groups[group]["channels"].append(channel_entry)

    saveChannelGroups(channel_groups) # Save updated channel groups
    savePortals(portals) # Save updated portal configurations
    logger.info("Playlist config saved!")
    flash("Playlist config saved!", "success") # Flash success message

    return redirect("/editor", code=302) # Redirect back to editor page

@app.route("/editor/reset", methods=["POST"])
@authorise
def editorReset():
    """
    Resets all channel customizations (enabled status, custom numbers, names, genres, EPG IDs) for all portals.
    """
    portals = getPortals()
    for portal in portals:
        portals[portal].update({ # Reset customization settings for each portal
            "enabled channels": [],
            "custom channel numbers": {},
            "custom channel names": {},
            "custom genres": {},
            "custom epg ids": {},
        })

    savePortals(portals) # Save updated portal configurations
    logger.info("Playlist reset!")
    flash("Playlist reset!", "success") # Flash success message

    return redirect("/editor", code=302) # Redirect back to editor page

@app.route("/settings", methods=["GET"])
@authorise
def settings():
    """
    Renders the settings page (settings.html) with current and default settings.
    """
    return render_template("settings.html", settings=getSettings(), defaultSettings=defaultSettings) # Render settings template with settings data

@app.route("/settings/save", methods=["POST"])
@authorise
def save():
    """
    Saves settings from form data to the configuration.
    """
    settings = {setting: request.form.get(setting, "false") for setting in defaultSettings} # Get settings from form data, default to "false" if not provided
    saveSettings(settings) # Save updated settings
    logger.info("Settings saved!")
    flash("Settings saved!", "success") # Flash success message
    return redirect("/settings", code=302) # Redirect back to settings page

#endregion

#region Route Handlers - Playlist Generation

@app.route("/playlist", methods=["GET"])
@authorise
def playlist():
    """
    Generates and returns an M3U playlist of enabled channels from all enabled portals.
    Supports channel sorting and filtering based on settings.
    """
    channels = [] # List to store playlist entries
    portals = getPortals()
    for portal in portals:
        if portals[portal]["enabled"] == "true": # Process only enabled portals
            enabledChannels = portals[portal].get("enabled channels", [])
            if enabledChannels: # Process only if there are enabled channels for this portal
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customGenres = portals[portal].get("custom genres", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})
                customEpgIds = portals[portal].get("custom epg ids", {})

                # Load channel and genre data from files for the first available MAC
                for mac in macs:
                    try:
                        name_path = os.path.join(parent_folder, f"{name}.json")
                        genre_path = os.path.join(parent_folder, f"{name}_genre.json")
                        with open(name_path, 'r') as file:
                            allChannels = json.load(file)
                        with open(genre_path, 'r') as file:
                            genres = json.load(file)
                        break # Break after loading data for the first MAC
                    except:
                        allChannels = None
                        genres = None

                if allChannels and genres: # If channel and genre data loaded successfully
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels: # Process only enabled channels
                            channelName = customChannelNames.get(channelId, str(channel.get("name"))) # Get custom name or default
                            genre = customGenres.get(channelId, str(genres.get(str(channel.get("tv_genre_id"))))) # Get custom genre or default from genres file
                            channelNumber = customChannelNumbers.get(channelId, str(channel.get("number"))) # Get custom number or default
                            epgId = customEpgIds.get(channelId, f"{portal}{channelId}") # Get custom EPG ID or generate default

                            playlist_entry = f'#EXTINF:-1 tvg-id="{epgId}"'
                            if getSettings().get("use channel numbers", "true") == "true":
                                playlist_entry += f' tvg-chno="{channelNumber}"'
                            if getSettings().get("use channel genres", "true") == "true":
                                playlist_entry += f' group-title="{genre}"'
                            playlist_entry += f',{channelName}\nhttp://{host}/play/{portal}/{channelId}' # Add channel name and play URL
                            channels.append(playlist_entry)

                else:
                    logger.error(f"Error making playlist for {name}, skipping")

    # Apply playlist sorting based on settings
    if getSettings().get("sort playlist by channel name", "true") == "true":
        channels.sort(key=lambda k: k.split(",")[1].split("\n")[0]) # Sort by channel name
    if getSettings().get("use channel numbers", "true") == "true" and getSettings().get("sort playlist by channel number", "false") == "true":
        channels.sort(key=lambda k: k.split('tvg-chno="')[1].split('"')[0]) # Sort by channel number
    if getSettings().get("use channel genres", "true") == "true" and getSettings().get("sort playlist by channel genre", "false") == "true":
        channels.sort(key=lambda k: k.split('group-title="')[1].split('"')[0]) # Sort by channel genre

    playlist_output = "#EXTM3U \n" + "\n".join(channels) # Combine playlist entries into M3U format

    return Response(playlist_output, mimetype="text/plain") # Return playlist as plain text M3U

@app.route("/groups_playlist", methods=["GET"])
@authorise
def groups_playlist():
    """
    Generates and returns an M3U playlist of channel groups. Each entry links to the /chplay/<groupID> route.
    """
    channel_groups = getChannelGroups()

    # Sort groups by their order
    sorted_groups = sorted(channel_groups.items(), key=lambda x: x[1].get("order", 0))

    playlist_entries = [] # List to store playlist entries for groups
    for group_name, group_data in sorted_groups:
        # Get the group's logo URL, if it exists
        logo_url = group_data.get("logo", "")
        if logo_url:
            # Make the logo URL absolute by adding the host
            logo_url = f"http://{host}{logo_url}"

        # Create the EXTINF line for the group
        playlist_entries.append(
            f'#EXTINF:-1 tvg-id="{group_name}" tvg-logo="{logo_url}",{group_name}\n'
            f'http://{host}/chplay/{group_name}' # Link to group playback route
        )

    playlist_output = "#EXTM3U\n" + "\n".join(playlist_entries) # Combine group playlist entries into M3U format
    return Response(playlist_output, mimetype="text/plain") # Return group playlist as plain text M3U

#endregion

#region Route Handlers - Stream Playback

@app.route("/play/<portalId>/<channelId>", methods=["GET"])
def channel(portalId, channelId):
    """
    Handles channel playback requests. Retrieves stream link, manages MAC occupation, performs stream testing,
    and uses caching and rate limiting. Supports web preview mode.
    """
    def streamData():
        """
        Stream data generator function. Executes ffmpeg command and yields stream chunks.
        Handles MAC occupation and unoccupation, and logs errors.
        """
        def occupy():
            """
            Occupies a MAC address for streaming. Updates the global 'occupied' dictionary.
            """
            occupied.setdefault(portalId, []).append({
                "mac": mac,
                "channel id": channelId,
                "channel name": channelName,
                "client": ip,
                "portal name": portalName,
                "start time": startTime,
            })
            logger.info(f"Occupied Portal({portalId}):MAC({mac})")

        def unoccupy():
            """
            Unoccupies a MAC address after streaming is finished. Removes entry from 'occupied' dictionary.
            """
            occupied[portalId].remove({
                "mac": mac,
                "channel id": channelId,
                "channel name": channelName,
                "client": ip,
                "portal name": portalName,
                "start time": startTime,
            })
            logger.info(f"Unoccupied Portal({portalId}):MAC({mac})")

        try:
            startTime = datetime.now(timezone.utc).timestamp()
            occupy()

            # Replace 'ffmpeg' with full path in command
            cmd = list(ffmpegcmd)  # Make a copy of the command list
            cmd[0] = ffmpeg_path  # Replace the first element with the full path

            with subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ) as ffmpeg_sp:
                while True:
                    chunk = ffmpeg_sp.stdout.read(1024)
                    if not chunk:
                        if ffmpeg_sp.poll() != 0:
                            stderr_output = ffmpeg_sp.stderr.read().decode('utf-8')
                            logger.error(f"Ffmpeg error output: {stderr_output}")
                            logger.error(f"Ffmpeg closed with error({ffmpeg_sp.poll()}). Moving MAC({mac}) for Portal({portalName})")
                            add_alert("error", f"Portal: {portalName}", 
                                    f"Stream failed for channel {channelName} (ID: {channelId}). Moving MAC {mac}. Error: {stderr_output}")
                            moveMac(portalId, mac)
                        break
                    yield chunk
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg and make sure it's in the system PATH")
            add_alert("error", "System", "FFmpeg not found. Please install FFmpeg and make sure it's in the system PATH")
        except Exception as e:
            logger.error(f"Exception during streaming: {e}")
            add_alert("error", f"Portal: {portalName}", f"Stream error for channel {channelName} (ID: {channelId}): {str(e)}")
        finally:
            unoccupy()
            if 'ffmpeg_sp' in locals():
                ffmpeg_sp.kill()

    def testStream():
        """
        Tests if a stream link is valid using ffprobe.

        Returns:
            bool: True if stream is valid, False otherwise.
        """
        timeout = int(getSettings().get("ffmpeg timeout")) * 1000000 # Get timeout from settings and convert to microseconds
        ffprobecmd = [
            "ffprobe",
            "-v", "info",  # Show more info for debugging
            "-select_streams", "v:0",  # Select the first video stream
            "-show_entries", "stream=codec_name",  # Show codec name
            "-of", "default=noprint_wrappers=1:nokey=1",  # Output format
            "-timeout", str(timeout),
            "-i", link # Stream link to test
        ]

        if proxy:
            ffprobecmd.extend(["-http_proxy", proxy]) # Add proxy to ffprobe command if configured

        try:
            with subprocess.Popen(
                ffprobecmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as ffprobe_sb: # Start ffprobe process
                stdout, stderr = ffprobe_sb.communicate() # Wait for ffprobe to finish and get output
                result = ffprobe_sb.returncode == 0 and stdout.strip() != b'' # Check if ffprobe exited successfully and produced output
                if not result:
                    add_alert("error", f"Portal: {portalName}", f"Stream test failed for channel {channelName} (ID: {channelId})") # Add alert if test failed
                return result # Return test result (True/False)
        except Exception as e:
            logger.error(f"Exception during stream test: {e}")
            add_alert("error", f"Portal: {portalName}", f"Stream test encountered an error for channel {channelName} (ID: {channelId})") # Add alert for exception during test
            return False # Return False if exception occurred

    def isMacFree():
        """
        Checks if a MAC address has available streams based on 'streams per mac' setting.

        Returns:
            bool: True if MAC is free or streams per mac is 0, False otherwise.
        """
        return sum(1 for i in occupied.get(portalId, []) if i["mac"] == mac) < streamsPerMac # Count occupied streams for MAC and compare to limit

    # Get portal and channel information
    portal = getPortals().get(portalId)
    portalName = portal.get("name")
    url = portal.get("url")
    macs = list(portal["macs"].keys())
    streamsPerMac = int(portal.get("streams per mac"))
    proxy = portal.get("proxy")
    web = request.args.get("web") # Check for 'web' parameter for web preview mode
    ip = request.remote_addr # Get client IP address

    # Initialize channelName at the start
    channelName = None
    try:
        name_path = os.path.join(parent_folder, f"{portalName}.json")
        with open(name_path, 'r') as file:
            channels = json.load(file)
            for c in channels:
                if str(c["id"]) == channelId:
                    channelName = portal.get("custom channel names", {}).get(channelId, c["name"]) # Get custom channel name or default
                    break
    except:
        pass

    # If we still don't have a channel name, use a default
    if not channelName:
        channelName = f"Channel ID: {channelId}"

    logger.info(f"IP({ip}) requested Portal({portalId}):Channel({channelId})") # Log channel request

    # Check link cache first before rate limit
    cached_link, cached_ffmpegcmd = link_cache.get(f"{portalId}:{channelId}")
    if cached_link: # If link found in cache
        if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
            if cached_ffmpegcmd:
                ffmpegcmd = cached_ffmpegcmd # Use cached ffmpeg command
                return Response(streamData(), mimetype="application/octet-stream") # Return stream using cached ffmpeg command
        else:
            return redirect(cached_link, code=302) # Redirect to cached link if not using ffmpeg stream method

    # If no cache hit, check rate limit
    can_access, remaining_time = rate_limiter.check_rate(f"{portalId}:{channelId}")
    if not can_access and not web:  # Don't apply rate limit for web preview
        logger.info(f"Channel {channelName} ({channelId}) in cooldown. {remaining_time:.1f} seconds remaining")
        add_alert("warning", f"Portal: {portalName}", f"Channel {channelName} in cooldown. {remaining_time:.1f} seconds remaining. Attempting fallback.") # Add alert for cooldown

        # Try to find a fallback in the same group
        channel_groups = getChannelGroups()
        current_group = None

        # Find which group this channel belongs to
        for group_name, group_data in channel_groups.items():
            if "channels" in group_data:
                for ch in group_data["channels"]:
                    if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portalId:
                        current_group = group_name # Found group for the channel
                        break
            if current_group:
                break

        if current_group: # If channel belongs to a group
            # Try other channels in the same group
            for channel_entry in channel_groups[current_group]["channels"]:
                if not isinstance(channel_entry, dict):
                    continue

                fallback_channel_id = channel_entry['channelId']
                fallback_portal_id = channel_entry['portalId']

                # Check cache for fallback first
                fallback_key = f"{fallback_portal_id}:{fallback_channel_id}"
                cached_link, _ = link_cache.get(fallback_key)
                if cached_link:
                    return redirect(f"/play/{fallback_portal_id}/{fallback_channel_id}", code=302) # Redirect to cached fallback if available

                # Skip if it's the same channel or if the fallback is also rate limited
                can_access_fallback, _ = rate_limiter.check_rate(fallback_key)
                if (fallback_channel_id == channelId and fallback_portal_id == portalId) or not can_access_fallback:
                    continue # Skip if same channel or fallback rate limited

                return redirect(f"/play/{fallback_portal_id}/{fallback_channel_id}", code=302) # Redirect to fallback channel

        # If no fallback found, return error
        return make_response(f"Channel in cooldown. Please wait {remaining_time:.1f} seconds.", 429) # Return 429 error if rate limited and no fallback

    freeMac = False # Flag to indicate if a free MAC was found

    for mac in macs:
        channels = None
        cmd = None
        link = None
        if streamsPerMac == 0 or isMacFree(): # Check if MAC is free or streams per mac is unlimited
            logger.info(f"Trying Portal({portalId}):MAC({mac}):Channel({channelId})") # Log MAC attempt
            freeMac = True # Mark free MAC as found

            # Check link cache first
            cached_link, cached_ffmpegcmd = link_cache.get(f"{portalId}:{channelId}")
            if cached_link: # If link found in cache
                link = cached_link
                if cached_ffmpegcmd:
                    ffmpegcmd = cached_ffmpegcmd # Use cached ffmpeg command
            else:
                # Get fresh link if not cached
                token = stb.getToken(url, mac, proxy) # Get token for MAC
                if token:
                    name_path = os.path.join(parent_folder, f"{portalName}.json")
                    with open(name_path, 'r') as file:
                        channels = json.load(file) # Load channel list

                if channels:
                    for c in channels:
                        if str(c["id"]) == channelId:
                            channelName = portal.get("custom channel names", {}).get(channelId, c["name"]) # Get custom channel name or default
                            cmd = c["cmd"] # Get channel command from channel data
                            break

                if cmd: # If channel command found
                    ids = portal["ids"][mac] # Get stored device IDs and signature for MAC
                    stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy) # Get profile (primarily to keep session alive)
                    if "http://localhost/" in cmd or "http:///ch/" in cmd: # Check if command is a relative link
                        link = stb.getLink(url, mac, token, cmd, proxy) # Get absolute stream link
                    else:
                        # Handle direct link commands more safely
                        parts = cmd.split(" ")
                        link = parts[1] if len(parts) > 1 else cmd # Extract link from command

        if link: # If stream link retrieved
            if getSettings().get("test streams", "true") == "false" or testStream(): # Test stream if enabled in settings
                # Cache the link and ffmpeg command if needed
                if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                    ffmpegcmd = str(getSettings()["ffmpeg command"]) # Get ffmpeg command template from settings
                    ffmpegcmd = ffmpegcmd.replace("<url>", link) # Replace <url> placeholder with stream link
                    ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000)) # Replace <timeout> placeholder
                    if proxy:
                        ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy) # Replace <proxy> placeholder
                    else:
                        ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "") # Remove proxy option if not configured
                    ffmpegcmd = " ".join(ffmpegcmd.split()).split() # Split ffmpeg command string into list
                    link_cache.set(f"{portalId}:{channelId}", link, ffmpegcmd) # Cache link and ffmpeg command
                else:
                    link_cache.set(f"{portalId}:{channelId}", link) # Cache link only if not using ffmpeg stream method

                # Update rate limit
                rate_limiter.update_rate(f"{portalId}:{channelId}") # Update rate limit timestamp

                if web: # Web preview mode
                    ffmpegcmd = [
                        "ffmpeg",
                        "-loglevel",
                        "panic",
                        "-hide_banner",
                        "-i",
                        link,
                        "-vcodec",
                        "copy",
                        "-f",
                        "mp4",
                        "-movflags",
                        "frag_keyframe+empty_moov",
                        "pipe:",
                    ] # Ffmpeg command for web preview (mp4 fragment)
                    if proxy:
                        ffmpegcmd.insert(1, "-http_proxy")
                        ffmpegcmd.insert(2, proxy) # Add proxy to web preview ffmpeg command
                    return Response(streamData(), mimetype="application/octet-stream") # Return stream for web preview
                else: # Normal stream playback
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        return Response(streamData(), mimetype="application/octet-stream") # Return stream using ffmpeg
                    else:
                        logger.info("Redirect sent")
                        return redirect(link, code=302) # Redirect to direct stream link

        logger.info(f"Unable to connect to Portal({portalId}) using MAC({mac})")
        logger.info(f"Moving MAC({mac}) for Portal({portalName})")
        moveMac(portalId, mac) # Move MAC if connection failed

        if getSettings().get("try all macs", "false") != "true": # Stop trying MACs if 'try all macs' is disabled
            break # Break loop after trying one MAC

    if not web: # If not web preview mode, try fallbacks if no working stream found
        logger.info(f"Portal({portalId}):Channel({channelId}) is not working. Looking for fallbacks...")
        add_alert("error", f"Portal: {portalName}", f"Channel {channelName} (ID: {channelId}) is not working, searching for fallbacks...") # Add alert

        portals = getPortals()
        channelGroups = getChannelGroups()

        # Find which group this channel belongs to
        channelGroup = None
        for group_name, group_data in channelGroups.items():
            if "channels" in group_data:
                for ch in group_data["channels"]:
                    if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portalId:
                        channelGroup = group_name # Found group for the channel
                        break
            if channelGroup:
                break

        if channelGroup: # If channel belongs to a group
            logger.info(f"Found channel in group: {channelGroup}")
            # Try all other channels in the same group
            for channel_entry in channelGroups[channelGroup]["channels"]:
                if not isinstance(channel_entry, dict):
                    continue

                fallbackChannelId = channel_entry['channelId']
                fallbackPortalId = channel_entry['portalId']

                # Check cache for fallback first
                fallback_key = f"{fallbackPortalId}:{fallbackChannelId}"
                cached_link, cached_ffmpegcmd = link_cache.get(fallback_key)
                if cached_link: # If fallback link found in cache
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        if cached_ffmpegcmd:
                            ffmpegcmd = cached_ffmpegcmd # Use cached ffmpeg command
                            return Response(streamData(), mimetype="application/octet-stream") # Return stream using cached ffmpeg command
                    else:
                        return redirect(cached_link, code=302) # Redirect to cached fallback link

                # Skip if the fallback channel is rate limited
                can_access_fallback, _ = rate_limiter.check_rate(fallback_key)
                if not can_access_fallback:
                    continue # Skip if fallback rate limited

                if fallbackChannelId != channelId:  # Don't try the same channel
                    if fallbackPortalId in portals and portals[fallbackPortalId]["enabled"] == "true": # Check if fallback portal is enabled
                        url = portals[fallbackPortalId].get("url")
                        macs = list(portals[fallbackPortalId]["macs"].keys())
                        proxy = portals[fallbackPortalId].get("proxy")
                        for mac in macs:
                            channels = None
                            cmd = None
                            link = None
                            if streamsPerMac == 0 or isMacFree(): # Check if MAC is free or streams per mac is unlimited
                                # Check link cache first for fallback
                                cached_link, cached_ffmpegcmd = link_cache.get(fallback_key)
                                if cached_link: # If fallback link found in cache
                                    link = cached_link
                                    if cached_ffmpegcmd:
                                        ffmpegcmd = cached_ffmpegcmd # Use cached ffmpeg command
                                else:
                                    try:
                                        token = stb.getToken(url, mac, proxy) # Get token for fallback MAC
                                        ids = portals[fallbackPortalId]["ids"][mac] # Get stored device IDs and signature
                                        stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy) # Get profile
                                        name_path = os.path.join(parent_folder, f"{portals[fallbackPortalId]['name']}.json")
                                        with open(name_path, 'r') as file:
                                            channels = json.load(file) # Load fallback channel list
                                    except:
                                        logger.info(f"Unable to connect to fallback Portal({fallbackPortalId}) using MAC({mac})")
                                        add_alert("warning", f"Portal: {portals[fallbackPortalId]['name']}", f"Failed to connect to fallback portal using MAC {mac}") # Add alert
                                    if channels:
                                        for c in channels:
                                            if str(c["id"]) == fallbackChannelId:
                                                channelName = portals[fallbackPortalId].get("custom channel names", {}).get(fallbackChannelId, c["name"]) # Get fallback channel name
                                                cmd = c["cmd"] # Get fallback channel command
                                                break
                                        if cmd: # If fallback channel command found
                                            ids = portals[fallbackPortalId]["ids"][mac] # Get stored device IDs and signature
                                            stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy) # Get profile
                                            if "http://localhost/" in cmd or "http:///ch/" in cmd: # Check if command is relative link
                                                link = stb.getLink(url, mac, token, cmd, proxy) # Get fallback stream link
                                            else:
                                                link = cmd.split(" ")[1] # Extract link from command

                                if link and testStream(): # Test fallback stream link
                                    # Cache the fallback link
                                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                                        ffmpegcmd = str(getSettings()["ffmpeg command"]) # Get ffmpeg command template
                                        ffmpegcmd = ffmpegcmd.replace("<url>", link) # Replace <url> placeholder
                                        ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000)) # Replace <timeout>
                                        if proxy:
                                            ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy) # Replace <proxy>
                                        else:
                                            ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "") # Remove proxy option if not configured
                                        ffmpegcmd = " ".join(ffmpegcmd.split()).split() # Split ffmpeg command string into list
                                        link_cache.set(fallback_key, link, ffmpegcmd) # Cache fallback link and ffmpeg command
                                    else:
                                        link_cache.set(fallback_key, link) # Cache fallback link only

                                    # Update rate limit for fallback
                                    rate_limiter.update_rate(fallback_key) # Update rate limit timestamp

                                    logger.info(f"Fallback found in group {channelGroup} - using channel {fallbackChannelId} from Portal({fallbackPortalId})")
                                    add_alert("warning", f"Portal: {portals[fallbackPortalId]['name']}", f"Using fallback channel {channelName} (ID: {fallbackChannelId}) from group {channelGroup}") # Add alert
                                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                                        return Response(streamData(), mimetype="application/octet-stream") # Return stream using fallback ffmpeg command
                                    else:
                                        logger.info("Redirect sent")
                                        return redirect(link) # Redirect to fallback stream link

    if freeMac:
        logger.info(f"No working streams found for Portal({portalId}):Channel({channelId})")
        add_alert("error", f"Portal: {portalName}", f"No working streams found for channel {channelName} (ID: {channelId})") # Add alert if no working streams found even with free MAC
    else:
        logger.info(f"No free MAC for Portal({portalId}):Channel({channelId})")
        add_alert("error", f"Portal: {portalName}", f"No free MAC available for channel {channelName} (ID: {channelId})") # Add alert if no free MAC available

    return make_response("No streams available", 503) # Return 503 error if no streams available

#endregion

#region Route Handlers - Dashboard and Logs

@app.route("/dashboard")
@authorise
def dashboard():
    """
    Renders the dashboard page (dashboard.html).
    """
    return render_template("dashboard.html") # Render dashboard template

@app.route("/streaming")
@authorise
def streaming():
    """
    Returns the current streaming status (occupied MACs) in JSON format.
    """
    return jsonify(occupied) # Return occupied streams as JSON

@app.route("/log")
@authorise
def log():
    """
    Returns the content of the STB-Proxy.log file as plain text.
    """
    try:
        with open("STB-Proxy.log", "r", encoding='utf-8') as f: # Open and read log file
            log = f.read() # Read log file content
        return log
    except FileNotFoundError:
        return "Log file not found"

#endregion

#region HDHR Emulation Routes

def hdhr(f):
    """
    Decorator to enforce authentication and HDHR enabled setting for HDHR routes.
=======
    Returns VOD categories for a portal.
>>>>>>> Stashed changes

    Args:
        portalId (str): ID of the portal.

    Returns:
        JSON: List of VOD categories.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

<<<<<<< Updated upstream
                # Load channel and genre data from files for the first available MAC
                for mac in macs:
                    try:
                        name_path = os.path.join(parent_folder, name + ".json")
                        genre_path = os.path.join(parent_folder, name +"_genre"+ ".json")
                        with open(name_path, 'r') as file:
                            allChannels = json.load(file)
                        with open(genre_path, 'r') as file:
                            genres = json.load(file)
                        break # Break after loading data for the first MAC
                    except:
                        allChannels = None

                if allChannels: # If channel data loaded successfully
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels: # Process only enabled channels
                            channelName = customChannelNames.get(channelId) # Get custom channel name
                            if channelName == None:
                                channelName = str(channel.get("name")) # Use default name if custom not set
                            channelNumber = customChannelNumbers.get(channelId) # Get custom channel number
                            if channelNumber == None:
                                channelNumber = str(channel.get("number")) # Use default number if custom not set

                            lineup.append(
                                {
                                    "GuideNumber": channelNumber,
                                    "GuideName": channelName,
                                    "URL": "http://"
                                    + host
                                    + "/play/"
                                    + portal
                                    + "/"
                                    + channelId, # HDHR lineup entry data
                                }
                            )
                else:
                    logger.error("Error making lineup for {}, skipping".format(name))

    return flask.jsonify(lineup) # Return HDHR lineup as JSON

#endregion

#region Channel Group Routes - Web UI and API

@app.route("/channels", methods=["GET", "POST"])
@authorise
def channels():
    """
    Handles channel group management page (channels.html) and saving new channel groups.
    """
    if request.method == "POST": # Handle POST request for saving new group
        group_name = request.form["group_name"]
        portal_id = request.form["portal"]
        channel_ids = request.form["channels"].split(",") # Split channel IDs from form

        channel_groups = getChannelGroups()

        # Create new group entries with portal information
        channel_entries = []
        for channel_id in channel_ids:
            channel_id = channel_id.strip()
            if channel_id:  # Skip empty strings
                channel_entries.append({
                    "channelId": channel_id,
                    "portalId": portal_id
                })

        channel_groups[group_name] = channel_entries # Add new group to channel groups
        saveChannelGroups(channel_groups) # Save updated channel groups
        flash(f"Channel group '{group_name}' saved!", "success") # Flash success message
        return redirect("/channels", code=302) # Redirect back to channels page
    else: # Handle GET request for displaying channels page
        return render_template("channels.html", channel_groups=getChannelGroups(), portals=getPortals()) # Render channels template with channel group and portal data

@app.route("/channels/delete", methods=["POST"])
@authorise
def delete_channel_group():
    """
    API endpoint to delete a channel group.
    """
    data = request.get_json() # Get JSON data from request
    group_name = data.get('group_name') # Get group name from JSON data
    if group_name:
        channel_groups = getChannelGroups()
        if group_name in channel_groups:
            del channel_groups[group_name] # Delete group from channel groups
            saveChannelGroups(channel_groups) # Save updated channel groups
            flash(f"Channel group '{group_name}' deleted!", "success") # Flash success message
            return jsonify({"status": "success"}) # Return success status as JSON
    return jsonify({"status": "error"}), 400 # Return error status if group name not found

@app.route("/channels/get_group/<group_name>")
@authorise
def get_group(group_name):
    """
    API endpoint to retrieve channels in a specific group.
    """
    channel_groups = getChannelGroups()
    if group_name in channel_groups:
        return jsonify({"status": "success", "channels": channel_groups[group_name]}) # Return channels in group as JSON
    return jsonify({"status": "error", "message": "Group not found"}), 404 # Return error status if group not found

@app.route("/channels/add_channels", methods=["POST"])
@authorise
def add_channels():
    """
    API endpoint to add channels to a channel group.
    """
    data = request.get_json() # Get JSON data from request
    group_name = data.get("group_name") # Get group name from JSON data
    portal_id = data.get("portal") # Get portal ID from JSON data
    channel_ids = data.get("channels", "").split(",") # Get channel IDs from JSON data, split into list

    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404 # Return error status if group not found

    # Get portal info
    portals = getPortals()
    if portal_id not in portals:
        return jsonify({"status": "error", "message": "Portal not found"}), 404 # Return error status if portal not found

    portal = portals[portal_id]
    portal_name = portal["name"]
=======
    portalName = portals[portalId]["name"]
>>>>>>> Stashed changes

    try:
        # Load VOD categories from file
        vod_categories_path = os.path.join(parent_folder, f"{portalName}_vod_categories.json")
        with open(vod_categories_path, 'r') as file:
            vod_categories = json.load(file)

        # Filter to only include VOD categories (not Series)
        vod_categories = [category for category in vod_categories if category["type"] == "VOD"]
        return jsonify(vod_categories)
    except Exception as e:
        logger.error(f"Error getting VOD categories for {portalName}: {e}")
        return jsonify({"error": f"Error getting VOD categories: {str(e)}"}), 500

@app.route("/api/portal/<portalId>/series/categories", methods=["GET"])
@authorise
def getPortalSeriesCategories(portalId):
    """
    Returns Series categories for a portal.

    Args:
        portalId (str): ID of the portal.

    Returns:
        JSON: List of Series categories.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portalName = portals[portalId]["name"]

<<<<<<< Updated upstream
    # Remove the channel from the group
    channel_groups[group_name]["channels"] = [
        ch for ch in channel_groups[group_name]["channels"]
        if not (isinstance(ch, dict) and
                ch.get("channelId") == channel_id and
                ch.get("portalId") == portal_id) # Filter out the channel to remove
    ]

    saveChannelGroups(channel_groups) # Save updated channel groups
    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]["channels"] # Return updated channel list as JSON
    })

@app.route("/channels/create", methods=["POST"])
@authorise
def create_group():
    """
    API endpoint to create a new channel group.
    """
    data = request.get_json() # Get JSON data from request
    group_name = data.get("group_name") # Get group name from JSON data

    if not group_name:
        return jsonify({"status": "error", "message": "Group name is required"}), 400 # Return error status if group name is missing

    channel_groups = getChannelGroups()
    if group_name in channel_groups:
        return jsonify({"status": "error", "message": "Group already exists"}), 400 # Return error status if group already exists

    # Get the next order number starting from 1
    next_order = max([group["order"] for group in channel_groups.values()], default=0) + 1 # Determine next order number

    channel_groups[group_name] = {
        "channels": [],
        "logo": "",
        "order": next_order # Initialize new group with default values
    }
    saveChannelGroups(channel_groups) # Save updated channel groups

    return jsonify({"status": "success"}) # Return success status as JSON

@app.route("/channels/reorder", methods=["POST"])
@authorise
def reorder_channels():
    """
    API endpoint to reorder channels within a channel group.
    """
    data = request.get_json() # Get JSON data from request
    group_name = data.get("group_name") # Get group name from JSON data
    new_channels = data.get("channels") # Get new channel order from JSON data

    if not group_name or not new_channels:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400 # Return error status if missing parameters

    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404 # Return error status if group not found

    channel_groups[group_name]["channels"] = new_channels # Update channel order in group
    saveChannelGroups(channel_groups) # Save updated channel groups

    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]["channels"] # Return updated channel list as JSON
    })

@app.route("/channels/upload_logo", methods=["POST"])
@authorise
def upload_group_logo():
    """
    API endpoint to upload a logo for a channel group.
    """
    if 'logo' not in request.files or 'group_name' not in request.form:
        return jsonify({"status": "error", "message": "Missing logo or group name"}), 400 # Return error status if missing logo or group name

    file = request.files['logo'] # Get uploaded file
    group_name = request.form['group_name'] # Get group name from form

    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400 # Return error status if no file selected

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({"status": "error", "message": "Invalid file type"}), 400 # Return error status if invalid file type

    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404 # Return error status if group not found

    # Create logos directory if it doesn't exist
    logos_dir = os.path.join(basePath, "static", "logos")
    os.makedirs(logos_dir, exist_ok=True) # Create directory if not exists

    # Save the file with a unique name
    filename = f"group_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}" # Generate unique filename
    file_path = os.path.join(logos_dir, filename) # Construct file path
    file.save(file_path) # Save uploaded file

    # Update group logo path
    channel_groups[group_name]["logo"] = f"/static/logos/{filename}" # Update logo path in channel group config
    saveChannelGroups(channel_groups) # Save updated channel groups

    return jsonify({
        "status": "success",
        "logo_url": channel_groups[group_name]["logo"] # Return success status and logo URL as JSON
    })

@app.route("/channels/reorder_groups", methods=["POST"])
@authorise
def reorder_groups():
    """
    API endpoint to reorder channel groups.
    """
    data = request.get_json() # Get JSON data from request
    new_order = data.get("groups") # Get new group order from JSON data

    if not new_order:
        return jsonify({"status": "error", "message": "Missing groups order"}), 400 # Return error status if missing group order

    channel_groups = getChannelGroups()

    # Update group orders starting from 1
    for index, group_name in enumerate(new_order, start=1):
        if group_name in channel_groups:
            channel_groups[group_name]["order"] = index # Update group order

    saveChannelGroups(channel_groups) # Save updated channel groups
    return jsonify({"status": "success"}) # Return success status as JSON

#endregion

#region Channel Group Playback Route

@app.route("/chplay/<groupID>", methods=["GET"])
def chplay(groupID):
    """
    Handles playback for a channel group. Redirects to the first available working channel in the group.
    """
    group_name = groupID
    if not group_name:
        return make_response("Group parameter is required", 400) # Return 400 error if group ID is missing

    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return make_response(f"Group '{group_name}' not found", 404) # Return 404 error if group not found

    # Get all channels in the group
    if "channels" not in channel_groups[group_name]:
        return make_response(f"Invalid group structure for '{group_name}'", 404) # Return 404 error if invalid group structure

    channels = channel_groups[group_name]["channels"]
    if not channels:
        return make_response(f"No channels found in group '{group_name}'", 404) # Return 404 error if no channels in group

    # Try each channel in the group until we find one that works
    for channel in channels:
        if isinstance(channel, dict):
            portal_id = channel.get("portalId") # Get portal ID from channel entry
            channel_id = channel.get("channelId") # Get channel ID from channel entry
            if portal_id and channel_id:
                # Check if we have a cached link
                cache_key = f"{portal_id}:{channel_id}"
                cached_link, cached_ffmpegcmd = link_cache.get(cache_key)
                if cached_link: # If cached link found
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        return redirect(f"/play/{portal_id}/{channel_id}", code=302) # Redirect to play route with cached link
                    else:
                        return redirect(cached_link, code=302) # Redirect to cached link

                # If no cache, redirect to play route
                return redirect(f"/play/{portal_id}/{channel_id}", code=302) # Redirect to play route to get a new stream

    return make_response(f"No valid channels found in group '{group_name}'", 404) # Return 404 error if no valid channels found in group

#endregion

#region Alert Routes - Web UI and API

@app.route("/alerts", methods=["GET"])
@authorise
def alerts():
    """
    Renders the alerts page (alerts.html) with current alerts.
    """
    return render_template("alerts.html", alerts=load_alerts()) # Render alerts template with alert data

@app.route("/alerts/unresolved/count", methods=["GET"])
@authorise
def unresolved_alerts_count():
    """
    API endpoint to retrieve the count of unresolved (active) alerts.
    """
    alerts = load_alerts() # Load alerts
    count = sum(1 for alert in alerts if alert.get('status') == 'active') # Count active alerts
    return jsonify({"count": count}) # Return count as JSON

@app.route("/resolve_alert", methods=["POST"])
@authorise
def resolve_alert():
    """
    API endpoint to resolve an alert by its ID.
    """
=======
>>>>>>> Stashed changes
    try:
        # First try to load from series-specific file
        series_categories_path = os.path.join(parent_folder, f"{portalName}_series_categories.json")
        if os.path.exists(series_categories_path):
            with open(series_categories_path, 'r') as file:
                series_categories = json.load(file)
                return jsonify(series_categories)

        # If series-specific file doesn't exist, try to filter VOD categories
        vod_categories_path = os.path.join(parent_folder, f"{portalName}_vod_categories.json")
        with open(vod_categories_path, 'r') as file:
            vod_categories = json.load(file)

        # Filter to only include Series categories
        series_categories = [category for category in vod_categories if category["type"] == "Series"]
        return jsonify(series_categories)
    except Exception as e:
        logger.error(f"Error getting Series categories for {portalName}: {e}")
        return jsonify({"error": f"Error getting Series categories: {str(e)}"}), 500

<<<<<<< Updated upstream
        if alert_id >= len(alerts):
            return jsonify({"success": False, "error": "Invalid alert ID"}), 404 # Return error status if invalid alert ID

        # Update alert status
        alerts[alert_id]["status"] = "resolved" # Set alert status to resolved
        alerts[alert_id]["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Record resolve timestamp

        # Save updated alerts
        save_alerts(alerts) # Save updated alerts

        return jsonify({"success": True}) # Return success status as JSON
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500 # Return error status if exception occurred

#endregion

#region Background Tasks (Currently Empty)

# Add error handling for non-working channels (currently a placeholder function)
def check_channel_status(url, mac, token, proxy):
    """
    Placeholder function for checking channel status (currently does not perform actual checks).
    """
    try:
        response = stb.make_request(url, proxy) # Placeholder request
        if not response or response.status_code != 200: # Placeholder check
            add_alert("error", "Channel Check", f"Channel not responding: {url}") # Placeholder alert
            return False
        return True
    except Exception as e:
        add_alert("error", "Channel Check", f"Error checking channel {url}: {str(e)}") # Placeholder alert
        return False

#endregion

#region Main Application Entrypoint

if __name__ == "__main__":
    config = loadConfig() # Load configuration on startup
    if "TERM_PROGRAM" in os.environ.keys() and os.environ["TERM_PROGRAM"] == "vscode": # Check if running in VS Code debugger
        app.run(host="0.0.0.0", port=8001, debug=True) # Run in debug mode for VS Code
=======
def tryWithTokenRefresh(func, url, mac, token, proxy, *args, **kwargs):
    """
    Always refresh the token before executing a function and add a small delay to avoid 
    flooding the server with requests.

    Args:
        func: The function to execute
        url (str): Portal URL
        mac (str): MAC address
        token (str): Current token (will be refreshed)
        proxy (str, optional): Proxy URL
        *args: Additional positional arguments for the function
        **kwargs: Additional keyword arguments for the function

    Returns:
        The result of the function call

    Raises:
        Exception: If the function call fails even after token refresh
    """
    # Find the portal that contains this MAC address to get the device IDs and signature
    portals = getPortals()
    device_id = None
    device_id2 = None
    signature = None
    timestamp = None

    # Check for "*" in arguments and replace with "all" for API calls
    modified_args = []
    for arg in args:
        if arg == "*":
            modified_args.append("all")
        else:
            modified_args.append(arg)
    
    for portal_id, portal in portals.items():
        if portal.get("url") == url and mac in portal.get("macs", {}):
            # Found the portal, get the device IDs and signature
            if mac in portal.get("ids", {}):
                ids = portal["ids"][mac]
                device_id = ids.get("device_id")
                device_id2 = ids.get("device_id2")
                signature = ids.get("signature")
                timestamp = ids.get("timestamp")
                break

    # Always refresh the token before trying the API call
    logger.info(f"Refreshing token for MAC {mac} before API call")
    new_token = stb.refreshToken(url, mac, proxy, device_id, device_id2, signature, timestamp)
    
    if new_token:
        logger.info(f"Token refreshed successfully, using new token")
        token = new_token
>>>>>>> Stashed changes
    else:
        logger.warning(f"Token refresh failed, using existing token")

    # Add a small delay to avoid flooding the server with requests
    import time
    time.sleep(0.5)  # 500ms delay between requests

    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Try with the token (which should be the new token if refresh was successful)
            result = func(url, mac, token, proxy=proxy, *modified_args, **kwargs)
            
            # Check if the response is a string that might indicate an error
            if isinstance(result, str):
                # Keep track of the original string for error reporting
                original_response = result
                
                # Convert to lowercase for consistent checking
                result_lower = result.lower()
                
                if "error" in result_lower or "failed" in result_lower:
                    logger.warning(f"API call returned a string that might be an error: {result}")
                    
                    # Check for auth failures
                    if "authorization failed" in result_lower or "auth failed" in result_lower or "auth error" in result_lower:
                        if retry_count < max_retries:
                            # Try token refresh again
                            retry_count += 1
                            logger.info(f"Authorization failed based on response, trying token refresh again (attempt {retry_count})")
                            time.sleep(1)  # Longer delay before retry
                            new_token = stb.refreshToken(url, mac, proxy, device_id, device_id2, signature, timestamp)
                            if new_token:
                                token = new_token
                                time.sleep(0.5)  # Small delay before retrying
                                continue  # Try request again
                            else:
                                # If refresh failed, return the original error
                                logger.error(f"Token refresh failed on retry {retry_count}")
                        else:
                            # Max retries reached
                            logger.error(f"Authorization failed after {max_retries} token refresh attempts")
                    
                    # Return the string response for the caller to handle
                    return original_response
                
                # If it's just other string data (not an error), return it
                return result
            
            # If we got a valid result (not a string), return it
            return result
            
        except Exception as e:
            error_message = str(e)
            if "Authorization failed" in error_message:
                if retry_count < max_retries:
                    # Try token refresh again
                    retry_count += 1
                    logger.info(f"Authorization exception, trying token refresh again (attempt {retry_count})")
                    time.sleep(1)  # Longer delay before retry
                    new_token = stb.refreshToken(url, mac, proxy, device_id, device_id2, signature, timestamp)
                    if new_token:
                        token = new_token
                        time.sleep(0.5)  # Small delay before retrying
                        continue  # Try request again
                    else:
                        # If refresh failed, raise exception
                        logger.error(f"Token refresh failed on retry {retry_count}")
                else:
                    # Max retries reached
                    logger.error(f"Authorization failed after {max_retries} token refresh attempts")
                    raise Exception("Failed to refresh token. Please update the portal manually.")
            else:
                # If it's not an authorization error, re-raise the exception
                raise
    
    # If we've exhausted all retries, return the original error
    if 'original_response' in locals():
        return original_response
    else:
        raise Exception("Maximum retries exceeded with no valid response")


def ensure_cache_directory(portal_id, portal_name):
    """
    Ensures that the cache directory structure exists for a given portal.
    
    Args:
        portal_id (str): ID of the portal.
        portal_name (str): Name of the portal (used for file naming).
        
    Returns:
        str: Path to the portal's cache directory.
    """
    try:
        # Define cache paths relative to application root
        basePath = os.path.abspath(os.getcwd())
        main_cache_dir = os.path.join(basePath, "cache")
        portal_cache_path = os.path.join(main_cache_dir, portal_id)
        
        # Create main cache directory if it doesn't exist
        if not os.path.exists(main_cache_dir):
            os.makedirs(main_cache_dir)
            logger.info(f"Created main cache directory: {main_cache_dir}")
            
        # Create portal-specific cache directory if it doesn't exist
        if not os.path.exists(portal_cache_path):
            os.makedirs(portal_cache_path)
            logger.info(f"Created cache directory for portal {portal_name} ({portal_id}): {portal_cache_path}")
            
        logger.debug(f"Using cache directory: {portal_cache_path}")
        return portal_cache_path
    except Exception as e:
        logger.error(f"Error creating cache directory: {e}")
        # Fall back to a simple path if there's an error
        return os.path.join(basePath, "cache", portal_id)

@app.route("/api/portal/<portalId>/vod/category/<categoryId>/items", methods=["GET"])
@authorise
def getVodCategoryItems(portalId, categoryId):
    """
    Returns VOD items for a category. First tries to load from cached JSON file,
    then falls back to fetching from the portal API.

    Args:
        portalId (str): ID of the portal.
        categoryId (str): ID of the category.

    Returns:
        JSON: List of VOD items.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portal = portals[portalId]
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    # Path to cached VOD items file
    vod_items_path = get_vod_items_path(portalId, categoryId)
    
    # Try to load from cache unless force refresh is requested
    if not force_refresh and os.path.exists(vod_items_path):
        try:
            items = load_json_content(vod_items_path)
            if items:
                # Fix any relative screenshot URLs
                items = fix_screenshot_urls(items, portal["url"])
                logger.info(f"Serving VOD items for portal {portalId}, category {categoryId} from cache")
                return jsonify(items)
        except Exception as e:
            logger.error(f"Error loading cached VOD items: {e}")
    
    # If not in cache or refresh requested, fetch from API
    logger.info(f"Fetching VOD items for portal {portalId}, category {categoryId} from API")
    try:
        url = portal["url"]
        macs = list(portal["macs"].keys())
        if not macs:
            return jsonify({"error": "No MACs available"}), 400

        mac = macs[0]
        
        # Get token - portal["macs"][mac] might be a string (expiry date) rather than a dict
        # Always get a fresh token to avoid attribute errors
        token = stb.getToken(url, mac, portal["proxy"])
        if not token:
            logger.error(f"Failed to obtain token for portal {portalId}, MAC {mac}")
            return jsonify({"error": "Failed to authenticate with portal"}), 500

        proxy = portal["proxy"]
        
        # Try to get items using tryWithTokenRefresh
        items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", categoryId)
        
        # Check if the response is a string instead of the expected list
        if isinstance(items, str):
            logger.error(f"Error fetching VOD items: received string response: {items}")
            return jsonify({"error": f"Invalid API response format: {items}"}), 500
        
        # Check if items is None or empty
        if not items:
            logger.warning(f"No VOD items found for category {categoryId}")
            return jsonify([]) # Return empty list
        
        # Fix any relative screenshot URLs
        items = fix_screenshot_urls(items, url)
        
        # Save items to cache file
        save_content_json(vod_items_path, items)
        
        return jsonify(items)
    except Exception as e:
        logger.error(f"Error fetching VOD items: {str(e)}")
        logger.exception("Traceback:")
        return jsonify({"error": f"Error fetching VOD items: {str(e)}"}), 500

@app.route("/api/portal/<portalId>/series/category/<categoryId>/items", methods=["GET"])
@authorise
def getSeriesCategoryItems(portalId, categoryId):
    """
    Returns Series items for a category. First tries to load from cached JSON file,
    then falls back to fetching from the portal API.

    Args:
        portalId (str): ID of the portal.
        categoryId (str): ID of the category.

    Returns:
        JSON: List of Series items.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portal = portals[portalId]
    url = portal["url"]
    macs = list(portal["macs"].keys())
    proxy = portal["proxy"]
    portal_name = portal["name"]
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    # Path to cached Series items file
    series_items_path = get_series_items_path(portalId, categoryId)
    
    # Try to load from cache unless force refresh is requested
    if not force_refresh and os.path.exists(series_items_path):
        try:
            items = load_json_content(series_items_path)
            if items:
                # Fix any relative screenshot URLs
                items = fix_screenshot_urls(items, url)
                logger.info(f"Serving Series items for portal {portalId}, category {categoryId} from cache")
                return jsonify(items)
        except Exception as e:
            logger.error(f"Error loading cached Series items: {e}")

    # Handle special "No Series Found" category
    if categoryId == "0":
        logger.info("Special 'No Series Found' category requested - returning empty list")
        return jsonify([{
            "id": "0",
            "title": "No Series Found",
            "type": "Series"
        }])

    # Fetch from portal API
    logger.info(f"Fetching Series items for portal {portalId}, category {categoryId} from API")
    try:
        # Get token for the first available MAC
        mac = macs[0]
        
        # Always get a fresh token to avoid attribute errors since portal["macs"][mac] might be a string (expiry date)
        token = stb.getToken(url, mac, proxy)
        if not token:
            return jsonify({"error": "Failed to get token"}), 500

        # Fetch Series items with automatic token refresh
        try:
            # First try with series type
            try:
                items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "series", categoryId)
                
                # Add type checking for the API response
                if isinstance(items, str):
                    logger.error(f"API returned a string instead of a list/dict for series type: {items}")
                    # Try with VOD type instead
                    logger.info(f"Trying VOD type for category {categoryId} after receiving string response")
                    raise Exception("API returned string, trying VOD type instead")
                
                # Ensure items is a list
                if not isinstance(items, list):
                    logger.error(f"API returned non-list response: {type(items)}")
                    if items is None:
                        items = []
                    else:
                        # Convert to list if possible, otherwise create a list with the single item
                        try:
                            items = list(items)
                        except Exception:
                            items = [items] if items else []
                            
                # Fix any relative screenshot URLs
                items = fix_screenshot_urls(items, url)
            except Exception as e:
                if "Authorization failed" in str(e) or "Failed to refresh token" in str(e):
                    # If we can't refresh the token, return an auth error
                    logger.error(f"Authorization error that couldn't be resolved with token refresh: {e}")
                    return jsonify({
                        "error": "Authorization failed",
                        "message": "The portal token has expired and could not be refreshed. Please refresh the portal data manually.",
                        "type": "auth_error"
                    }), 401

                # For other errors, try with vod type
                logger.info(f"Error with series type: {e}, trying vod type for category {categoryId}")
                try:
                    items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", categoryId)
                    
                    # Add type checking for the API response
                    if isinstance(items, str):
                        logger.error(f"API returned a string instead of a list/dict for VOD type: {items}")
                        return jsonify({
                            "error": "Invalid API response format",
                            "message": f"Expected list/dict but received string: {items[:100]}...",
                            "type": "format_error"
                        }), 500
                    
                    # Ensure items is a list
                    if not isinstance(items, list):
                        logger.error(f"API returned non-list response: {type(items)}")
                        if items is None:
                            items = []
                        else:
                            # Convert to list if possible, otherwise create a list with the single item
                            try:
                                items = list(items)
                            except Exception:
                                items = [items] if items else []
                                
                    # Fix any relative screenshot URLs
                    items = fix_screenshot_urls(items, url)
                except Exception as e2:
                    if "Authorization failed" in str(e2) or "Failed to refresh token" in str(e2):
                        # If we can't refresh the token, return an auth error
                        logger.error(f"Authorization error that couldn't be resolved with token refresh: {e2}")
                        return jsonify({
                            "error": "Authorization failed",
                            "message": "The portal token has expired and could not be refreshed. Please refresh the portal data manually.",
                            "type": "auth_error"
                        }), 401
                    # For other errors, just raise
                    raise e2

            if not items:
                # Try with vod type if series type returns empty
                logger.info(f"No items found with series type, trying vod type for category {categoryId}")
                try:
                    items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", categoryId)
                    
                    # Ensure items is a list
                    if not isinstance(items, list):
                        logger.error(f"API returned non-list response: {type(items)}")
                        if items is None:
                            items = []
                        elif isinstance(items, str):
                            logger.error(f"API returned a string instead of a list/dict: {items}")
                            return jsonify({"error": "No items found"}), 404
                        else:
                            # Convert to list if possible, otherwise create a list with the single item
                            try:
                                items = list(items)
                            except Exception:
                                items = [items] if items else []
                except Exception as e:
                    if "Authorization failed" in str(e) or "Failed to refresh token" in str(e):
                        # If we can't refresh the token, return an auth error
                        logger.error(f"Authorization error that couldn't be resolved with token refresh: {e}")
                        return jsonify({
                            "error": "Authorization failed",
                            "message": "The portal token has expired and could not be refreshed. Please refresh the portal data manually.",
                            "type": "auth_error"
                        }), 401
                    # For other errors, just raise
                    raise e

                if not items:
                    logger.info(f"No items found in category {categoryId} for either series or vod type")
                    return jsonify({"error": "No items found"}), 404

                # Filter to only include Series items, checking each item is a dict first
                filtered_items = []
                for item in items:
                    if isinstance(item, dict) and item.get("item_type") == "Series":
                        filtered_items.append(item)
                    elif isinstance(item, str):
                        logger.warning(f"Skipping string item in series list: {item}")
                
                items = filtered_items
                if not items:
                    logger.info(f"No Series items found in category {categoryId} after filtering vod items")
                    return jsonify({"error": "No Series items found in this category"}), 404
            else:
                # Ensure all items are dictionaries
                filtered_items = []
                for item in items:
                    if isinstance(item, dict):
                        filtered_items.append(item)
                    elif isinstance(item, str):
                        logger.warning(f"Skipping string item in series list: {item}")
                
                items = filtered_items
        except Exception as e:
            logger.error(f"Error fetching Series items: {e}")
            error_message = str(e)

            # Check for authorization errors that couldn't be resolved with token refresh
            if "Authorization failed" in error_message or "Failed to refresh token" in error_message:
                return jsonify({
                    "error": "Authorization failed",
                    "message": "The portal token has expired and could not be refreshed. Please refresh the portal data manually.",
                    "type": "auth_error"
                }), 401

            return jsonify({
                "error": "Error fetching Series items",
                "message": error_message,
                "type": "general_error"
            }), 500

        # Save items to cache file if we have valid items
        if items:
            save_content_json(series_items_path, items)

        return jsonify(items)
    except Exception as e:
        logger.error(f"Error fetching Series items for {portal_name}, category {categoryId}: {e}")
        return jsonify({"error": f"Error fetching Series items: {str(e)}"}), 500

@app.route("/api/portal/<portalId>/series/<seriesId>/seasons", methods=["GET"])
@authorise
def getSeriesSeasons(portalId, seriesId):
    """
    Returns seasons for a series. First tries to load from cached JSON file,
    then falls back to fetching from the portal API.

    Args:
        portalId (str): ID of the portal.
        seriesId (str): ID of the series.

    Returns:
        JSON: List of seasons.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portal = portals[portalId]
    url = portal["url"]
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    # Path to cached seasons file
    seasons_path = get_seasons_path(portalId, seriesId)
    
    # Try to load from cache unless force refresh is requested
    if not force_refresh and os.path.exists(seasons_path):
        try:
            seasons = load_json_content(seasons_path)
            if seasons:
                # Fix any relative screenshot URLs
                seasons = fix_screenshot_urls(seasons, url)
                logger.info(f"Serving seasons for portal {portalId}, series {seriesId} from cache")
                return jsonify(seasons)
        except Exception as e:
            logger.error(f"Error loading cached seasons: {e}")
    
    # If not in cache or refresh requested, fetch from API
    logger.info(f"Fetching seasons for portal {portalId}, series {seriesId} from API")
    try:
        url = portal["url"]
        macs = list(portal["macs"].keys())
        if not macs:
            return jsonify({"error": "No MACs available"}), 400

        mac = macs[0]
        
        # Get token - always get a fresh token to avoid attribute errors
        token = stb.getToken(url, mac, portal["proxy"])
        if not token:
            logger.error(f"Failed to obtain token for portal {portalId}, MAC {mac}")
            return jsonify({"error": "Failed to authenticate with portal"}), 500

        proxy = portal["proxy"]
        
        # Try to get seasons using tryWithTokenRefresh
        seasons = tryWithTokenRefresh(stb.getSeriesSeasons, url, mac, token, proxy, seriesId)
        
        # Check if the response is a string instead of the expected list
        if isinstance(seasons, str):
            logger.error(f"Error fetching seasons: received string response: {seasons}")
            return jsonify({"error": f"Invalid API response format: {seasons}"}), 500
        
        # Check if seasons is None or empty
        if not seasons:
            logger.warning(f"No seasons found for series {seriesId}")
            return jsonify([]) # Return empty list
        
        # Fix any relative screenshot URLs
        seasons = fix_screenshot_urls(seasons, url)
        
        # Save seasons to cache file
        save_content_json(seasons_path, seasons)
        
        return jsonify(seasons)
    except Exception as e:
        logger.error(f"Error fetching seasons: {str(e)}")
        logger.exception("Traceback:")
        return jsonify({"error": f"Error fetching seasons: {str(e)}"}), 500

@app.route("/api/portal/<portalId>/series/<seriesId>/season/<seasonId>/episodes", methods=["GET"])
@authorise
def getSeasonEpisodes(portalId, seriesId, seasonId):
    """
    Returns episodes for a season. First tries to load from cached JSON file,
    then falls back to fetching from the portal API.

    Args:
        portalId (str): ID of the portal.
        seriesId (str): ID of the series.
        seasonId (str): ID of the season.

    Returns:
        JSON: List of episodes.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portal = portals[portalId]
    url = portal["url"]
    macs = list(portal["macs"].keys())
    proxy = portal["proxy"]
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    # Path to cached episodes file
    episodes_path = get_episodes_path(portalId, seriesId, seasonId)
    
    # Try to load from cache unless force refresh is requested
    if not force_refresh and os.path.exists(episodes_path):
        try:
            episodes = load_json_content(episodes_path)
            if episodes:
                # Fix any relative screenshot URLs
                episodes = fix_screenshot_urls(episodes, url)
                logger.info(f"Serving episodes for portal {portalId}, series {seriesId}, season {seasonId} from cache")
                return jsonify(episodes)
        except Exception as e:
            logger.error(f"Error loading cached episodes: {e}")
    
    # Fetch from portal API
    logger.info(f"Fetching episodes for portal {portalId}, series {seriesId}, season {seasonId} from API")
    try:
        if not macs:
            return jsonify({"error": "No MACs available"}), 400
        
        # Get token for the first available MAC
        mac = macs[0]
        
        # Get token - always get a fresh token to avoid attribute errors
        token = stb.getToken(url, mac, proxy)
        if not token:
            logger.error(f"Failed to obtain token for portal {portalId}, MAC {mac}")
            return jsonify({"error": "Failed to authenticate with portal"}), 500

        # Fetch episodes with automatic token refresh
        try:
            episodes = tryWithTokenRefresh(stb.getSeasonEpisodes, url, mac, token, proxy, seriesId, seasonId)
            
            # Add type checking for the API response
            if isinstance(episodes, str):
                logger.error(f"API returned a string instead of a list for episodes: {episodes}")
                return jsonify({
                    "error": "Invalid API response format",
                    "message": f"Expected list but received string: {episodes[:100]}...",
                    "type": "format_error"
                }), 500
                
            if not episodes:
                logger.warning(f"No episodes found for series {seriesId}, season {seasonId}")
                return jsonify([]) # Return empty list
                
            # Fix any relative screenshot URLs
            episodes = fix_screenshot_urls(episodes, url)
        except Exception as e:
            logger.error(f"Error fetching episodes: {e}")
            error_message = str(e)

            # Check for authorization errors that couldn't be resolved with token refresh
            if "Authorization failed" in error_message or "Failed to refresh token" in error_message:
                return jsonify({
                    "error": "Authorization failed",
                    "message": "The portal token has expired and could not be refreshed. Please refresh the portal data manually.",
                    "type": "auth_error"
                }), 401

            return jsonify({
                "error": "Error fetching episodes",
                "message": error_message,
                "type": "general_error"
            }), 500

        # Save episodes to cache file
        save_content_json(episodes_path, episodes)

        return jsonify(episodes)
    except Exception as e:
        logger.error(f"Error fetching episodes for series {seriesId}, season {seasonId}: {e}")
        logger.exception("Traceback:")
        return jsonify({"error": f"Error fetching episodes: {str(e)}"}), 500

<<<<<<< Updated upstream
#endregion
=======
#endregion

#region Deprecated Cache API Routes (Redirects to Unified API)

@app.route("/api/cached/vod_categories/<portalId>", methods=["GET"])
def getCachedVodCategories(portalId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/vod/{portalId}/categories instead.
    """
    return redirect(f"/api/cache/vod/{portalId}/categories", code=302)

@app.route("/api/cached/series_categories/<portalId>", methods=["GET"])
def getCachedSeriesCategories(portalId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/series/{portalId}/categories instead.
    """
    return redirect(f"/api/cache/series/{portalId}/categories", code=302)

@app.route("/api/cached/vod_items/<portalId>/<categoryId>", methods=["GET"])
def getCachedVodItems(portalId, categoryId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/vod/{portalId}/category/{categoryId} instead.
    """
    return redirect(f"/api/cache/vod/{portalId}/category/{categoryId}", code=302)

@app.route("/api/cached/series_items/<portalId>/<categoryId>", methods=["GET"])
def getCachedSeriesItems(portalId, categoryId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/series/{portalId}/category/{categoryId} instead.
    """
    return redirect(f"/api/cache/series/{portalId}/category/{categoryId}", code=302)

@app.route("/api/cached/series_seasons/<portalId>/<seriesId>", methods=["GET"])
def getCachedSeriesSeasons(portalId, seriesId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/series/{portalId}/id/{seriesId} instead.
    """
    return redirect(f"/api/cache/series/{portalId}/id/{seriesId}", code=302)

@app.route("/api/cached/series_episodes/<portalId>/<seriesId>/<seasonId>", methods=["GET"])
def getCachedSeriesEpisodes(portalId, seriesId, seasonId):
    """
    [DEPRECATED] Redirects to the unified cache API.
    Use /api/cache/series/{portalId}/id/{seriesId}/season/{seasonId} instead.
    """
    return redirect(f"/api/cache/series/{portalId}/id/{seriesId}/season/{seasonId}", code=302)

@app.route("/api/cached/all_movies/<portalId>", methods=["GET"])
def getCachedAllMovies(portalId):
    """
    [DEPRECATED] This endpoint is deprecated.
    The 'all movies' functionality should be implemented on the client-side
    by fetching categories and combining movie items.
    """
    try:
        # Get portal details
        portals = getPortals()
        if portalId not in portals:
            return jsonify({"error": "Portal not found"}), 404
            
        portal = portals[portalId]
        portalName = portal.get("name")
        
        # Get VOD categories and fetch all items
        all_movies = []
        
        # Get categories via the unified cache API
        categories_response = get_cached_content("vod", portalId, "categories")
        if not isinstance(categories_response, flask.Response) or categories_response.status_code != 200:
            return jsonify({"error": "Failed to fetch VOD categories"}), 500
            
        categories = json.loads(categories_response.get_data(as_text=True))
        
        # Fetch items for each category
        for category in categories:
            if not isinstance(category, dict):
                continue
                
            category_id = category.get("id")
            if not category_id:
                continue
                
            # Get items via the unified cache API
            items_response = get_cached_content("vod", portalId, f"category/{category_id}")
            if not isinstance(items_response, flask.Response) or items_response.status_code != 200:
                continue
                
            items = json.loads(items_response.get_data(as_text=True))
            
            # Add category info to each item
            for item in items:
                if isinstance(item, dict):
                    item["category_id"] = category_id
                    item["category_name"] = category.get("title", "Unknown")
                    all_movies.append(item)
        
        return jsonify(all_movies)
    except Exception as e:
        logger.error(f"Error retrieving all cached movies: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cached/all_series/<portalId>", methods=["GET"])
def getCachedAllSeries(portalId):
    """
    [DEPRECATED] This endpoint is deprecated.
    The 'all series' functionality should be implemented on the client-side
    by fetching categories and combining series items.
    """
    try:
        # Get portal details
        portals = getPortals()
        if portalId not in portals:
            return jsonify({"error": "Portal not found"}), 404
            
        portal = portals[portalId]
        portalName = portal.get("name")
        
        # Get Series categories and fetch all items
        all_series = []
        
        # Get categories via the unified cache API
        categories_response = get_cached_content("series", portalId, "categories")
        if not isinstance(categories_response, flask.Response) or categories_response.status_code != 200:
            return jsonify({"error": "Failed to fetch Series categories"}), 500
            
        categories = json.loads(categories_response.get_data(as_text=True))
        
        # Fetch items for each category
        for category in categories:
            if not isinstance(category, dict):
                continue
                
            category_id = category.get("id")
            if not category_id:
                continue
                
            # Get items via the unified cache API
            items_response = get_cached_content("series", portalId, f"category/{category_id}")
            if not isinstance(items_response, flask.Response) or items_response.status_code != 200:
                continue
                
            items = json.loads(items_response.get_data(as_text=True))
            
            # Add category info to each item
            for item in items:
                if isinstance(item, dict):
                    item["category_id"] = category_id
                    item["category_name"] = category.get("title", "Unknown")
                    all_series.append(item)
        
        return jsonify(all_series)
    except Exception as e:
        logger.error(f"Error retrieving all cached series: {e}")
        return jsonify({"error": str(e)}), 500

#endregion

#region Content Management Functions

def ensure_content_directories():
    """
    Ensures that the content directory structure exists.
    Creates the main content directory and subdirectories for vod and series.
    
    Returns:
        tuple: Paths to the content directories (content_dir, vod_dir, series_dir)
    """
    content_dir = os.path.join(parent_folder, "content")
    vod_dir = os.path.join(content_dir, "vod")
    series_dir = os.path.join(content_dir, "series")
    
    # Create directories if they don't exist
    for directory in [content_dir, vod_dir, series_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    
    return content_dir, vod_dir, series_dir

def get_vod_items_path(portal_id, category_id):
    """
    Returns the path to the JSON file for VOD items of a specific category.
    
    Args:
        portal_id (str): ID of the portal.
        category_id (str): ID of the category.
        
    Returns:
        str: Path to the VOD items JSON file.
    """
    _, vod_dir, _ = ensure_content_directories()
    portal_vod_dir = os.path.join(vod_dir, portal_id)
    
    # Create portal-specific directory if it doesn't exist
    if not os.path.exists(portal_vod_dir):
        os.makedirs(portal_vod_dir)
    
    # Replace "*" with "all" for the "all categories" case to avoid invalid filename errors
    safe_category_id = "all" if category_id == "*" else category_id
        
    return os.path.join(portal_vod_dir, f"category_{safe_category_id}.json")

def get_series_items_path(portal_id, category_id):
    """
    Returns the path to the JSON file for Series items of a specific category.
    
    Args:
        portal_id (str): ID of the portal.
        category_id (str): ID of the category.
        
    Returns:
        str: Path to the Series items JSON file.
    """
    _, _, series_dir = ensure_content_directories()
    portal_series_dir = os.path.join(series_dir, portal_id)
    
    # Create portal-specific directory if it doesn't exist
    if not os.path.exists(portal_series_dir):
        os.makedirs(portal_series_dir)
    
    # Replace "*" with "all" for the "all categories" case to avoid invalid filename errors
    safe_category_id = "all" if category_id == "*" else category_id
    
    return os.path.join(portal_series_dir, f"category_{safe_category_id}.json")

def get_seasons_path(portal_id, series_id):
    """
    Returns the path to the JSON file for seasons of a specific series.
    
    Args:
        portal_id (str): ID of the portal.
        series_id (str): ID of the series.
        
    Returns:
        str: Path to the seasons JSON file.
    """
    _, _, series_dir = ensure_content_directories()
    portal_series_dir = os.path.join(series_dir, portal_id)
    
    # Create portal-specific directory if it doesn't exist
    if not os.path.exists(portal_series_dir):
        os.makedirs(portal_series_dir)
    
    # Replace "*" with "all" for the "all series" case and sanitize other special characters
    safe_series_id = "all" if series_id == "*" else series_id.replace(":", "_").replace("/", "_").replace("\\", "_")
    
    return os.path.join(portal_series_dir, f"series_{safe_series_id}_seasons.json")

def get_episodes_path(portal_id, series_id, season_id):
    """
    Returns the path to the JSON file for episodes of a specific season of a series.
    
    Args:
        portal_id (str): ID of the portal.
        series_id (str): ID of the series.
        season_id (str): ID of the season.
        
    Returns:
        str: Path to the episodes JSON file.
    """
    _, _, series_dir = ensure_content_directories()
    portal_series_dir = os.path.join(series_dir, portal_id)
    
    # Create portal-specific directory if it doesn't exist
    if not os.path.exists(portal_series_dir):
        os.makedirs(portal_series_dir)
    
    # Sanitize file path components
    safe_series_id = "all" if series_id == "*" else series_id.replace(":", "_").replace("/", "_").replace("\\", "_")
    safe_season_id = "all" if season_id == "*" else season_id.replace(":", "_").replace("/", "_").replace("\\", "_")
    
    return os.path.join(portal_series_dir, f"series_{safe_series_id}_season_{safe_season_id}_episodes.json")

def load_json_content(file_path, default=None):
    """
    Loads content from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file.
        default: Default value to return if file doesn't exist or can't be parsed.
        
    Returns:
        The loaded JSON content or the default value.
    """
    if default is None:
        default = []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Could not load content from {file_path}: {e}")
        return default

def save_content_json(file_path, content):
    """
    Saves content to a JSON file.
    
    Args:
        file_path (str): Path to the JSON file.
        content: Content to save.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(content, file, indent=4)
        logger.info(f"Content saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving content to {file_path}: {e}")
        return False

#endregion

#region Prefetch Content

@app.route("/api/portal/<portalId>/prefetch", methods=["POST"])
@authorise
def prefetchPortalContent(portalId):
    """
    Prefetches and caches all content for a portal (VODs, Series, Seasons, Episodes).
    This is a long-running operation that runs in the background.

    Args:
        portalId (str): ID of the portal.

    Returns:
        JSON: Status message.
    """
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404

    portal = portals[portalId]
    portal_name = portal.get("name")
    
    # Start the prefetch process in a background thread
    def prefetch_worker():
        """Background worker function to prefetch all content"""
        try:
            logger.info(f"Starting content prefetch for portal {portal_name} ({portalId})")
            
            url = portal["url"]
            macs = list(portal["macs"].keys())
            proxy = portal["proxy"]
            
            if not macs:
                logger.error(f"No MACs available for portal {portal_name}")
                return
                
            mac = macs[0]
            # Always get a fresh token to avoid attribute errors
            token = stb.getToken(url, mac, proxy)
            if not token:
                logger.error(f"Failed to get token for portal {portal_name}")
                return
                
            # 1. Prefetch VOD categories
            try:
                vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
                with open(vod_categories_path, 'r') as file:
                    vod_categories = json.load(file)
                
                # Filter to only include VOD categories
                vod_categories = [category for category in vod_categories if category.get("type") == "VOD"]
                
                logger.info(f"Prefetching {len(vod_categories)} VOD categories for portal {portal_name}")
                
                # Process each VOD category
                for i, category in enumerate(vod_categories):
                    try:
                        category_id = category.get("id")
                        if not category_id:
                            continue
                            
                        logger.info(f"Prefetching VOD category {i+1}/{len(vod_categories)}: {category.get('title')} ({category_id})")
                        
                        # Get the items
                        vod_items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", category_id)
                        
                        # Check if the response is valid
                        if isinstance(vod_items, str) or not vod_items:
                            logger.warning(f"Skipping VOD category {category_id}: invalid response")
                            continue
                            
                        # Save to cache
                        vod_items_path = get_vod_items_path(portalId, category_id)
                        save_content_json(vod_items_path, vod_items)
                        
                        logger.info(f"Cached {len(vod_items)} VOD items for category {category_id}")
                        
                        # Add a small delay to avoid overwhelming the API
                        time.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Error prefetching VOD category {category.get('id')}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error prefetching VOD categories: {e}")
            
            # 2. Prefetch Series categories and items
            try:
                # Try to load from series-specific file first
                series_categories_path = os.path.join(parent_folder, f"{portal_name}_series_categories.json")
                if os.path.exists(series_categories_path):
                    with open(series_categories_path, 'r') as file:
                        series_categories = json.load(file)
                else:
                    # Fall back to filtering VOD categories
                    vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
                    with open(vod_categories_path, 'r') as file:
                        all_categories = json.load(file)
                        series_categories = [category for category in all_categories if category.get("type") == "Series"]
                
                logger.info(f"Prefetching {len(series_categories)} Series categories for portal {portal_name}")
                
                # Process each Series category
                for i, category in enumerate(series_categories):
                    try:
                        category_id = category.get("id")
                        if not category_id:
                            continue
                            
                        logger.info(f"Prefetching Series category {i+1}/{len(series_categories)}: {category.get('title')} ({category_id})")
                        
                        # First try with series type, then with vod type
                        try:
                            series_items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "series", category_id)
                            
                            # Check if the response is a string
                            if isinstance(series_items, str):
                                # Try with VOD type instead
                                series_items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", category_id)
                                
                            # Ensure items is a list
                            if not isinstance(series_items, list):
                                if series_items is None:
                                    series_items = []
                                else:
                                    # Convert to list if possible
                                    try:
                                        series_items = list(series_items)
                                    except:
                                        series_items = [series_items] if series_items else []
                            
                            # Filter to only include Series items
                            filtered_items = []
                            for item in series_items:
                                if isinstance(item, dict) and (
                                    item.get("item_type") == "Series" or 
                                    item.get("type") == "Series"
                                ):
                                    filtered_items.append(item)
                                elif isinstance(item, str):
                                    # Skip string items
                                    continue
                            
                            series_items = filtered_items
                            
                        except Exception as e:
                            logger.error(f"Error fetching series items for category {category_id}: {e}")
                            series_items = []
                        
                        # Check if we got valid items
                        if not series_items:
                            logger.warning(f"No Series items found for category {category_id}")
                            continue
                            
                        # Save to cache
                        series_items_path = get_series_items_path(portalId, category_id)
                        save_content_json(series_items_path, series_items)
                        
                        logger.info(f"Cached {len(series_items)} Series items for category {category_id}")
                        
                        # 3. Prefetch seasons and episodes for each series
                        logger.info(f"Prefetching seasons and episodes for {len(series_items)} series in category {category_id}")
                        
                        for j, series in enumerate(series_items):
                            try:
                                series_id = series.get("id")
                                if not series_id:
                                    continue
                                    
                                logger.info(f"Prefetching series {j+1}/{len(series_items)}: {series.get('name', series.get('title', 'Unknown'))} ({series_id})")
                                
                                # Get seasons
                                seasons = tryWithTokenRefresh(stb.getSeriesSeasons, url, mac, token, proxy, series_id)
                                
                                # Check if the response is valid
                                if isinstance(seasons, str) or not seasons:
                                    logger.warning(f"Skipping seasons for series {series_id}: invalid response")
                                    continue
                                    
                                # Save seasons to cache
                                seasons_path = get_seasons_path(portalId, series_id)
                                save_content_json(seasons_path, seasons)
                                
                                logger.info(f"Cached {len(seasons)} seasons for series {series_id}")
                                
                                # Prefetch episodes for each season
                                for season in seasons:
                                    try:
                                        season_id = season.get("id")
                                        if not season_id:
                                            continue
                                            
                                        # Get episodes
                                        episodes = tryWithTokenRefresh(stb.getSeasonEpisodes, url, mac, token, proxy, series_id, season_id)
                                        
                                        # Check if the response is valid
                                        if isinstance(episodes, str) or not episodes:
                                            logger.warning(f"Skipping episodes for season {season_id}: invalid response")
                                            continue
                                            
                                        # Save episodes to cache
                                        episodes_path = get_episodes_path(portalId, series_id, season_id)
                                        save_content_json(episodes_path, episodes)
                                        
                                        logger.info(f"Cached {len(episodes)} episodes for season {season_id} of series {series_id}")
                                        
                                        # Add a small delay to avoid overwhelming the API
                                        time.sleep(0.5)
                                        
                                    except Exception as e:
                                        logger.error(f"Error prefetching episodes for season {season.get('id')} of series {series_id}: {e}")
                                        continue
                                
                                # Add a small delay to avoid overwhelming the API
                                time.sleep(0.5)
                                
                            except Exception as e:
                                logger.error(f"Error prefetching seasons for series {series.get('id')}: {e}")
                                continue
                        
                        # Add a small delay between categories
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error prefetching Series category {category.get('id')}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error prefetching Series categories: {e}")
            
            logger.info(f"Content prefetch completed for portal {portal_name} ({portalId})")
            
        except Exception as e:
            logger.error(f"Error in prefetch worker for portal {portal_name}: {e}")
    
    # Start the worker thread
    prefetch_thread = threading.Thread(target=prefetch_worker)
    prefetch_thread.daemon = True  # Allow the thread to be terminated when the main program exits
    prefetch_thread.start()
    
    return jsonify({
        "status": "success",
        "message": f"Started prefetching content for portal {portal_name} ({portalId}). This process runs in the background and may take a while to complete."
    })

@app.route("/portals/<portalId>/prefetch", methods=["GET"])
@authorise
def prefetchPortalUI(portalId):
    """
    Renders a simple UI for prefetching content for a portal.
    
    Args:
        portalId (str): ID of the portal.
        
    Returns:
        Response: Rendered HTML template.
    """
    portals = getPortals()
    if portalId not in portals:
        flash("Portal not found", "danger")
        return redirect("/portals", code=302)
        
    portal = portals[portalId]
    
    return render_template("prefetch.html", portal=portal, portalId=portalId)

#endregion

@app.route("/portal/<portalId>/channels", methods=["GET"])
@authorise
def portalChannels(portalId):
    """
    Renders the channels.html template for a specific portal.
    
    Args:
        portalId (str): ID of the portal.
        
    Returns:
        Response: Rendered HTML template with channels data.
    """
    portals = getPortals()
    if portalId not in portals:
        flash("Portal not found", "danger")
        return redirect("/portals", code=302)
    
    portal = portals[portalId]
    portal_name = portal.get("name")
    
    try:
        # Load channels from file
        channels_path = os.path.join(parent_folder, f"{portal_name}.json")
        channels = []
        if os.path.exists(channels_path):
            with open(channels_path, 'r') as file:
                channels = json.load(file)
        
        # Load genres from file
        genres_path = os.path.join(parent_folder, f"{portal_name}_genres.json")
        genres = []
        if os.path.exists(genres_path):
            with open(genres_path, 'r') as file:
                genres = json.load(file)
                
        # Get channel groups
        channel_groups = getChannelGroups()
        
        return render_template("channels.html", 
                              portal=portal, 
                              portalId=portalId, 
                              channels=channels, 
                              genres=genres,
                              channel_groups=channel_groups)
    except Exception as e:
        logger.error(f"Error loading channels for portal {portal_name}: {e}")
        flash(f"Error loading channels: {str(e)}", "danger")
        return redirect("/portals", code=302)

#endregion

#region Playlist Generation Functions

@app.route("/api/playlist/movies", methods=["POST"])
@authorise
def create_movies_playlist():
    """
    Creates an M3U playlist from selected movies.
    
    Expects JSON with:
    - portalId (str): Portal ID
    - movieIds (list): List of movie IDs to include in the playlist
    - playlistName (str): Name for the playlist
    - includeMetadata (bool): Whether to include extended metadata in the playlist
    - useDirectLinks (bool, optional): Whether to use direct stream links (default: true)
    - xuiCompatible (bool, optional): Whether to format the playlist for XUI One Panel compatibility (default: false)
    
    Returns:
        M3U playlist file for download
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing request data"}), 400
            
        portal_id = data.get("portalId")
        movie_ids = data.get("movieIds", [])
        playlist_name = data.get("playlistName", "Movies Playlist")
        include_metadata = data.get("includeMetadata", True)
        use_direct_links = data.get("useDirectLinks", True)
        xui_compatible = data.get("xuiCompatible", False)
        
        if not portal_id:
            return jsonify({"error": "Missing portal ID"}), 400
            
        if not movie_ids:
            return jsonify({"error": "No movies selected"}), 400
        
        # Get portal details
        portals = getPortals()
        if portal_id not in portals:
            return jsonify({"error": "Portal not found"}), 404
            
        portal = portals[portal_id]
        portal_name = portal.get("name", "Unknown Portal")
        url = portal["url"]
        
        # Get available MACs for the portal
        macs = list(portal["macs"].keys())
        if not macs:
            logger.error(f"No MACs available for portal {portal_id}")
            return jsonify({"error": "No MACs available for the portal"}), 400
            
        # Use the first available MAC
        mac = macs[0]
        proxy = portal.get("proxy")
        
        # Get token for the portal
        token = stb.getToken(url, mac, proxy)
        if not token:
            logger.error(f"Failed to authenticate with portal {portal_id}")
            return jsonify({"error": "Failed to authenticate with portal"}), 500
            
        # Start building the playlist
        playlist_content = "#EXTM3U\n"
        
        # Add playlist info if metadata is enabled and not XUI compatible format
        if include_metadata and not xui_compatible:
            playlist_content += f'#PLAYLIST:{playlist_name}\n'
        
        # Get all movies data
        all_movies = {}
        
        # Try to load movie details from cached VOD categories
        vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
        try:
            if os.path.exists(vod_categories_path):
                with open(vod_categories_path, 'r') as f:
                    categories = json.load(f)
                
                for category in categories:
                    if category.get("type") != "VOD":
                        continue
                        
                    category_id = category.get("id")
                    if not category_id:
                        continue
                        
                    # Get items path
                    items_path = get_vod_items_path(portal_id, category_id)
                    
                    if os.path.exists(items_path):
                        with open(items_path, 'r') as f:
                            try:
                                items = json.load(f)
                                for item in items:
                                    if isinstance(item, dict) and "id" in item:
                                        all_movies[item["id"]] = item
                            except json.JSONDecodeError:
                                logger.warning(f"Error parsing JSON from {items_path}")
        except Exception as e:
            logger.warning(f"Error loading cached movie details: {e}")
        
        # Fix image URLs for all movies by converting relative paths to absolute
        fixed_movies = {}
        for movie_id, movie in all_movies.items():
            fixed_movies[movie_id] = movie.copy()
        
        # Use the fix_screenshot_urls function to ensure all image URLs are absolute
        movie_list = list(fixed_movies.values())
        fixed_movie_list = fix_screenshot_urls(movie_list, url)
        
        # Update the fixed_movies dictionary with the fixed URLs
        for i, movie in enumerate(fixed_movie_list):
            if movie.get("id") in fixed_movies:
                fixed_movies[movie.get("id")] = movie
        
        # Get server address for app URLs if not using direct links
        server_address = request.host_url.rstrip('/')
        logger.info(f"Server address for playlist: {server_address}")
        
        # Add each movie to the playlist
        for movie_id in movie_ids:
            try:
                if use_direct_links:
                    # Get direct stream URL (this replaces the internal app URL)
                    stream_link = stb.getVodSeriesLink(url, mac, token, movie_id, "vod", proxy=proxy)
                    if not stream_link:
                        logger.warning(f"Failed to get direct stream link for movie {movie_id} - skipping")
                        continue
                else:
                    # Use application URL with from_playlist parameter
                    stream_link = f"{server_address}/play/vod/{portal_id}/{movie_id}?from_playlist=true"
                
                # Get movie details if available
                movie = fixed_movies.get(movie_id, {})
                movie_name = movie.get("name", movie.get("o_name", f"Movie {movie_id}"))
                
                # Add extended info
                if xui_compatible:
                    # XUI One Panel compatible format
                    # Format: #EXTINF:-1 tvg-id="MovieName.movie" tvg-logo="http://example.com/logo.jpg" group-title="Playlist Name",Movie Name
                    
                    # Create a safe tvg-id (alphanumeric and dots only)
                    tvg_id = f"{movie_name.replace(' ', '')}.movie"
                    tvg_id = ''.join(c for c in tvg_id if c.isalnum() or c == '.')
                    
                    # Get logo URL
                    logo = movie.get("screenshot_uri", movie.get("poster_path", movie.get("cover_big", "")))
                    logo_attr = f' tvg-logo="{logo}"' if logo else ""
                    
                    # Add all metadata as attributes in the EXTINF line
                    playlist_content += f'#EXTINF:-1 tvg-id="{tvg_id}"{logo_attr} group-title="{playlist_name}",{movie_name}\n'
                    
                elif include_metadata:
                    # Traditional extended M3U format with separate tags
                    duration = movie.get("duration", -1)
                    if duration and not isinstance(duration, int):
                        try:
                            duration = int(duration)
                        except (ValueError, TypeError):
                            duration = -1
                            
                    # Use default -1 for unknown duration
                    playlist_content += f'#EXTINF:{duration},{movie_name}\n'
                    
                    # Add logo if available - ensure it has absolute URL
                    logo = movie.get("screenshot_uri", movie.get("poster_path", movie.get("cover_big", "")))
                    if logo:
                        # Logo should already be fixed by fix_screenshot_urls
                        playlist_content += f'#EXTLOGO:{logo}\n'
                        
                    # Add genre if available
                    genre = movie.get("genre", "")
                    if genre:
                        playlist_content += f'#EXTGENRE:{genre}\n'
                        
                    # Add description if available
                    description = movie.get("description", movie.get("plot", ""))
                    if description:
                        # Limit description length
                        if len(description) > 500:
                            description = description[:497] + "..."
                        playlist_content += f'#EXTDESCRIPTION:{description}\n'
                else:
                    # Simple format without extended metadata
                    playlist_content += f'#EXTINF:-1,{movie_name}\n'
                
                # Add the stream URL
                playlist_content += f'{stream_link}\n'
            except Exception as e:
                logger.warning(f"Error processing movie {movie_id}: {str(e)}")
                continue
        
        # Create response
        response = make_response(playlist_content)
        response.headers["Content-Type"] = "audio/x-mpegurl" 
        response.headers["Content-Disposition"] = f'attachment; filename="{playlist_name.replace(" ", "_")}.m3u"'
        
        return response
    except Exception as e:
        logger.error(f"Error creating movie playlist: {e}")
        return jsonify({"error": f"Error creating playlist: {str(e)}"}), 500

@app.route("/api/playlist/series", methods=["POST"])
@authorise
def create_series_playlist():
    """
    Creates an M3U playlist from selected series episodes.
    
    Expects JSON with:
    - portalId (str): Portal ID
    - seriesIds (list): List of series IDs to include
    - playlistName (str): Name for the playlist
    - includeMetadata (bool): Whether to include extended metadata in the playlist
    - includeEpisodes (bool, optional): Whether to include individual episodes (default: False)
    - useDirectLinks (bool, optional): Whether to use direct stream links (default: true)
    - xuiCompatible (bool, optional): Whether to format the playlist for XUI One Panel compatibility (default: false)
    
    Returns:
        M3U playlist file for download
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing request data"}), 400
            
        portal_id = data.get("portalId")
        series_ids = data.get("seriesIds", [])
        playlist_name = data.get("playlistName", "Series Playlist")
        include_metadata = data.get("includeMetadata", True)
        include_episodes = data.get("includeEpisodes", False)
        use_direct_links = data.get("useDirectLinks", True)
        xui_compatible = data.get("xuiCompatible", False)
        
        if not portal_id:
            return jsonify({"error": "Missing portal ID"}), 400
            
        if not series_ids:
            return jsonify({"error": "No series selected"}), 400
        
        # Get portal details
        portals = getPortals()
        if portal_id not in portals:
            return jsonify({"error": "Portal not found"}), 404
        
        portal = portals[portal_id]
        portal_name = portal.get("name", "Unknown Portal")
        url = portal["url"]
        
        # Get available MACs for the portal
        macs = list(portal["macs"].keys())
        if not macs:
            logger.error(f"No MACs available for portal {portal_id}")
            return jsonify({"error": "No MACs available for the portal"}), 400
            
        # Use the first available MAC
        mac = macs[0]
        proxy = portal.get("proxy")
        
        # Get token for the portal
        token = stb.getToken(url, mac, proxy)
        if not token:
            logger.error(f"Failed to authenticate with portal {portal_id}")
            return jsonify({"error": "Failed to authenticate with portal"}), 500
            
        # Start building the playlist
        playlist_content = "#EXTM3U\n"
        
        # Add playlist info if metadata is enabled and not XUI compatible format
        if include_metadata and not xui_compatible:
            playlist_content += f'#PLAYLIST:{playlist_name}\n'
            
        # Get server address for app URLs if not using direct links
        server_address = request.host_url.rstrip('/')
        logger.info(f"Server address for playlist: {server_address}")
        
        # Get all series data
        all_series = {}
        
        # Try to load series details from cached Series categories
        series_categories_path = os.path.join(parent_folder, f"{portal_name}_series_categories.json")
        
        try:
            # First try series-specific categories
            if os.path.exists(series_categories_path):
                with open(series_categories_path, 'r') as f:
                    categories = json.load(f)
            else:
                # Fall back to VOD categories with Series type
                vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
                if os.path.exists(vod_categories_path):
                    with open(vod_categories_path, 'r') as f:
                        all_categories = json.load(f)
                        categories = [c for c in all_categories if c.get("type") == "Series"]
                else:
                    categories = []
                
            # Process categories
            for category in categories:
                category_id = category.get("id")
                if not category_id:
                    continue
                    
                # Get items path
                items_path = get_series_items_path(portal_id, category_id)
                
                if os.path.exists(items_path):
                    with open(items_path, 'r') as f:
                        try:
                            items = json.load(f)
                            for item in items:
                                if isinstance(item, dict) and "id" in item:
                                    all_series[item["id"]] = item
                        except json.JSONDecodeError:
                            logger.warning(f"Error parsing JSON from {items_path}")
        except Exception as e:
            logger.warning(f"Error loading cached series details: {e}")
        
        # Fix image URLs for all series by converting relative paths to absolute
        fixed_series = {}
        for series_id, series in all_series.items():
            fixed_series[series_id] = series.copy()
        
        # Use the fix_screenshot_urls function to ensure all image URLs are absolute
        series_list = list(fixed_series.values())
        fixed_series_list = fix_screenshot_urls(series_list, url)
        
        # Update the fixed_series dictionary with the fixed URLs
        for i, series in enumerate(fixed_series_list):
            if series.get("id") in fixed_series:
                fixed_series[series.get("id")] = series
        
        # Function to ensure image URL is absolute
        def ensure_absolute_url(image_url):
            if not image_url:
                return ""
                
            if not image_url.startswith(('http://', 'https://')):
                base_url = url.split('/c/')[0] if '/c/' in url else url
                base_url = base_url.rstrip('/')
                if image_url.startswith('/'):
                    return base_url + image_url
                else:
                    return base_url + '/' + image_url
            return image_url
        
        # Add each series to the playlist
        for series_id in series_ids:
            # Get series details if available
            series = fixed_series.get(series_id, {})
            series_name = series.get("name", series.get("o_name", f"Series {series_id}"))
            
            if include_episodes and include_metadata:
                # Try to load seasons
                try:
                    seasons_path = get_seasons_path(portal_id, series_id)
                    if os.path.exists(seasons_path):
                        with open(seasons_path, 'r') as f:
                            seasons = json.load(f)
                            
                            # Fix season image URLs
                            seasons = fix_screenshot_urls(seasons, url)
                            
                            # Add each season and episode
                            for season in seasons:
                                season_id = season.get("id")
                                season_name = season.get("name", f"Season {season.get('season_number', '?')}")
                                
                                # Add season header as a comment (if not XUI compatible)
                                if not xui_compatible:
                                    playlist_content += f'#EXTGRP:{series_name} - {season_name}\n'
                                
                                # Get episodes
                                episodes_path = get_episodes_path(portal_id, series_id, season_id)
                                if os.path.exists(episodes_path):
                                    with open(episodes_path, 'r') as f:
                                        episodes = json.load(f)
                                        
                                        # Fix episode image URLs
                                        episodes = fix_screenshot_urls(episodes, url)
                                        
                                        # Add each episode
                                        for episode in episodes:
                                            episode_id = episode.get("id")
                                            if not episode_id:
                                                continue
                                            
                                            try:
                                                if use_direct_links:
                                                    # Get direct stream link for episode
                                                    stream_link = stb.getVodSeriesLink(url, mac, token, episode_id, "episode", series_info, proxy=proxy)
                                                    if not stream_link:
                                                        logger.warning(f"Failed to get direct stream link for episode {episode_id} - skipping")
                                                        continue
                                                else:
                                                    # Use application URL with from_playlist parameter
                                                    stream_link = f"{server_address}/play/series/{portal_id}/{series_id}/{season_id}/{episode_id}?from_playlist=true"
                                                    
                                                episode_name = episode.get("name", episode.get("title", ""))
                                                episode_number = episode.get("episode_number", "?")
                                                full_name = f"{series_name} - S{season.get('season_number', '?')}E{episode_number}: {episode_name}"
                                                
                                                if xui_compatible:
                                                    # Create a safe tvg-id
                                                    tvg_id = f"{series_name.replace(' ', '')}.S{season.get('season_number', '0')}E{episode_number}"
                                                    tvg_id = ''.join(c for c in tvg_id if c.isalnum() or c == '.')
                                                    
                                                    # Get logo URL
                                                    logo = episode.get("screenshot_uri", episode.get("poster_path", ""))
                                                    logo_attr = f' tvg-logo="{logo}"' if logo else ""
                                                    
                                                    # Add all metadata as attributes in the EXTINF line
                                                    playlist_content += f'#EXTINF:-1 tvg-id="{tvg_id}"{logo_attr} group-title="{playlist_name}",{full_name}\n'
                                                else:
                                                    # Traditional extended M3U format
                                                    # Add extended info
                                                    duration = episode.get("duration", -1)
                                                    if duration and not isinstance(duration, int):
                                                        try:
                                                            duration = int(duration)
                                                        except (ValueError, TypeError):
                                                            duration = -1
                                                    
                                                    playlist_content += f'#EXTINF:{duration},{full_name}\n'
                                                    
                                                    # Add logo if available
                                                    logo = episode.get("screenshot_uri", episode.get("poster_path", ""))
                                                    if logo:
                                                        # Logo should already be fixed by fix_screenshot_urls
                                                        playlist_content += f'#EXTLOGO:{logo}\n'
                                                        
                                                    # Add description if available
                                                    description = episode.get("description", episode.get("plot", ""))
                                                    if description:
                                                        # Limit description length
                                                        if len(description) > 500:
                                                            description = description[:497] + "..."
                                                        playlist_content += f'#EXTDESCRIPTION:{description}\n'
                                                
                                                # Add the stream URL
                                                playlist_content += f'{stream_link}\n'
                                            except Exception as e:
                                                logger.warning(f"Error processing episode {episode_id}: {str(e)}")
                                                continue
                except Exception as e:
                    logger.warning(f"Error including episodes for series {series_id}: {e}")
                    try:
                        # Fall back to series-only link if episodes fail
                        if use_direct_links:
                            # Get direct stream link for series
                            stream_link = stb.getVodSeriesLink(url, mac, token, series_id, "series", proxy=proxy)
                            if not stream_link:
                                logger.warning(f"Failed to get direct stream link for series {series_id} - skipping")
                                continue
                        else:
                            # Use application URL with from_playlist parameter
                            stream_link = f"{server_address}/play/series/{portal_id}/{series_id}?from_playlist=true"
                        
                        if xui_compatible:
                            # Create a safe tvg-id
                            tvg_id = f"{series_name.replace(' ', '')}.series"
                            tvg_id = ''.join(c for c in tvg_id if c.isalnum() or c == '.')
                            
                            # Get logo URL
                            logo = series.get("screenshot_uri", series.get("poster_path", series.get("cover_big", "")))
                            logo_attr = f' tvg-logo="{logo}"' if logo else ""
                            
                            # Add all metadata as attributes in the EXTINF line
                            playlist_content += f'#EXTINF:-1 tvg-id="{tvg_id}"{logo_attr} group-title="{playlist_name}",{series_name}\n'
                        else:
                            # Traditional extended M3U format
                            # Add extended info
                            playlist_content += f'#EXTINF:-1,{series_name}\n'
                            
                            # Add logo if available - already fixed in fixed_series
                            logo = series.get("screenshot_uri", series.get("poster_path", series.get("cover_big", "")))
                            if logo:
                                playlist_content += f'#EXTLOGO:{logo}\n'
                                
                            # Add description if available
                            description = series.get("description", series.get("plot", ""))
                            if description:
                                # Limit description length
                                if len(description) > 500:
                                    description = description[:497] + "..."
                                playlist_content += f'#EXTDESCRIPTION:{description}\n'
                        
                        # Add the stream URL
                        playlist_content += f'{stream_link}\n'
                    except Exception as e:
                        logger.warning(f"Error processing series {series_id}: {str(e)}")
                        continue
            else:
                try:
                    # Just add the series link
                    if use_direct_links:
                        # Get direct stream link for series
                        stream_link = stb.getVodSeriesLink(url, mac, token, series_id, "series", proxy=proxy)
                        if not stream_link:
                            logger.warning(f"Failed to get direct stream link for series {series_id} - skipping")
                            continue
                    else:
                        # Use application URL with from_playlist parameter
                        stream_link = f"{server_address}/play/series/{portal_id}/{series_id}?from_playlist=true"
                    
                    # XUI compatible format
                    if xui_compatible:
                        # Create a safe tvg-id
                        tvg_id = f"{series_name.replace(' ', '')}.series"
                        tvg_id = ''.join(c for c in tvg_id if c.isalnum() or c == '.')
                        
                        # Get logo URL
                        logo = series.get("screenshot_uri", series.get("poster_path", series.get("cover_big", "")))
                        logo_attr = f' tvg-logo="{logo}"' if logo else ""
                        
                        # Add all metadata as attributes in the EXTINF line
                        playlist_content += f'#EXTINF:-1 tvg-id="{tvg_id}"{logo_attr} group-title="{playlist_name}",{series_name}\n'
                    # Add extended info if metadata is enabled
                    elif include_metadata:
                        playlist_content += f'#EXTINF:-1,{series_name}\n'
                        
                        # Add logo if available - already fixed in fixed_series
                        logo = series.get("screenshot_uri", series.get("poster_path", series.get("cover_big", "")))
                        if logo:
                            playlist_content += f'#EXTLOGO:{logo}\n'
                            
                        # Add genre if available
                        genre = series.get("genre", "")
                        if genre:
                            playlist_content += f'#EXTGENRE:{genre}\n'
                            
                        # Add description if available
                        description = series.get("description", series.get("plot", ""))
                        if description:
                            # Limit description length
                            if len(description) > 500:
                                description = description[:497] + "..."
                            playlist_content += f'#EXTDESCRIPTION:{description}\n'
                    else:
                        # Simple format without extended metadata
                        playlist_content += f'#EXTINF:-1,{series_name}\n'
                    
                    # Add the stream URL
                    playlist_content += f'{stream_link}\n'
                except Exception as e:
                    logger.warning(f"Error processing series {series_id}: {str(e)}")
                    continue
        
        # Create response
        response = make_response(playlist_content)
        response.headers["Content-Type"] = "audio/x-mpegurl"
        response.headers["Content-Disposition"] = f'attachment; filename="{playlist_name.replace(" ", "_")}.m3u"'
        
        return response
    except Exception as e:
        logger.error(f"Error creating series playlist: {e}")
        return jsonify({"error": f"Error creating playlist: {str(e)}"}), 500

#endregion

#region Content Playback Routes

@app.route("/play/vod/<portalId>/<movieId>", methods=["GET"])
def play_vod(portalId, movieId):
    """
    Stream a VOD item from the specified portal.
    
    Args:
        portalId (str): ID of the portal
        movieId (str): ID of the movie to stream
        
    Returns:
        Response: Stream response or error
    """
    from_playlist = request.args.get('from_playlist', 'false').lower() == 'true'
    is_web_view = not from_playlist
    
    logger.info(f"Request to play VOD: portalId={portalId}, movieId={movieId}")
    logger.info(f"Web view requested: {is_web_view}, from playlist: {from_playlist}")
    
    # Get portal details
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404
    
    portal = portals[portalId]
    portal_name = portal.get("name", "Unknown Portal")
    url = portal["url"]
    
    logger.info(f"Portal found: {portal_name} with URL: {url}")
    
    # Get available MACs for the portal
    macs = list(portal["macs"].keys())
    if not macs:
        logger.error(f"No MACs available for portal {portalId}")
        return jsonify({"error": "No MACs available for the portal"}), 400
        
    # Use the first available MAC
    mac = macs[0]
    proxy = portal.get("proxy")
    
    logger.info(f"Using MAC: {mac} and proxy: {proxy}")
    
    # Full authentication process
    # Step 1: Get token
    token = stb.getToken(url, mac, proxy)
    if not token:
        logger.error(f"Failed to get token for portal {portalId}")
        if from_playlist:
            return jsonify({"error": "Authentication failed - could not get token"}), 401
        return render_template("error.html", error="Failed to authenticate with portal - could not get token.")
    
    logger.info(f"Successfully obtained token for portal {portalId}")
    
    # Step 2: Full authentication with profile (needed for VOD content)
    try:
        # Generate device IDs
        device_id = stb.generate_device_id(mac)
        device_id2 = device_id
        
        # Generate timestamp and signature
        import time
        timestamp = int(time.time())
        signature = stb.generate_signature(mac, token, [str(timestamp)])
        
        # Get profile to complete authentication
        logger.info(f"Getting profile to complete authentication")
        profile = stb.getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy)
        
        if not profile:
            logger.warning(f"Failed to get profile, but will try to get stream link anyway")
    except Exception as e:
        logger.warning(f"Error in profile authentication: {str(e)}")
    
    # Try to get stream link
    try:
        logger.info(f"Attempting to get stream link for movie {movieId}")
        stream_link = stb.getVodSeriesLink(url, mac, token, movieId, "vod", proxy=proxy)
        
        if not stream_link:
            logger.error(f"Failed to get stream link for movie {movieId}")
            if from_playlist:
                return jsonify({"error": "Failed to get stream link"}), 404
            return render_template("error.html", error="Failed to get stream link for the movie.")
            
        # Handle stream links that require authentication
        if isinstance(stream_link, dict) and "auth" in stream_link:
            logger.info("Stream requires authentication, sending headers and cookies")
            
            if from_playlist:
                # For playlists, return headers and cookies for direct stream access
                headers = stream_link.get('auth', {}).get('headers', {})
                cookies = stream_link.get('auth', {}).get('cookies', {})
                direct_url = stream_link.get('url', '')
                
                return jsonify({
                    "direct_url": direct_url,
                    "headers": headers,
                    "cookies": cookies
                })
            else:
                # For web view, we'll use our player to handle auth
                return render_template(
                    "player.html", 
                    stream_url=stream_link.get('url', ''),
                    stream_headers=json.dumps(stream_link.get('auth', {}).get('headers', {})),
                    stream_cookies=json.dumps(stream_link.get('auth', {}).get('cookies', {})),
                    title=f"VOD: {movieId}"
                )
        
        # Regular direct stream URL
        logger.info(f"Stream link found: {stream_link[:100] if isinstance(stream_link, str) else 'Unknown type'}...")
        
        if from_playlist:
            # For playlists, return direct URL
            return jsonify({"direct_url": stream_link})
        else:
            # For web view, check if we should use player or redirect
            if request.args.get('player', 'false').lower() == 'true':
                return render_template("player.html", stream_url=stream_link, title=f"VOD: {movieId}")
            else:
                return redirect(stream_link)
    
    except Exception as e:
        logger.error(f"Error playing VOD item: {str(e)}")
        if from_playlist:
            return jsonify({"error": str(e)}), 500
        return render_template("error.html", error=f"Error playing movie: {str(e)}")
        
@app.route("/play/series/<portalId>/<seriesId>", methods=["GET"])
def play_series(portalId, seriesId):
    """
    Stream a Series from the specified portal.
    
    Args:
        portalId (str): ID of the portal
        seriesId (str): ID of the series to stream
        
    Returns:
        Response: Stream response or error
    """
    from_playlist = request.args.get('from_playlist', 'false').lower() == 'true'
    is_web_view = not from_playlist
    
    logger.info(f"Request to play series: portalId={portalId}, seriesId={seriesId}")
    logger.info(f"Web view requested: {is_web_view}, from playlist: {from_playlist}")
    
    # Get portal details
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404
    
    portal = portals[portalId]
    portal_name = portal.get("name", "Unknown Portal")
    url = portal["url"]
    
    logger.info(f"Portal found: {portal_name} with URL: {url}")
    
    # Get available MACs for the portal
    macs = list(portal["macs"].keys())
    if not macs:
        logger.error(f"No MACs available for portal {portalId}")
        return jsonify({"error": "No MACs available for the portal"}), 400
        
    # Use the first available MAC
    mac = macs[0]
    proxy = portal.get("proxy")
    
    logger.info(f"Using MAC: {mac} and proxy: {proxy}")
    
    # Full authentication process
    # Step 1: Get token
    token = stb.getToken(url, mac, proxy)
    if not token:
        logger.error(f"Failed to get token for portal {portalId}")
        if from_playlist:
            return jsonify({"error": "Authentication failed - could not get token"}), 401
        return render_template("error.html", error="Failed to authenticate with portal - could not get token.")
    
    logger.info(f"Successfully obtained token for portal {portalId}")
    
    # Step 2: Full authentication with profile (needed for series content)
    try:
        # Generate device IDs
        device_id = stb.generate_device_id(mac)
        device_id2 = device_id
        
        # Generate timestamp and signature
        import time
        timestamp = int(time.time())
        signature = stb.generate_signature(mac, token, [str(timestamp)])
        
        # Get profile to complete authentication
        logger.info(f"Getting profile to complete authentication")
        profile = stb.getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy)
        
        if not profile:
            logger.warning(f"Failed to get profile, but will try to get stream link anyway")
    except Exception as e:
        logger.warning(f"Error in profile authentication: {str(e)}")
    
    # Try to get stream link
    try:
        logger.info(f"Attempting to get stream link for series {seriesId}")
        stream_link = stb.getVodSeriesLink(url, mac, token, seriesId, "series", proxy=proxy)
        
        if not stream_link:
            logger.error(f"Failed to get stream link for series {seriesId}")
            if from_playlist:
                return jsonify({"error": "Failed to get stream link"}), 404
            return render_template("error.html", error="Failed to get stream link for the series.")
            
        # Handle stream links that require authentication
        if isinstance(stream_link, dict) and "auth" in stream_link:
            logger.info("Stream requires authentication, sending headers and cookies")
            
            if from_playlist:
                # For playlists, return headers and cookies for direct stream access
                headers = stream_link.get('auth', {}).get('headers', {})
                cookies = stream_link.get('auth', {}).get('cookies', {})
                direct_url = stream_link.get('url', '')
                
                return jsonify({
                    "direct_url": direct_url,
                    "headers": headers,
                    "cookies": cookies
                })
            else:
                # For web view, we'll use our player to handle auth
                return render_template(
                    "player.html", 
                    stream_url=stream_link.get('url', ''),
                    stream_headers=json.dumps(stream_link.get('auth', {}).get('headers', {})),
                    stream_cookies=json.dumps(stream_link.get('auth', {}).get('cookies', {})),
                    title=f"Series: {seriesId}"
                )
        
        # Regular direct stream URL
        logger.info(f"Stream link found: {stream_link[:100] if isinstance(stream_link, str) else 'Unknown type'}...")
        
        if from_playlist:
            # For playlists, return direct URL
            return jsonify({"direct_url": stream_link})
        else:
            # For web view, check if we should use player or redirect
            if request.args.get('player', 'false').lower() == 'true':
                return render_template("player.html", stream_url=stream_link, title=f"Series: {seriesId}")
            else:
                return redirect(stream_link)
    
    except Exception as e:
        logger.error(f"Error playing series: {str(e)}")
        if from_playlist:
            return jsonify({"error": str(e)}), 500
        return render_template("error.html", error=f"Error playing series: {str(e)}")

@app.route("/play/series/<portalId>/<seriesId>/<seasonId>/<episodeId>", methods=["GET"])
def play_episode(portalId, seriesId, seasonId, episodeId):
    """
    Stream a Series episode from the specified portal.
    
    Args:
        portalId (str): ID of the portal
        seriesId (str): ID of the series
        seasonId (str): ID of the season
        episodeId (str): ID of the episode to stream
        
    Returns:
        Response: Stream response or error
    """
    from_playlist = request.args.get('from_playlist', 'false').lower() == 'true'
    is_web_view = not from_playlist
    
    logger.info(f"Request to play episode: portalId={portalId}, seriesId={seriesId}, seasonId={seasonId}, episodeId={episodeId}")
    logger.info(f"Web view requested: {is_web_view}, from playlist: {from_playlist}")
    
    # Get portal details
    portals = getPortals()
    if portalId not in portals:
        return jsonify({"error": "Portal not found"}), 404
    
    portal = portals[portalId]
    portal_name = portal.get("name", "Unknown Portal")
    url = portal["url"]
    
    logger.info(f"Portal found: {portal_name} with URL: {url}")
    
    # Get available MACs for the portal
    macs = list(portal["macs"].keys())
    if not macs:
        logger.error(f"No MACs available for portal {portalId}")
        return jsonify({"error": "No MACs available for the portal"}), 400
        
    # Use the first available MAC
    mac = macs[0]
    proxy = portal.get("proxy")
    
    logger.info(f"Using MAC: {mac} and proxy: {proxy}")
    
    # Full authentication process
    # Step 1: Get token
    token = stb.getToken(url, mac, proxy)
    if not token:
        logger.error(f"Failed to get token for portal {portalId}")
        if from_playlist:
            return jsonify({"error": "Authentication failed - could not get token"}), 401
        return render_template("error.html", error="Failed to authenticate with portal - could not get token.")
    
    logger.info(f"Successfully obtained token for portal {portalId}")
    
    # Step 2: Full authentication with profile (needed for episode content)
    try:
        # Generate device IDs
        device_id = stb.generate_device_id(mac)
        device_id2 = device_id
        
        # Generate timestamp and signature
        import time
        timestamp = int(time.time())
        signature = stb.generate_signature(mac, token, [str(timestamp)])
        
        # Get profile to complete authentication
        logger.info(f"Getting profile to complete authentication")
        profile = stb.getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy)
        
        if not profile:
            logger.warning(f"Failed to get profile, but will try to get stream link anyway")
    except Exception as e:
        logger.warning(f"Error in profile authentication: {str(e)}")
    
    # Try to get stream link
    try:
        # Create series info dict for episode
        series_info = {
            "series_id": seriesId,
            "season_id": seasonId,
            "episode_id": episodeId,
            "episode_number": episodeId  # Use episode ID as number if actual number is not available
        }
        
        logger.info(f"Attempting to get stream link for episode {episodeId}")
        stream_link = stb.getVodSeriesLink(url, mac, token, episodeId, "episode", series_info, proxy=proxy)
        
        if not stream_link:
            logger.error(f"Failed to get stream link for episode {episodeId}")
            if from_playlist:
                return jsonify({"error": "Failed to get stream link"}), 404
            return render_template("error.html", error="Failed to get stream link for the episode.")
            
        # Handle stream links that require authentication
        if isinstance(stream_link, dict) and "auth" in stream_link:
            logger.info("Stream requires authentication, sending headers and cookies")
            
            if from_playlist:
                # For playlists, return headers and cookies for direct stream access
                headers = stream_link.get('auth', {}).get('headers', {})
                cookies = stream_link.get('auth', {}).get('cookies', {})
                direct_url = stream_link.get('url', '')
                
                return jsonify({
                    "direct_url": direct_url,
                    "headers": headers,
                    "cookies": cookies
                })
            else:
                # For web view, we'll use our player to handle auth
                return render_template(
                    "player.html", 
                    stream_url=stream_link.get('url', ''),
                    stream_headers=json.dumps(stream_link.get('auth', {}).get('headers', {})),
                    stream_cookies=json.dumps(stream_link.get('auth', {}).get('cookies', {})),
                    title=f"Episode: {episodeId}"
                )
        
        # Regular direct stream URL
        logger.info(f"Stream link found: {stream_link[:100] if isinstance(stream_link, str) else 'Unknown type'}...")
        
        if from_playlist:
            # For playlists, return direct URL
            return jsonify({"direct_url": stream_link})
        else:
            # For web view, check if we should use player or redirect
            if request.args.get('player', 'false').lower() == 'true':
                return render_template("player.html", stream_url=stream_link, title=f"Episode: {episodeId}")
            else:
                return redirect(stream_link)
    
    except Exception as e:
        logger.error(f"Error playing episode: {str(e)}")
        if from_playlist:
            return jsonify({"error": str(e)}), 500
        return render_template("error.html", error=f"Error playing episode: {str(e)}")

#endregion

# Main application entry point
if __name__ == "__main__":
    # Load configuration at startup
    loadConfig()
    
    # Parse host and port from environment variable or use default
    host_parts = host.split(":")
    host_addr = host_parts[0] if len(host_parts) > 0 else "localhost"
    host_port = int(host_parts[1]) if len(host_parts) > 1 else 8001
    
    # Log startup information
    logger.info(f"Starting STB-ReStreamer on {host_addr}:{host_port}")
    logger.info(f"FFmpeg path: {ffmpeg_path}")
    logger.info(f"FFprobe path: {ffprobe_path}")
    logger.info(f"Config file: {configFile}")
    
    # Serve the Flask application using Waitress
    waitress.serve(app, host=host_addr, port=host_port, threads=10)

def get_cached_content(content_type, portal_id, resource_path):
    """
    Helper function to fetch content from the cache or API.
    
    Args:
        content_type (str): Type of content ('vod' or 'series')
        portal_id (str): Portal ID
        resource_path (str): Path to the resource (e.g. 'categories', 'category/123')
        
    Returns:
        Response: Flask response object with the content
    """
    try:
        portals = getPortals()
        if portal_id not in portals:
            return jsonify({"error": "Portal not found"}), 404
            
        portal = portals[portal_id]
        url = portal["url"]
        
        # Handle different resource types
        if resource_path == "categories":
            # Get categories
            if content_type == "vod":
                # Load VOD categories from file
                portal_name = portal.get("name")
                vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
                
                if os.path.exists(vod_categories_path):
                    with open(vod_categories_path, 'r') as file:
                        vod_categories = json.load(file)
                    
                    # Filter to only include VOD categories (not Series)
                    vod_categories = [category for category in vod_categories if category.get("type") == "VOD"]
                    return jsonify(vod_categories)
                else:
                    return jsonify({"error": "VOD categories not found"}), 404
            elif content_type == "series":
                # Load Series categories from file
                portal_name = portal.get("name")
                series_categories_path = os.path.join(parent_folder, f"{portal_name}_series_categories.json")
                
                if os.path.exists(series_categories_path):
                    with open(series_categories_path, 'r') as file:
                        series_categories = json.load(file)
                    
                    # Filter to only include Series categories
                    series_categories = [category for category in series_categories if category.get("type") == "Series"]
                    return jsonify(series_categories)
                else:
                    # Try to load from VOD categories file and filter
                    vod_categories_path = os.path.join(parent_folder, f"{portal_name}_vod_categories.json")
                    if os.path.exists(vod_categories_path):
                        with open(vod_categories_path, 'r') as file:
                            vod_categories = json.load(file)
                        
                        # Filter to only include Series categories
                        series_categories = [category for category in vod_categories if category.get("type") == "Series"]
                        return jsonify(series_categories)
                    else:
                        return jsonify({"error": "Series categories not found"}), 404
            else:
                return jsonify({"error": f"Invalid content type: {content_type}"}), 400
        elif resource_path.startswith("category/"):
            # Get items for a category
            category_id = resource_path.split("/")[1]
            
            if content_type == "vod":
                # Get VOD items for the category
                vod_items_path = get_vod_items_path(portal_id, category_id)
                
                if os.path.exists(vod_items_path):
                    # Load from cache
                    items = load_json_content(vod_items_path)
                    if items:
                        # Fix any relative screenshot URLs
                        items = fix_screenshot_urls(items, url)
                        return jsonify(items)
                    
                # Try to fetch from API if not in cache or empty
                try:
                    macs = list(portal["macs"].keys())
                    if not macs:
                        return jsonify({"error": "No MACs available"}), 400
                    
                    mac = macs[0]
                    proxy = portal["proxy"]
                    
                    # Get token
                    token = stb.getToken(url, mac, proxy)
                    if not token:
                        return jsonify({"error": "Failed to authenticate with portal"}), 500
                    
                    # Get items
                    items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", category_id)
                    
                    # Check if valid response
                    if isinstance(items, str) or not items:
                        return jsonify([])
                    
                    # Fix any relative screenshot URLs
                    items = fix_screenshot_urls(items, url)
                    
                    # Save to cache
                    save_content_json(vod_items_path, items)
                    
                    return jsonify(items)
                except Exception as e:
                    logger.error(f"Error fetching VOD items for category {category_id}: {e}")
                    return jsonify({"error": f"Error fetching VOD items: {str(e)}"}), 500
            elif content_type == "series":
                # Get Series items for the category
                series_items_path = get_series_items_path(portal_id, category_id)
                
                if os.path.exists(series_items_path):
                    # Load from cache
                    items = load_json_content(series_items_path)
                    if items:
                        # Fix any relative screenshot URLs
                        items = fix_screenshot_urls(items, url)
                        return jsonify(items)
                
                # Handle special "No Series Found" category
                if category_id == "0":
                    return jsonify([{
                        "id": "0",
                        "title": "No Series Found",
                        "type": "Series"
                    }])
                
                # Try to fetch from API if not in cache or empty
                try:
                    macs = list(portal["macs"].keys())
                    if not macs:
                        return jsonify({"error": "No MACs available"}), 400
                    
                    mac = macs[0]
                    proxy = portal["proxy"]
                    
                    # Get token
                    token = stb.getToken(url, mac, proxy)
                    if not token:
                        return jsonify({"error": "Failed to authenticate with portal"}), 500
                    
                    # First try with series type
                    try:
                        items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "series", category_id)
                        
                        # Ensure items is a list and not a string
                        if isinstance(items, str):
                            raise Exception("API returned string, trying VOD type instead")
                        
                        if not isinstance(items, list):
                            if items is None:
                                items = []
                            else:
                                # Convert to list if possible
                                try:
                                    items = list(items)
                                except:
                                    items = [items] if items else []
                    except:
                        # Try with VOD type instead
                        items = tryWithTokenRefresh(stb.getOrderedList, url, mac, token, proxy, "vod", category_id)
                        
                        # Ensure items is a list and not a string
                        if isinstance(items, str) or not items:
                            return jsonify([])
                        
                        if not isinstance(items, list):
                            if items is None:
                                items = []
                            else:
                                # Convert to list if possible
                                try:
                                    items = list(items)
                                except:
                                    items = [items] if items else []
                    
                    # Filter to only include Series items
                    filtered_items = []
                    for item in items:
                        if isinstance(item, dict) and (
                            item.get("item_type") == "Series" or 
                            item.get("type") == "Series"
                        ):
                            filtered_items.append(item)
                    
                    items = filtered_items
                    
                    # Fix any relative screenshot URLs
                    items = fix_screenshot_urls(items, url)
                    
                    # Save to cache
                    save_content_json(series_items_path, items)
                    
                    return jsonify(items)
                except Exception as e:
                    logger.error(f"Error fetching Series items for category {category_id}: {e}")
                    return jsonify({"error": f"Error fetching Series items: {str(e)}"}), 500
            else:
                return jsonify({"error": f"Invalid content type: {content_type}"}), 400
        elif resource_path.startswith("seasons/"):
            # Get seasons for a series
            series_id = resource_path.split("/")[1]
            
            if content_type != "series":
                return jsonify({"error": f"Invalid content type for seasons: {content_type}"}), 400
            
            # Get seasons from cache or API
            seasons_path = get_seasons_path(portal_id, series_id)
            
            if os.path.exists(seasons_path):
                # Load from cache
                seasons = load_json_content(seasons_path)
                if seasons:
                    # Fix any relative screenshot URLs
                    seasons = fix_screenshot_urls(seasons, url)
                    return jsonify(seasons)
            
            # Try to fetch from API if not in cache or empty
            try:
                macs = list(portal["macs"].keys())
                if not macs:
                    return jsonify({"error": "No MACs available"}), 400
                
                mac = macs[0]
                proxy = portal["proxy"]
                
                # Get token
                token = stb.getToken(url, mac, proxy)
                if not token:
                    return jsonify({"error": "Failed to authenticate with portal"}), 500
                
                # Get seasons
                seasons = tryWithTokenRefresh(stb.getSeriesSeasons, url, mac, token, proxy, series_id)
                
                # Check if valid response
                if isinstance(seasons, str) or not seasons:
                    return jsonify([])
                
                # Fix any relative screenshot URLs
                seasons = fix_screenshot_urls(seasons, url)
                
                # Save to cache
                save_content_json(seasons_path, seasons)
                
                return jsonify(seasons)
            except Exception as e:
                logger.error(f"Error fetching seasons for series {series_id}: {e}")
                return jsonify({"error": f"Error fetching seasons: {str(e)}"}), 500
        elif resource_path.startswith("episodes/"):
            # Get episodes for a season
            parts = resource_path.split("/")
            if len(parts) < 3:
                return jsonify({"error": "Invalid resource path"}), 400
                
            series_id = parts[1]
            season_id = parts[2]
            
            if content_type != "series":
                return jsonify({"error": f"Invalid content type for episodes: {content_type}"}), 400
            
            # Get episodes from cache or API
            episodes_path = get_episodes_path(portal_id, series_id, season_id)
            
            if os.path.exists(episodes_path):
                # Load from cache
                episodes = load_json_content(episodes_path)
                if episodes:
                    # Fix any relative screenshot URLs
                    episodes = fix_screenshot_urls(episodes, url)
                    return jsonify(episodes)
            
            # Try to fetch from API if not in cache or empty
            try:
                macs = list(portal["macs"].keys())
                if not macs:
                    return jsonify({"error": "No MACs available"}), 400
                
                mac = macs[0]
                proxy = portal["proxy"]
                
                # Get token
                token = stb.getToken(url, mac, proxy)
                if not token:
                    return jsonify({"error": "Failed to authenticate with portal"}), 500
                
                # Get episodes
                episodes = tryWithTokenRefresh(stb.getSeasonEpisodes, url, mac, token, proxy, series_id, season_id)
                
                # Check if valid response
                if isinstance(episodes, str) or not episodes:
                    return jsonify([])
                
                # Fix any relative screenshot URLs
                episodes = fix_screenshot_urls(episodes, url)
                
                # Save to cache
                save_content_json(episodes_path, episodes)
                
                return jsonify(episodes)
            except Exception as e:
                logger.error(f"Error fetching episodes for series {series_id}, season {season_id}: {e}")
                return jsonify({"error": f"Error fetching episodes: {str(e)}"}), 500
        else:
            return jsonify({"error": f"Invalid resource path: {resource_path}"}), 400
    except Exception as e:
        logger.error(f"Error fetching cached content: {e}")
        return jsonify({"error": f"Error fetching content: {str(e)}"}), 500
>>>>>>> Stashed changes
