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

<<<<<<< HEAD
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
=======
class LinkCache:
    def __init__(self, max_size=1000, default_ttl=8):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock()

    def get(self, key):
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
        with self.lock:
            if key in self.cache:
                data = self.cache[key]
                if time.time() - data['timestamp'] < self.default_ttl:
<<<<<<< HEAD
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

=======
                    # Move to end to mark as recently used
                    self.cache.move_to_end(key)
                    return data['link'], data.get('ffmpegcmd')
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None, None

    def set(self, key, link, ffmpegcmd=None):
        with self.lock:
            # Remove oldest items if cache is full
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
            self.cache[key] = {
                'link': link,
                'ffmpegcmd': ffmpegcmd,
                'timestamp': time.time()
            }
<<<<<<< HEAD
            self.cache.move_to_end(key) # Move to end to mark as recently used (LRU)

    def cleanup(self):
        """
        Removes expired entries from the cache.
        """
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items()
=======
            # Move to end to mark as recently used
            self.cache.move_to_end(key)

    def cleanup(self):
        """Remove expired entries"""
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items() 
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
                      if now - v['timestamp'] > self.default_ttl]
            for k in expired:
                del self.cache[k]

<<<<<<< HEAD

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

=======
class RateLimiter:
    def __init__(self, default_limit=30, cleanup_interval=300):
        self.cooldowns = {}  # {key: {'timestamp': time, 'count': n}}
        self.default_limit = default_limit
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self.lock = Lock()

    def check_rate(self, key, duration=None):
        """Check if key is rate limited. Returns (can_access, remaining_time)"""
        if duration is None:
            duration = self.default_limit
            
        with self.lock:
            self._cleanup_if_needed()
            
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
            now = time.time()
            if key in self.cooldowns:
                last_access = self.cooldowns[key]['timestamp']
                time_elapsed = now - last_access
                if time_elapsed < duration:
<<<<<<< HEAD
                    return False, duration - time_elapsed # Rate limited, return remaining time
            return True, 0 # Not rate limited, access allowed

    def update_rate(self, key):
        """
        Updates the rate limit timestamp for a key, effectively starting or resetting the cooldown.

        Args:
            key (str): The key to update (e.g., portalId:channelId).
        """
=======
                    return False, duration - time_elapsed
            return True, 0

    def update_rate(self, key):
        """Update rate limit for key"""
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
        with self.lock:
            now = time.time()
            self.cooldowns[key] = {
                'timestamp': now,
                'count': self.cooldowns.get(key, {}).get('count', 0) + 1
            }

    def _cleanup_if_needed(self):
<<<<<<< HEAD
        """
        Cleans up expired cooldown entries if the cleanup interval has passed.
        """
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            expired = [k for k, v in self.cooldowns.items()
=======
        """Remove expired entries if cleanup interval has passed"""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            expired = [k for k, v in self.cooldowns.items() 
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
                      if now - v['timestamp'] > self.default_limit]
            for k in expired:
                del self.cooldowns[k]
            self.last_cleanup = now

<<<<<<< HEAD
# Initialize caching and rate limiting instances
link_cache = LinkCache(max_size=1000, default_ttl=8)
rate_limiter = RateLimiter(default_limit=30, cleanup_interval=300)

#endregion

#region Flask Application Setup
=======
# Initialize improved caching and rate limiting
link_cache = LinkCache(max_size=1000, default_ttl=8)
rate_limiter = RateLimiter(default_limit=30, cleanup_interval=300)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

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

def savePortalData(name, allChannels, allGenre):
    """
    Saves portal channel and genre data to JSON files.

    Args:
        name (str): Portal name (used for file naming).
        allChannels (list): List of channel dictionaries.
        allGenre (dict): Dictionary of genre IDs to genre names.
    """
    save_json(os.path.join(parent_folder, f"{name}.json"), allChannels, f"Channels '{name}.json' saved")
    save_json(os.path.join(parent_folder, f"{name}_genre.json"), allGenre, f"Genres '{name}_genre.json' saved")

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
                    allChannels = stb.getAllChannels(url, mac, token, proxy) # Get all channels for the first successful MAC
                    allGenre = stb.getGenreNames(url, mac, token, proxy) # Get genre names
                    savePortalData(name, allChannels, allGenre) # Save channel and genre data to files
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

    for mac in newmacs:
        if retest or mac not in oldmacs.keys(): # Retest MAC if requested or if it's a new MAC
            token = stb.getToken(url, mac, proxy) # Get token for MAC
            if token:
                ids = portals[id]["ids"][mac] # Get stored device IDs and signature for MAC
                stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy) # Get profile (primarily to keep session alive)
                expiry = stb.getExpires(url, mac, token, proxy) # Get expiry date
                if expiry:
                    macsout[mac] = expiry # Store MAC and expiry
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

