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

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

logger = logging.getLogger("STB-Proxy")
logger.setLevel(logging.INFO)
logFormat = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fileHandler = logging.FileHandler("STB-Proxy.log")
fileHandler.setFormatter(logFormat)
logger.addHandler(fileHandler)
consoleFormat = logging.Formatter("[%(levelname)s] %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleFormat)
logger.addHandler(consoleHandler)

basePath = os.path.abspath(os.getcwd())
parent_folder = os.path.join(basePath, "portals")

host = os.getenv("HOST", "localhost:8001")
configFile = os.getenv("CONFIG", os.path.join(basePath, "config.json"))

occupied = {}
config = {}
portalsdata = {}
portalmacids = {}
d_ffmpegcmd = "ffmpeg -re -http_proxy <proxy> -timeout <timeout> -i <url> -map 0 -codec copy -f mpegts pipe:"

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

# Add alerts storage
alerts_file = os.path.join(basePath, "alerts.json")

def load_alerts():
    try:
        with open(alerts_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_alerts(alerts):
    with open(alerts_file, "w") as f:
        json.dump(alerts, f, indent=4)

def add_alert(alert_type, source, message, status="active"):
    alerts = load_alerts()
    alert = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": alert_type,
        "source": source,
        "message": message,
        "status": status
    }
    alerts.append(alert)
    save_alerts(alerts)
    return alert

def save_json(file_path, data, message):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
        print(message)

def savePortalData(name, allChannels, allGenre):
    save_json(os.path.join(parent_folder, f"{name}.json"), allChannels, f"Channels '{name}.json' saved")
    save_json(os.path.join(parent_folder, f"{name}_genre.json"), allGenre, f"Genres '{name}_genre.json' saved")

def loadConfig():
    try:
        with open(configFile) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning("No existing config found. Creating a new one")
        data = {}

    data.setdefault("portals", {})
    data.setdefault("settings", {})

    settings = data["settings"]
    settingsOut = {setting: settings.get(setting, default) for setting, default in defaultSettings.items()}

    data["settings"] = settingsOut

    portals = data["portals"]
    portalsOut = {portal: {setting: portals[portal].get(setting, default) for setting, default in defaultPortal.items()} for portal in portals}

    data["portals"] = portalsOut

    save_json(configFile, data, "Config saved")

    return data

def getPortals():
    return config["portals"]

def savePortals(portals):
    config["portals"] = portals
    save_json(configFile, config, "Portals saved")

def getSettings():
    return config["settings"]

def saveSettings(settings):
    config["settings"] = settings
    save_json(configFile, config, "Settings saved")

def getChannelGroups():
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
                saveChannelGroups(groups)
            
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
                    
            saveChannelGroups(groups)
    except FileNotFoundError:
        # Create default group if file doesn't exist
        groups = {
            "Default Group": {
                "channels": [],
                "logo": "",
                "order": 1
            }
        }
        saveChannelGroups(groups)
    return groups

def saveChannelGroups(channel_groups):
    with open(os.path.join(basePath, "channel_groups.json"), "w") as f:
        json.dump(channel_groups, f, indent=4)

def authorise(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        if security == "false" or (auth and auth.username == username and auth.password == password):
            return f(*args, **kwargs)
        return make_response("Could not verify your login!", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})
    return decorated

def moveMac(portalId, mac):
    try:
        portals = getPortals()
        macs = portals[portalId]["macs"]
        macs[mac] = macs.pop(mac)
        portals[portalId]["macs"] = macs
        savePortals(portals)
    except Exception as e:
        add_alert("error", f"Portal {portalId}", f"Error moving MAC {mac}: {str(e)}")
        raise

@app.route("/", methods=["GET"])
@authorise
def home():
    return redirect("/portals", code=302)

@app.route("/portals", methods=["GET"])
@authorise
def portals():
    return render_template("portals.html", portals=getPortals())

@app.route("/portal/add", methods=["POST"])
@authorise
def portalsAdd():
    id = uuid.uuid4().hex
    enabled = "true"
    name = request.form["name"]
    url = request.form["url"]
    macs = list(set(request.form["macs"].split(",")))
    streamsPerMac = request.form["streams per mac"]
    proxy = request.form["proxy"]

    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error(f"Error getting URL for Portal({name})")
            flash(f"Error getting URL for Portal({name})", "danger")
            return redirect("/portals", code=302)

    macsd = {}
    ids = {}
    gotchannels = False
    for mac in macs:
        token = stb.getToken(url, mac, proxy)
        if token:
            device_id = stb.generate_device_id(mac)
            device_id2 = device_id
            timestamp = int(time.time())
            signature = stb.generate_signature(mac, token, [str(timestamp)])
            profile = stb.getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy)
            print(profile)
            if 'block_msg' in profile and profile['block_msg']:
                logger.info(profile['block_msg'])
            expiry = stb.getExpires(url, mac, token, proxy)
            if 'expire_billing_date' in profile and profile['expire_billing_date'] and not expiry:
                expiry = profile['expire_billing_date']
            if 'created' in profile and profile['created'] and not expiry:
                expiry = "Never"
            if expiry:
                macsd[mac] = expiry
                ids[mac] = {
                    "device_id": device_id,
                    "device_id2": device_id2,
                    "signature": signature,
                    "timestamp": timestamp
                }
                if not gotchannels:
                    allChannels = stb.getAllChannels(url, mac, token, proxy)
                    allGenre = stb.getGenreNames(url, mac, token, proxy)
                    savePortalData(name, allChannels, allGenre)
                    gotchannels = True
                logger.info(f"Successfully tested MAC({mac}) for Portal({name})")
                flash(f"Successfully tested MAC({mac}) for Portal({name})", "success")
                continue

        logger.error(f"Error testing MAC({mac}) for Portal({name})")
        flash(f"Error testing MAC({mac}) for Portal({name})", "danger")

    if macsd:
        portal = {
            "enabled": enabled,
            "name": name,
            "url": url,
            "macs": macsd,
            "ids": ids,
            "streams per mac": streamsPerMac,
            "proxy": proxy,
        }

        for setting, default in defaultPortal.items():
            portal.setdefault(setting, default)

        portals = getPortals()
        portals[id] = portal
        savePortals(portals)
        logger.info(f"Portal({portal['name']}) added!")
    else:
        logger.error(f"None of the MACs tested OK for Portal({name}). Adding not successful")

    return redirect("/portals", code=302)

