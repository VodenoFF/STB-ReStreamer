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
    "fallback channels": {},
    "channel groups": {},
}

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
    except FileNotFoundError:
        # Create default group if file doesn't exist
        groups = {
            "Default Group": []  # Default group with empty channel list
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
    portals = getPortals()
    macs = portals[portalId]["macs"]
    macs[mac] = macs.pop(mac)
    portals[portalId]["macs"] = macs
    savePortals(portals)

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
            if 'block_msg' in profile and profile['block_msg']:
                logger.info(profile['block_msg'])
            expiry = stb.getExpires(url, mac, token, proxy)
            if 'expire_billing_date' in profile and profile['expire_billing_date'] and not expiry:
                expiry = profile['expire_billing_date']
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
            fallbackChannels = portals[portal].get("fallback channels", {})

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
                    fallbackChannel = fallbackChannels.get(channelId, "")

                    # Determine the group for this channel
                    group = ""
                    for group_name, group_channels in channel_groups.items():
                        for ch in group_channels:
                            if isinstance(ch, dict) and ch.get('channelId') == channelId:
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
                        "fallbackChannel": fallbackChannel,
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
    fallbackEdits = json.loads(request.form["fallbackEdits"])
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

    for edit in fallbackEdits:
        update_portal(edit, "channel name", "fallback channels")

    for edit in groupEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        group = edit["group"]

        # Remove channel from all existing groups first
        for g in channel_groups.values():
            # Each entry in the group is now a dict with channelId and portalId
            g[:] = [ch for ch in g if not (isinstance(ch, dict) and ch.get('channelId') == channelId)]

        # Add to new group if one is selected
        if group:
            if group not in channel_groups:
                channel_groups[group] = []
            
            # Add as dict with both channelId and portalId
            channel_entry = {
                'channelId': channelId,
                'portalId': portal
            }
            if channel_entry not in channel_groups[group]:
                channel_groups[group].append(channel_entry)

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
            "fallback channels": {},
            "channel groups": {},
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
                stderr=subprocess.DEVNULL,
            ) as ffmpeg_sp:
                while True:
                    chunk = ffmpeg_sp.stdout.read(1024)
                    if len(chunk) == 0:
                        if ffmpeg_sp.poll() != 0:
                            logger.info(f"Ffmpeg closed with error({ffmpeg_sp.poll()}). Moving MAC({mac}) for Portal({portalName})")
                            moveMac(portalId, mac)
                        break
                    yield chunk
        except:
            pass
        finally:
            unoccupy()
            ffmpeg_sp.kill()

    def testStream():
        timeout = int(getSettings()["ffmpeg timeout"]) * 1000000
        ffprobecmd = ["ffprobe", "-timeout", str(timeout), "-i", link]

        if proxy:
            ffprobecmd.insert(1, "-http_proxy")
            ffprobecmd.insert(2, proxy)

        with subprocess.Popen(
            ffprobecmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as ffprobe_sb:
            ffprobe_sb.communicate()
            return ffprobe_sb.returncode == 0

    def isMacFree():
        return sum(1 for i in occupied.get(portalId, []) if i["mac"] == mac) < streamsPerMac

    portal = getPortals().get(portalId)
    portalName = portal.get("name")
    url = portal.get("url")
    macs = list(portal["macs"].keys())
    streamsPerMac = int(portal.get("streams per mac"))
    proxy = portal.get("proxy")
    web = request.args.get("web")
    ip = request.remote_addr

    logger.info(f"IP({ip}) requested Portal({portalId}):Channel({channelId})")

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

        portals = getPortals()
        channelGroups = getChannelGroups()
        
        # Find which group this channel belongs to
        channelGroup = None
        for group_name, channels in channelGroups.items():
            for ch in channels:
                if isinstance(ch, dict) and ch.get('channelId') == channelId:
                    channelGroup = group_name
                    break
            if channelGroup:
                break

        if channelGroup:
            logger.info(f"Found channel in group: {channelGroup}")
            # Try all other channels in the same group
            for channel_entry in channelGroups[channelGroup]:
                if not isinstance(channel_entry, dict):
                    continue
                    
                fallbackChannelId = channel_entry['channelId']
                fallbackPortalId = channel_entry['portalId']
                
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
                                            logger.info(f"Fallback found in group {channelGroup} - using channel {fallbackChannelId} from Portal({fallbackPortalId})")
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
    else:
        logger.info(f"No free MAC for Portal({portalId}):Channel({channelId})")

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
                        # token = stb.getToken(url, mac, proxy)
                        # ids = portals[portal]["ids"][mac]
                        # stb.getProfile(url, mac, token, ids["device_id"], ids["device_id2"], ids["signature"], ids["timestamp"], proxy)
                        # stb.getProfile(url, mac, token, proxy)
                        # allChannels = stb.getAllChannels(url, mac, token, proxy)
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
        
    # Add new channels to the group
    for channel_id in channel_ids:
        channel_id = channel_id.strip()
        if channel_id:
            new_entry = {
                "channelId": channel_id,
                "portalId": portal_id
            }
            if new_entry not in channel_groups[group_name]:
                channel_groups[group_name].append(new_entry)
    
    saveChannelGroups(channel_groups)
    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]
    })

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
    channel_groups[group_name] = [
        ch for ch in channel_groups[group_name] 
        if not (isinstance(ch, dict) and 
                ch.get("channelId") == channel_id and 
                ch.get("portalId") == portal_id)
    ]
    
    saveChannelGroups(channel_groups)
    return jsonify({
        "status": "success",
        "channels": channel_groups[group_name]
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
        
    channel_groups[group_name] = []
    saveChannelGroups(channel_groups)
    
    return jsonify({"status": "success"})

if __name__ == "__main__":
    config = loadConfig()
    if "TERM_PROGRAM" in os.environ.keys() and os.environ["TERM_PROGRAM"] == "vscode":
        app.run(host="0.0.0.0", port=8001, debug=True)
    else:
        waitress.serve(app, port=8001, _quiet=True, threads=24)