@app.route("/editor", methods=["GET"])
@authorise
def editor():
    """
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

<<<<<<< HEAD
    playlist_output = "#EXTM3U\n" + "\n".join(playlist_entries) # Combine group playlist entries into M3U format
    return Response(playlist_output, mimetype="text/plain") # Return group playlist as plain text M3U

#endregion

#region Route Handlers - Stream Playback

=======
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
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

<<<<<<< HEAD
        Returns:
            bool: True if MAC is free or streams per mac is 0, False otherwise.
        """
        return sum(1 for i in occupied.get(portalId, []) if i["mac"] == mac) < streamsPerMac # Count occupied streams for MAC and compare to limit

    # Get portal and channel information
=======
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
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
<<<<<<< HEAD
    if cached_link: # If link found in cache
        if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
            if cached_ffmpegcmd:
                ffmpegcmd = cached_ffmpegcmd # Use cached ffmpeg command
                return Response(streamData(), mimetype="application/octet-stream") # Return stream using cached ffmpeg command
        else:
            return redirect(cached_link, code=302) # Redirect to cached link if not using ffmpeg stream method
=======
    if cached_link:
        if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
            if cached_ffmpegcmd:
                ffmpegcmd = cached_ffmpegcmd
                return Response(streamData(), mimetype="application/octet-stream")
        else:
            return redirect(cached_link, code=302)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

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
<<<<<<< HEAD

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
=======
                
                # Check cache for fallback first
                fallback_key = f"{fallback_portal_id}:{fallback_channel_id}"
                cached_link, _ = link_cache.get(fallback_key)
                if cached_link:
                    return redirect(f"/play/{fallback_portal_id}/{fallback_channel_id}", code=302)
                
                # Skip if it's the same channel or if the fallback is also rate limited
                can_access_fallback, _ = rate_limiter.check_rate(fallback_key)
                if (fallback_channel_id == channelId and fallback_portal_id == portalId) or not can_access_fallback:
                    continue

                return redirect(f"/play/{fallback_portal_id}/{fallback_channel_id}", code=302)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

        # If no fallback found, return error
        return make_response(f"Channel in cooldown. Please wait {remaining_time:.1f} seconds.", 429) # Return 429 error if rate limited and no fallback

    freeMac = False # Flag to indicate if a free MAC was found

    for mac in macs:
        channels = None
        cmd = None
        link = None
<<<<<<< HEAD
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
=======
        if streamsPerMac == 0 or isMacFree():
            logger.info(f"Trying Portal({portalId}):MAC({mac}):Channel({channelId})")
            freeMac = True
            
            # Check link cache first
            cached_link, cached_ffmpegcmd = link_cache.get(f"{portalId}:{channelId}")
            if cached_link:
                link = cached_link
                if cached_ffmpegcmd:
                    ffmpegcmd = cached_ffmpegcmd
            else:
                # Get fresh link if not cached
                token = stb.getToken(url, mac, proxy)
                if token:
                    name_path = os.path.join(parent_folder, f"{portalName}.json")
                    with open(name_path, 'r') as file:
                        channels = json.load(file)

                if channels:
                    for c in channels:
                        if str(c["id"]) == channelId:
                            channelName = portal.get("custom channel names", {}).get(channelId, c["name"])
                            cmd = c["cmd"]
                            break

                if cmd:
                    ids = portal["ids"][mac]
                    stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy)
                    if "http://localhost/" in cmd or "http:///ch/" in cmd:
                        link = stb.getLink(url, mac, token, cmd, proxy)
                    else:
                        # Handle direct link commands more safely
                        parts = cmd.split(" ")
                        link = parts[1] if len(parts) > 1 else cmd

        if link:
            if getSettings().get("test streams", "true") == "false" or testStream():
                # Cache the link and ffmpeg command if needed
                if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                    ffmpegcmd = str(getSettings()["ffmpeg command"])
                    ffmpegcmd = ffmpegcmd.replace("<url>", link)
                    ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000))
                    if proxy:
                        ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy)
                    else:
                        ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "")
                    ffmpegcmd = " ".join(ffmpegcmd.split()).split()
                    link_cache.set(f"{portalId}:{channelId}", link, ffmpegcmd)
                else:
                    link_cache.set(f"{portalId}:{channelId}", link)

                # Update rate limit
                rate_limiter.update_rate(f"{portalId}:{channelId}")
                
                if web:
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
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
<<<<<<< HEAD
                        return Response(streamData(), mimetype="application/octet-stream") # Return stream using ffmpeg
                    else:
                        logger.info("Redirect sent")
                        return redirect(link, code=302) # Redirect to direct stream link