@app.route("/portal/update", methods=["POST"])
@authorise
def portalUpdate():
    id = request.form["id"]
    enabled = request.form.get("enabled", "false")
    name = request.form["name"]
    url = request.form["url"]
    newmacs = list(set(request.form["macs"].split(",")))
    streamsPerMac = request.form["streams per mac"]
    proxy = request.form["proxy"]
    retest = request.form.get("retest", None)

    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error(f"Error getting URL for Portal({name})")
            flash(f"Error getting URL for Portal({name})", "danger")
            return redirect("/portals", code=302)

    portals = getPortals()
    oldmacs = portals[id]["macs"]
   
    macsout = {}
    deadmacs = []

    for mac in newmacs:
        if retest or mac not in oldmacs.keys():
            token = stb.getToken(url, mac, proxy)
            if token:
                ids = portals[id]["ids"][mac]
                stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy)
                expiry = stb.getExpires(url, mac, token, proxy)
                if expiry:
                    macsout[mac] = expiry
                    logger.info(f"Successfully tested MAC({mac}) for Portal({name})")
                    flash(f"Successfully tested MAC({mac}) for Portal({name})", "success")

            if mac not in macsout:
                deadmacs.append(mac)

        if mac in oldmacs and mac not in deadmacs:
            macsout[mac] = oldmacs[mac]

        if mac not in macsout:
            logger.error(f"Error testing MAC({mac}) for Portal({name})")
            flash(f"Error testing MAC({mac}) for Portal({name})", "danger")

    if macsout:
        portals[id].update({
            "enabled": enabled,
            "name": name,
            "url": url,
            "macs": macsout,
            "streams per mac": streamsPerMac,
            "proxy": proxy,
        })
        savePortals(portals)
        logger.info(f"Portal({name}) updated!")
        flash(f"Portal({name}) updated!", "success")
    else:
        logger.error(f"None of the MACs tested OK for Portal({name}). Adding not successful")

    return redirect("/portals", code=302)

@app.route("/portal/remove", methods=["POST"])
@authorise
def portalRemove():
    id = request.form["deleteId"]
    portals = getPortals()
    name = portals[id]["name"]
    del portals[id]
    savePortals(portals)
    logger.info(f"Portal ({name}) removed!")
    flash(f"Portal ({name}) removed!", "success")
    return redirect("/portals", code=302)

@app.route("/editor", methods=["GET"])
@authorise
def editor():
    channel_groups = getChannelGroups()
    return render_template("editor.html", channel_groups=channel_groups)

@app.route("/editor_data", methods=["GET"])
@authorise
def editor_data():
    channels = []
    portals = getPortals()
    channel_groups = getChannelGroups()
    for portal in portals:
        if portals[portal]["enabled"] == "true":
            portalName = portals[portal]["name"]
            url = portals[portal]["url"]
            macs = list(portals[portal]["macs"].keys())
            proxy = portals[portal]["proxy"]
            enabledChannels = portals[portal].get("enabled channels", [])
            customChannelNames = portals[portal].get("custom channel names", {})
            customGenres = portals[portal].get("custom genres", {})
            customChannelNumbers = portals[portal].get("custom channel numbers", {})
            customEpgIds = portals[portal].get("custom epg ids", {})


            for mac in macs:
                try:
                    name_path = os.path.join(parent_folder, f"{portalName}.json")
                    genre_path = os.path.join(parent_folder, f"{portalName}_genre.json")
                    with open(name_path, 'r') as file:
                        allChannels = json.load(file)
                    with open(genre_path, 'r') as file:
                        genres = json.load(file)
                    break
                except:
                    allChannels = None
                    genres = None

            if allChannels and genres:
                for channel in allChannels:
                    channelId = str(channel["id"])
                    channelName = str(channel["name"])
                    channelNumber = str(channel["number"])
                    genre = str(genres.get(str(channel["tv_genre_id"])))
                    enabled = channelId in enabledChannels
                    customChannelNumber = customChannelNumbers.get(channelId, "")
                    customChannelName = customChannelNames.get(channelId, "")
                    customGenre = customGenres.get(channelId, "")
                    customEpgId = customEpgIds.get(channelId, "")

                    # Determine the group for this channel
                    group = ""
                    for group_name, group_data in channel_groups.items():
                        if "channels" in group_data:
                            for ch in group_data["channels"]:
                                if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portal:
                                    group = group_name
                                    break
                        if group:
                            break

                    channels.append({
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
                        "link": f"http://{host}/play/{portal}/{channelId}?web=true",
                    })
            else:
                logger.error(f"Error getting channel data for {portalName}, skipping")
                flash(f"Error getting channel data for {portalName}, skipping", "danger")

    return jsonify({"data": channels})

@app.route("/editor/save", methods=["POST"])
@authorise
def editorSave():
    enabledEdits = json.loads(request.form["enabledEdits"])
    numberEdits = json.loads(request.form["numberEdits"])
    nameEdits = json.loads(request.form["nameEdits"])
    genreEdits = json.loads(request.form["genreEdits"])
    epgEdits = json.loads(request.form["epgEdits"])
    groupEdits = json.loads(request.form["groupEdits"])
    portals = getPortals()
    channel_groups = getChannelGroups()

    def update_portal(edit, key, subkey):
        portal = edit["portal"]
        channelId = edit["channel id"]
        value = edit[key]
        if value:
            portals[portal].setdefault(subkey, {})
            portals[portal][subkey].update({channelId: value})
        else:
            portals[portal][subkey].pop(channelId, None)

    for edit in enabledEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        enabled = edit["enabled"]
        if enabled:
            portals[portal].setdefault("enabled channels", [])
            portals[portal]["enabled channels"].append(channelId)
        else:
            portals[portal]["enabled channels"] = list(filter((channelId).__ne__, portals[portal]["enabled channels"]))

    for edit in numberEdits:
        update_portal(edit, "custom number", "custom channel numbers")

    for edit in nameEdits:
        update_portal(edit, "custom name", "custom channel names")

    for edit in genreEdits:
        update_portal(edit, "custom genre", "custom genres")

    for edit in epgEdits:
        update_portal(edit, "custom epg id", "custom epg ids")


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
                channel_groups[group] = {
                    "channels": [],
                    "logo": "",
                    "order": max([g.get("order", 0) for g in channel_groups.values()], default=0) + 1
                }
            
            # Add as dict with both channelId and portalId
            channel_entry = {
                "channelId": channelId,
                "portalId": portal
            }
            if channel_entry not in channel_groups[group]["channels"]:
                channel_groups[group]["channels"].append(channel_entry)

    saveChannelGroups(channel_groups)
    logger.info("Playlist config saved!")
    flash("Playlist config saved!", "success")

    return redirect("/editor", code=302)

@app.route("/editor/reset", methods=["POST"])
@authorise
def editorReset():
    portals = getPortals()
    for portal in portals:
        portals[portal].update({
            "enabled channels": [],
            "custom channel numbers": {},
            "custom channel names": {},
            "custom genres": {},
            "custom epg ids": {},
        })

    savePortals(portals)
    logger.info("Playlist reset!")
    flash("Playlist reset!", "success")

    return redirect("/editor", code=302)

@app.route("/settings", methods=["GET"])
@authorise
def settings():
    return render_template("settings.html", settings=getSettings(), defaultSettings=defaultSettings)

@app.route("/settings/save", methods=["POST"])
@authorise
def save():
    settings = {setting: request.form.get(setting, "false") for setting in defaultSettings}
    saveSettings(settings)
    logger.info("Settings saved!")
    flash("Settings saved!", "success")
    return redirect("/settings", code=302)