=======
                        return Response(streamData(), mimetype="application/octet-stream")
                    else:
                        logger.info("Redirect sent")
                        return redirect(link, code=302)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

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
<<<<<<< HEAD

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

=======
                
                # Check cache for fallback first
                fallback_key = f"{fallbackPortalId}:{fallbackChannelId}"
                cached_link, cached_ffmpegcmd = link_cache.get(fallback_key)
                if cached_link:
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        if cached_ffmpegcmd:
                            ffmpegcmd = cached_ffmpegcmd
                            return Response(streamData(), mimetype="application/octet-stream")
                    else:
                        return redirect(cached_link, code=302)
                
                # Skip if the fallback channel is rate limited
                can_access_fallback, _ = rate_limiter.check_rate(fallback_key)
                if not can_access_fallback:
                    continue
                
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
                if fallbackChannelId != channelId:  # Don't try the same channel
                    if fallbackPortalId in portals and portals[fallbackPortalId]["enabled"] == "true": # Check if fallback portal is enabled
                        url = portals[fallbackPortalId].get("url")
                        macs = list(portals[fallbackPortalId]["macs"].keys())
                        proxy = portals[fallbackPortalId].get("proxy")
                        for mac in macs:
                            channels = None
                            cmd = None
                            link = None
<<<<<<< HEAD
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
=======
                            if streamsPerMac == 0 or isMacFree():
                                # Check link cache first for fallback
                                cached_link, cached_ffmpegcmd = link_cache.get(fallback_key)
                                if cached_link:
                                    link = cached_link
                                    if cached_ffmpegcmd:
                                        ffmpegcmd = cached_ffmpegcmd
                                else:
                                    try:
                                        token = stb.getToken(url, mac, proxy)
                                        ids = portals[fallbackPortalId]["ids"][mac]
                                        stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy)
                                        name_path = os.path.join(parent_folder, f"{portals[fallbackPortalId]['name']}.json")
                                        with open(name_path, 'r') as file:
                                            channels = json.load(file)
                                    except:
                                        logger.info(f"Unable to connect to fallback Portal({fallbackPortalId}) using MAC({mac})")
                                        add_alert("warning", f"Portal: {portals[fallbackPortalId]['name']}", f"Failed to connect to fallback portal using MAC {mac}")
                                    if channels:
                                        for c in channels:
                                            if str(c["id"]) == fallbackChannelId:
                                                channelName = portals[fallbackPortalId].get("custom channel names", {}).get(fallbackChannelId, c["name"])
                                                cmd = c["cmd"]
                                                break
                                        if cmd:
                                            ids = portals[fallbackPortalId]["ids"][mac]
                                            stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy)
                                            if "http://localhost/" in cmd or "http:///ch/" in cmd:
                                                link = stb.getLink(url, mac, token, cmd, proxy)
                                            else:
                                                link = cmd.split(" ")[1]

                                if link and testStream():
                                    # Cache the fallback link
                                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                                        ffmpegcmd = str(getSettings()["ffmpeg command"])
                                        ffmpegcmd = ffmpegcmd.replace("<url>", link)
                                        ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000))
                                        if proxy:
                                            ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy)
                                        else:
                                            ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "")
                                        ffmpegcmd = " ".join(ffmpegcmd.split()).split()
                                        link_cache.set(fallback_key, link, ffmpegcmd)
                                    else:
                                        link_cache.set(fallback_key, link)
                                    
                                    # Update rate limit for fallback
                                    rate_limiter.update_rate(fallback_key)
                                    
                                    logger.info(f"Fallback found in group {channelGroup} - using channel {fallbackChannelId} from Portal({fallbackPortalId})")
                                    add_alert("warning", f"Portal: {portals[fallbackPortalId]['name']}", f"Using fallback channel {channelName} (ID: {fallbackChannelId}) from group {channelGroup}")
                                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                                        return Response(streamData(), mimetype="application/octet-stream")
                                    else:
                                        logger.info("Redirect sent")
                                        return redirect(link)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

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

    Args:
        f (function): The function to be decorated (route handler).

    Returns:
        function: Decorated function that performs authentication and HDHR check.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        hdhrenabled = settings["enable hdhr"]
        if security == "false" or (auth and auth.username == username and auth.password == password): # Check authentication
            if hdhrenabled: # Check if HDHR emulation is enabled
                return f(*args, **kwargs) # Proceed to route handler if authenticated and HDHR enabled
        return make_response("Error", 404) # Return 404 error if authentication failed or HDHR not enabled
    return decorated

@app.route("/discover.json", methods=["GET"])
@hdhr
def discover():
    """
    HDHR discovery endpoint. Returns device information in JSON format.
    """
    settings = getSettings()
    data = {
        "BaseURL": host,
        "DeviceAuth": settings["hdhr name"],
        "DeviceID": settings["hdhr id"],
        "FirmwareName": "STB-Proxy",
        "FirmwareVersion": "1337",
        "FriendlyName": settings["hdhr name"],
        "LineupURL": f"{host}/lineup.json",
        "Manufacturer": "Chris",
        "ModelNumber": "1337",
        "TunerCount": int(settings["hdhr tuners"]),
    } # HDHR discovery data
    return jsonify(data) # Return discovery data as JSON

@app.route("/lineup_status.json", methods=["GET"])
@hdhr
def status():
    """
    HDHR lineup status endpoint. Returns scan status in JSON format.
    """
    data = {
        "ScanInProgress": 0,
        "ScanPossible": 0,
        "Source": "Antenna",
        "SourceList": ["Antenna"],
    } # HDHR lineup status data
    return jsonify(data) # Return status data as JSON

@app.route("/lineup.json", methods=["GET"])
@app.route("/lineup.post", methods=["POST"])
@hdhr
def lineup():
    """
    HDHR lineup endpoint. Returns channel lineup in JSON format.
    """
    lineup = [] # List to store HDHR lineup entries
    portals = getPortals()
    for portal in portals:
        if portals[portal]["enabled"] == "true": # Process only enabled portals
            enabledChannels = portals[portal].get("enabled channels", [])
            if len(enabledChannels) != 0: # Process if portal has enabled channels
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})

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

    try:
        # Load channel data from portal's JSON file
        name_path = os.path.join(parent_folder, f"{portal_name}.json")
        with open(name_path, 'r') as file:
            all_channels = json.load(file) # Load channel list from file

        # Create channel name lookup
        channel_lookup = {str(ch["id"]): ch["name"] for ch in all_channels}

        # Add new channels to the group
        for channel_id in channel_ids:
            channel_id = channel_id.strip()
            if channel_id:
                channel_name = channel_lookup.get(channel_id, "Unknown Channel") # Get channel name from lookup or use default
                new_entry = {
                    "channelId": channel_id,
                    "portalId": portal_id,
                    "channelName": channel_name
                }
                # Check if channel already exists
                exists = False
                for existing_channel in channel_groups[group_name]["channels"]:
                    if (existing_channel.get("channelId") == channel_id and
                        existing_channel.get("portalId") == portal_id):
                        exists = True
                        break # Break if channel already exists

                if not exists: # Add channel if it doesn't exist
                    channel_groups[group_name]["channels"].append(new_entry)

        saveChannelGroups(channel_groups) # Save updated channel groups
        return jsonify({
            "status": "success",
            "channels": channel_groups[group_name]["channels"] # Return updated channel list as JSON
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Error loading channel data: {str(e)}"}), 500 # Return error status if exception occurred

@app.route("/channels/remove_channel", methods=["POST"])
@authorise
def remove_channel():
    """
    API endpoint to remove a channel from a channel group.
    """
    data = request.get_json() # Get JSON data from request
    group_name = data.get("group_name") # Get group name from JSON data
    channel_id = data.get("channel_id") # Get channel ID from JSON data
    portal_id = data.get("portal_id") # Get portal ID from JSON data

    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404 # Return error status if group not found

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
<<<<<<< HEAD
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
=======
                if cached_link:
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        return redirect(f"/play/{portal_id}/{channel_id}", code=302)
                    else:
                        return redirect(cached_link, code=302)
                
                # If no cache, redirect to play route
                return redirect(f"/play/{portal_id}/{channel_id}", code=302)
    
    return make_response(f"No valid channels found in group '{group_name}'", 404)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64

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
    try:
        data = request.get_json() # Get JSON data from request
        alert_id = data.get('alert_id') # Get alert ID from JSON data

        if alert_id is None:
            return jsonify({"success": False, "error": "No alert ID provided"}), 400 # Return error status if no alert ID provided

        alerts = load_alerts() # Load alerts

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
    else:
<<<<<<< HEAD
        waitress.serve(app, port=8001, _quiet=True, threads=12) # Run using Waitress WSGI server in production mode

#endregion
=======
        waitress.serve(app, port=8001, _quiet=True, threads=12)
>>>>>>> ff45c7dafe287180f514b9b7241316a3f236bf64