@app.route("/playlist", methods=["GET"])
@authorise
def playlist():
    channels = []
    portals = getPortals()
    for portal in portals:
        if portals[portal]["enabled"] == "true":
            enabledChannels = portals[portal].get("enabled channels", [])
            if enabledChannels:
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customGenres = portals[portal].get("custom genres", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})
                customEpgIds = portals[portal].get("custom epg ids", {})

                for mac in macs:
                    try:
                        name_path = os.path.join(parent_folder, f"{name}.json")
                        genre_path = os.path.join(parent_folder, f"{name}_genre.json")
                        with open(name_path, 'r') as file:
                            allChannels = json.load(file)
                        with open(genre_path, 'r') as file:
                            genres = json.load(file)
                        break
                    except:
                        allChannels = None
                        genres = None

                if allChannels and genres:
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels:
                            channelName = customChannelNames.get(channelId, str(channel.get("name")))
                            genre = customGenres.get(channelId, str(genres.get(str(channel.get("tv_genre_id")))))
                            channelNumber = customChannelNumbers.get(channelId, str(channel.get("number")))
                            epgId = customEpgIds.get(channelId, f"{portal}{channelId}")
                            channels.append(
                                f'#EXTINF:-1 tvg-id="{epgId}"'
                                + (f' tvg-chno="{channelNumber}"' if getSettings().get("use channel numbers", "true") == "true" else "")
                                + (f' group-title="{genre}"' if getSettings().get("use channel genres", "true") == "true" else "")
                                + f'",{channelName}\nhttp://{host}/play/{portal}/{channelId}'
                            )
                else:
                    logger.error(f"Error making playlist for {name}, skipping")

    if getSettings().get("sort playlist by channel name", "true") == "true":
        channels.sort(key=lambda k: k.split(",")[1].split("\n")[0])
    if getSettings().get("use channel numbers", "true") == "true" and getSettings().get("sort playlist by channel number", "false") == "true":
        channels.sort(key=lambda k: k.split('tvg-chno="')[1].split('"')[0])
    if getSettings().get("use channel genres", "true") == "true" and getSettings().get("sort playlist by channel genre", "false") == "true":
        channels.sort(key=lambda k: k.split('group-title="')[1].split('"')[0])

    playlist = "#EXTM3U \n" + "\n".join(channels)

    return Response(playlist, mimetype="text/plain")

@app.route("/groups_playlist", methods=["GET"])
@authorise
def groups_playlist():
    channel_groups = getChannelGroups()
    
    # Sort groups by their order
    sorted_groups = sorted(channel_groups.items(), key=lambda x: x[1].get("order", 0))
    
    playlist_entries = []
    for group_name, group_data in sorted_groups:
        # Get the group's logo URL, if it exists
        logo_url = group_data.get("logo", "")
        if logo_url:
            # Make the logo URL absolute by adding the host
            logo_url = f"http://{host}{logo_url}"
            
        # Create the EXTINF line for the group
        playlist_entries.append(
            f'#EXTINF:-1 tvg-id="{group_name}" tvg-logo="{logo_url}",{group_name}\n'
            f'http://{host}/chplay/{group_name}'
        )
    
    playlist = "#EXTM3U\n" + "\n".join(playlist_entries)
    return Response(playlist, mimetype="text/plain")

# Add channel cooldown tracking
channel_cooldowns = {}
COOLDOWN_DURATION = 30  # seconds

@app.route("/play/<portalId>/<channelId>", methods=["GET"])
def channel(portalId, channelId):
    def streamData():
        def occupy():
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
            with subprocess.Popen(
                ffmpegcmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr for debugging
            ) as ffmpeg_sp:
                while True:
                    chunk = ffmpeg_sp.stdout.read(1024)
                    if not chunk:
                        if ffmpeg_sp.poll() != 0:
                            stderr_output = ffmpeg_sp.stderr.read().decode('utf-8')
                            print(f"Ffmpeg error output: {stderr_output}")
                            print(f"Ffmpeg closed with error({ffmpeg_sp.poll()}). Moving MAC({mac}) for Portal({portalName})")
                            add_alert("error", f"Portal: {portalName}", f"Stream failed for channel {channelName} (ID: {channelId}). Moving MAC {mac}.")
                            moveMac(portalId, mac)
                        break
                    yield chunk
        except Exception as e:
            print(f"Exception during streaming: {e}")
            add_alert("error", f"Portal: {portalName}", f"Stream error for channel {channelName} (ID: {channelId})")
        finally:
            unoccupy()
            if 'ffmpeg_sp' in locals():
                ffmpeg_sp.kill()

    def testStream():
        timeout = int(getSettings().get("ffmpeg timeout")) * 1000000
        ffprobecmd = [
            "ffprobe",
            "-v", "info",  # Show more info for debugging
            "-select_streams", "v:0",  # Select the first video stream
            "-show_entries", "stream=codec_name",  # Show codec name
            "-of", "default=noprint_wrappers=1:nokey=1",  # Output format
            "-timeout", str(timeout),
            "-i", link
        ]

        if proxy:
            ffprobecmd.extend(["-http_proxy", proxy])

        try:
            with subprocess.Popen(
                ffprobecmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as ffprobe_sb:
                stdout, stderr = ffprobe_sb.communicate()
                result = ffprobe_sb.returncode == 0 and stdout.strip() != b''
                if not result:
                    add_alert("error", f"Portal: {portalName}", f"Stream test failed for channel {channelName} (ID: {channelId})")
                return result
        except Exception as e:
            logger.error(f"Exception during stream test: {e}")
            add_alert("error", f"Portal: {portalName}", f"Stream test encountered an error for channel {channelName} (ID: {channelId})")
            return False

    def isMacFree():
        return sum(1 for i in occupied.get(portalId, []) if i["mac"] == mac) < streamsPerMac

    def check_cooldown():
        cooldown_key = f"{portalId}:{channelId}"
        if cooldown_key in channel_cooldowns:
            last_access = channel_cooldowns[cooldown_key]
            time_elapsed = time.time() - last_access
            if time_elapsed < COOLDOWN_DURATION:
                return False, COOLDOWN_DURATION - time_elapsed
        return True, 0

    portal = getPortals().get(portalId)
    portalName = portal.get("name")
    url = portal.get("url")
    macs = list(portal["macs"].keys())
    streamsPerMac = int(portal.get("streams per mac"))
    proxy = portal.get("proxy")
    web = request.args.get("web")
    ip = request.remote_addr

    # Initialize channelName at the start
    channelName = None
    try:
        name_path = os.path.join(parent_folder, f"{portalName}.json")
        with open(name_path, 'r') as file:
            channels = json.load(file)
            for c in channels:
                if str(c["id"]) == channelId:
                    channelName = portal.get("custom channel names", {}).get(channelId, c["name"])
                    break
    except:
        pass
    
    # If we still don't have a channel name, use a default
    if not channelName:
        channelName = f"Channel ID: {channelId}"

    logger.info(f"IP({ip}) requested Portal({portalId}):Channel({channelId})")

    # Check cooldown
    can_access, remaining_time = check_cooldown()
    if not can_access and not web:  # Don't apply cooldown for web preview
        logger.info(f"Channel {channelName} ({channelId}) in cooldown. {remaining_time:.1f} seconds remaining")
        add_alert("warning", f"Portal: {portalName}", f"Channel {channelName} in cooldown. {remaining_time:.1f} seconds remaining. Attempting fallback.")
        
        # Try to find a fallback in the same group
        channel_groups = getChannelGroups()
        current_group = None
        
        # Find which group this channel belongs to
        for group_name, group_data in channel_groups.items():
            if "channels" in group_data:
                for ch in group_data["channels"]:
                    if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portalId:
                        current_group = group_name
                        break
            if current_group:
                break

        if current_group:
            # Try other channels in the same group
            for channel_entry in channel_groups[current_group]["channels"]:
                if not isinstance(channel_entry, dict):
                    continue
                    
                fallback_channel_id = channel_entry['channelId']
                fallback_portal_id = channel_entry['portalId']
                
                # Skip if it's the same channel or if the fallback is also in cooldown
                fallback_key = f"{fallback_portal_id}:{fallback_channel_id}"
                if (fallback_channel_id == channelId and fallback_portal_id == portalId) or \
                   (fallback_key in channel_cooldowns and time.time() - channel_cooldowns[fallback_key] < COOLDOWN_DURATION):
                    continue

                return redirect(f"/play/{fallback_portal_id}/{fallback_channel_id}")

        # If no fallback found, return error
        return make_response(f"Channel in cooldown. Please wait {remaining_time:.1f} seconds.", 429)

    freeMac = False

    for mac in macs:
        channels = None
        cmd = None
        link = None
        if streamsPerMac == 0 or isMacFree():
            logger.info(f"Trying Portal({portalId}):MAC({mac}):Channel({channelId})")
            freeMac = True
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
                link = cmd.split(" ")[1]

        if link:
            if getSettings().get("test streams", "true") == "false" or testStream():
                # Update cooldown timestamp
                channel_cooldowns[f"{portalId}:{channelId}"] = time.time()
                
                if web:
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
                    ]
                    if proxy:
                        ffmpegcmd.insert(1, "-http_proxy")
                        ffmpegcmd.insert(2, proxy)
                    return Response(streamData(), mimetype="application/octet-stream")
                else:
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        ffmpegcmd = str(getSettings()["ffmpeg command"])
                        ffmpegcmd = ffmpegcmd.replace("<url>", link)
                        ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000))
                        if proxy:
                            ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy)
                        else:
                            ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "")
                        ffmpegcmd = " ".join(ffmpegcmd.split()).split()
                        return Response(streamData(), mimetype="application/octet-stream")
                    else:
                        logger.info("Redirect sent")
                        return redirect(link)

        logger.info(f"Unable to connect to Portal({portalId}) using MAC({mac})")
        logger.info(f"Moving MAC({mac}) for Portal({portalName})")
        moveMac(portalId, mac)

        if getSettings().get("try all macs", "false") != "true":
            break

    if not web:
        logger.info(f"Portal({portalId}):Channel({channelId}) is not working. Looking for fallbacks...")
        add_alert("error", f"Portal: {portalName}", f"Channel {channelName} (ID: {channelId}) is not working, searching for fallbacks...")

        portals = getPortals()
        channelGroups = getChannelGroups()
        
        # Find which group this channel belongs to
        channelGroup = None
        for group_name, group_data in channelGroups.items():
            if "channels" in group_data:
                for ch in group_data["channels"]:
                    if isinstance(ch, dict) and ch.get('channelId') == channelId and ch.get('portalId') == portalId:
                        channelGroup = group_name
                        break
            if channelGroup:
                break

        if channelGroup:
            logger.info(f"Found channel in group: {channelGroup}")
            # Try all other channels in the same group
            for channel_entry in channelGroups[channelGroup]["channels"]:
                if not isinstance(channel_entry, dict):
                    continue
                    
                fallbackChannelId = channel_entry['channelId']
                fallbackPortalId = channel_entry['portalId']
                
                # Skip if the fallback channel is in cooldown
                fallback_key = f"{fallbackPortalId}:{fallbackChannelId}"
                if fallback_key in channel_cooldowns and time.time() - channel_cooldowns[fallback_key] < COOLDOWN_DURATION:
                    continue
                
                if fallbackChannelId != channelId:  # Don't try the same channel
                    if fallbackPortalId in portals and portals[fallbackPortalId]["enabled"] == "true":
                        url = portals[fallbackPortalId].get("url")
                        macs = list(portals[fallbackPortalId]["macs"].keys())
                        proxy = portals[fallbackPortalId].get("proxy")
                        for mac in macs:
                            channels = None
                            cmd = None
                            link = None
                            if streamsPerMac == 0 or isMacFree():
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
                                            # Update cooldown timestamp for the fallback channel
                                            channel_cooldowns[fallback_key] = time.time()
                                            
                                            logger.info(f"Fallback found in group {channelGroup} - using channel {fallbackChannelId} from Portal({fallbackPortalId})")
                                            add_alert("warning", f"Portal: {portals[fallbackPortalId]['name']}", f"Using fallback channel {channelName} (ID: {fallbackChannelId}) from group {channelGroup}")
                                            if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                                                ffmpegcmd = str(getSettings()["ffmpeg command"])
                                                ffmpegcmd = ffmpegcmd.replace("<url>", link)
                                                ffmpegcmd = ffmpegcmd.replace("<timeout>", str(int(getSettings()["ffmpeg timeout"]) * 1000000))
                                                if proxy:
                                                    ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy)
                                                else:
                                                    ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "")
                                                ffmpegcmd = " ".join(ffmpegcmd.split()).split()
                                                return Response(streamData(), mimetype="application/octet-stream")
                                            else:
                                                logger.info("Redirect sent")
                                                return redirect(link)

    if freeMac:
        logger.info(f"No working streams found for Portal({portalId}):Channel({channelId})")
        add_alert("error", f"Portal: {portalName}", f"No working streams found for channel {channelName} (ID: {channelId})")
    else:
        logger.info(f"No free MAC for Portal({portalId}):Channel({channelId})")
        add_alert("error", f"Portal: {portalName}", f"No free MAC available for channel {channelName} (ID: {channelId})")

    return make_response("No streams available", 503)

@app.route("/dashboard")
@authorise
def dashboard():
    return render_template("dashboard.html")

@app.route("/streaming")
@authorise
def streaming():
    return jsonify(occupied)

@app.route("/log")
@authorise
def log():
    with open("STB-Proxy.log") as f:
        log = f.read()
    return log

def hdhr(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        hdhrenabled = settings["enable hdhr"]
        if security == "false" or (auth and auth.username == username and auth.password == password):
            if hdhrenabled:
                return f(*args, **kwargs)
        return make_response("Error", 404)
    return decorated

@app.route("/discover.json", methods=["GET"])
@hdhr
def discover():
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
    }
    return jsonify(data)

@app.route("/lineup_status.json", methods=["GET"])
@hdhr
def status():
    data = {
        "ScanInProgress": 0,
        "ScanPossible": 0,
        "Source": "Antenna",
        "SourceList": ["Antenna"],
    }
    return jsonify(data)

@app.route("/lineup.json", methods=["GET"])
@app.route("/lineup.post", methods=["POST"])
@hdhr
def lineup():
    lineup = []
    portals = getPortals()
    for portal in portals:
        if portals[portal]["enabled"] == "true":
            enabledChannels = portals[portal].get("enabled channels", [])
            if len(enabledChannels) != 0:
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})

                for mac in macs:
                    try:
                        name_path = os.path.join(parent_folder, name + ".json")
                        genre_path = os.path.join(parent_folder, name +"_genre"+ ".json")
                        with open(name_path, 'r') as file:
                            allChannels = json.load(file)
                        with open(genre_path, 'r') as file:
                            genres = json.load(file)
                        break
                    except:
                        allChannels = None

                if allChannels:
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels:
                            channelName = customChannelNames.get(channelId)
                            if channelName == None:
                                channelName = str(channel.get("name"))
                            channelNumber = customChannelNumbers.get(channelId)
                            if channelNumber == None:
                                channelNumber = str(channel.get("number"))

                            lineup.append(
                                {
                                    "GuideNumber": channelNumber,
                                    "GuideName": channelName,
                                    "URL": "http://"
                                    + host
                                    + "/play/"
                                    + portal
                                    + "/"
                                    + channelId,
                                }
                            )
                else:
                    logger.error("Error making lineup for {}, skipping".format(name))

    return flask.jsonify(lineup)


@app.route("/channels", methods=["GET", "POST"])
@authorise
def channels():
    if request.method == "POST":
        group_name = request.form["group_name"]
        portal_id = request.form["portal"]
        channel_ids = request.form["channels"].split(",")
        
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
        
        channel_groups[group_name] = channel_entries
        saveChannelGroups(channel_groups)
        flash(f"Channel group '{group_name}' saved!", "success")
        return redirect("/channels", code=302)
    else:
        return render_template("channels.html", channel_groups=getChannelGroups(), portals=getPortals())

@app.route("/channels/delete", methods=["POST"])
@authorise
def delete_channel_group():
    data = request.get_json()
    group_name = data.get('group_name')
    if group_name:
        channel_groups = getChannelGroups()
        if group_name in channel_groups:
            del channel_groups[group_name]
            saveChannelGroups(channel_groups)
            flash(f"Channel group '{group_name}' deleted!", "success")
            return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route("/channels/get_group/<group_name>")
@authorise
def get_group(group_name):
    channel_groups = getChannelGroups()
    if group_name in channel_groups:
        return jsonify({"status": "success", "channels": channel_groups[group_name]})
    return jsonify({"status": "error", "message": "Group not found"}), 404

@app.route("/channels/add_channels", methods=["POST"])
@authorise
def add_channels():
    data = request.get_json()
    group_name = data.get("group_name")
    portal_id = data.get("portal")
    channel_ids = data.get("channels", "").split(",")
    
    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404
        
    # Get portal info
    portals = getPortals()
    if portal_id not in portals:
        return jsonify({"status": "error", "message": "Portal not found"}), 404
    
    portal = portals[portal_id]
    portal_name = portal["name"]
    
    try:
        # Load channel data from portal's JSON file
        name_path = os.path.join(parent_folder, f"{portal_name}.json")
        with open(name_path, 'r') as file:
            all_channels = json.load(file)
            
        # Create channel name lookup
        channel_lookup = {str(ch["id"]): ch["name"] for ch in all_channels}
        
        # Add new channels to the group
        for channel_id in channel_ids:
            channel_id = channel_id.strip()
            if channel_id:
                channel_name = channel_lookup.get(channel_id, "Unknown Channel")
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
                        break
                
                if not exists:
                    channel_groups[group_name]["channels"].append(new_entry)
        
        saveChannelGroups(channel_groups)
        return jsonify({
            "status": "success",
            "channels": channel_groups[group_name]["channels"]
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error loading channel data: {str(e)}"}), 500

@app.route("/channels/remove_channel", methods=["POST"])
@authorise
def remove_channel():
    data = request.get_json()
    group_name = data.get("group_name")
    channel_id = data.get("channel_id")
    portal_id = data.get("portal_id")
    
    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404
        
    # Remove the channel from the group
    channel_groups[group_name]["channels"] = [
        ch for ch in channel_groups[group_name]["channels"] 
        if not (isinstance(ch, dict) and 
                ch.get("channelId") == channel_id and 
                ch.get("portalId") == portal_id)
    ]
    
    saveChannelGroups(channel_groups)
    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]["channels"]
    })

@app.route("/channels/create", methods=["POST"])
@authorise
def create_group():
    data = request.get_json()
    group_name = data.get("group_name")
    
    if not group_name:
        return jsonify({"status": "error", "message": "Group name is required"}), 400
        
    channel_groups = getChannelGroups()
    if group_name in channel_groups:
        return jsonify({"status": "error", "message": "Group already exists"}), 400
    
    # Get the next order number starting from 1
    next_order = max([group["order"] for group in channel_groups.values()], default=0) + 1
        
    channel_groups[group_name] = {
        "channels": [],
        "logo": "",
        "order": next_order
    }
    saveChannelGroups(channel_groups)
    
    return jsonify({"status": "success"})

@app.route("/channels/reorder", methods=["POST"])
@authorise
def reorder_channels():
    data = request.get_json()
    group_name = data.get("group_name")
    new_channels = data.get("channels")
    
    if not group_name or not new_channels:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
    
    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404
    
    channel_groups[group_name]["channels"] = new_channels
    saveChannelGroups(channel_groups)
    
    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]["channels"]
    })

@app.route("/channels/upload_logo", methods=["POST"])
@authorise
def upload_group_logo():
    if 'logo' not in request.files or 'group_name' not in request.form:
        return jsonify({"status": "error", "message": "Missing logo or group name"}), 400
        
    file = request.files['logo']
    group_name = request.form['group_name']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
        
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({"status": "error", "message": "Invalid file type"}), 400
    
    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return jsonify({"status": "error", "message": "Group not found"}), 404
    
    # Create logos directory if it doesn't exist
    logos_dir = os.path.join(basePath, "static", "logos")
    os.makedirs(logos_dir, exist_ok=True)
    
    # Save the file with a unique name
    filename = f"group_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    file_path = os.path.join(logos_dir, filename)
    file.save(file_path)
    
    # Update group logo path
    channel_groups[group_name]["logo"] = f"/static/logos/{filename}"
    saveChannelGroups(channel_groups)
    
    return jsonify({
        "status": "success",
        "logo_url": channel_groups[group_name]["logo"]
    })

@app.route("/channels/reorder_groups", methods=["POST"])
@authorise
def reorder_groups():
    data = request.get_json()
    new_order = data.get("groups")
    
    if not new_order:
        return jsonify({"status": "error", "message": "Missing groups order"}), 400
    
    channel_groups = getChannelGroups()
    
    # Update group orders starting from 1
    for index, group_name in enumerate(new_order, start=1):
        if group_name in channel_groups:
            channel_groups[group_name]["order"] = index
    
    saveChannelGroups(channel_groups)
    return jsonify({"status": "success"})

@app.route("/chplay/<groupID>", methods=["GET"])
def chplay(groupID):
    group_name = groupID
    if not group_name:
        return make_response("Group parameter is required", 400)
    
    channel_groups = getChannelGroups()
    if group_name not in channel_groups:
        return make_response(f"Group '{group_name}' not found", 404)
    
    # Get all channels in the group
    if "channels" not in channel_groups[group_name]:
        return make_response(f"Invalid group structure for '{group_name}'", 404)
        
    channels = channel_groups[group_name]["channels"]
    if not channels:
        return make_response(f"No channels found in group '{group_name}'", 404)
    
    # Try each channel in the group until we find one that works
    for channel in channels:
        if isinstance(channel, dict):
            portal_id = channel.get("portalId")
            channel_id = channel.get("channelId")
            if portal_id and channel_id:
                # Redirect to the play route for this channel
                return redirect(f"/play/{portal_id}/{channel_id}")
    
    return make_response(f"No valid channels found in group '{group_name}'", 404)

@app.route("/alerts", methods=["GET"])
@authorise
def alerts():
    return render_template("alerts.html", alerts=load_alerts())

@app.route("/alerts/unresolved/count", methods=["GET"])
@authorise
def unresolved_alerts_count():
    alerts = load_alerts()
    count = sum(1 for alert in alerts if alert.get('status') == 'active')
    return jsonify({"count": count})

@app.route("/resolve_alert", methods=["POST"])
@authorise
def resolve_alert():
    try:
        data = request.get_json()
        alert_id = data.get('alert_id')
        
        if alert_id is None:
            return jsonify({"success": False, "error": "No alert ID provided"}), 400
        
        alerts = load_alerts()
        
        if alert_id >= len(alerts):
            return jsonify({"success": False, "error": "Invalid alert ID"}), 404
        
        # Update alert status
        alerts[alert_id]["status"] = "resolved"
        alerts[alert_id]["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save updated alerts
        save_alerts(alerts)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Add error handling for non-working channels
def check_channel_status(url, mac, token, proxy):
    try:
        response = stb.make_request(url, proxy)
        if not response or response.status_code != 200:
            add_alert("error", "Channel Check", f"Channel not responding: {url}")
            return False
        return True
    except Exception as e:
        add_alert("error", "Channel Check", f"Error checking channel {url}: {str(e)}")
        return False

if __name__ == "__main__":
    config = loadConfig()
    if "TERM_PROGRAM" in os.environ.keys() and os.environ["TERM_PROGRAM"] == "vscode":
        app.run(host="0.0.0.0", port=8001, debug=True)
    else:
        waitress.serve(app, port=8001, _quiet=True, threads=12)