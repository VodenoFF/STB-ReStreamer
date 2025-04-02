import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse
import re
import hashlib
import time

s = requests.Session()
retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
s.mount("http://", HTTPAdapter(max_retries=retries))

def generate_device_id(mac_address):
    # Example of creating a simple device ID (adjust hashing algorithm if needed)
    return hashlib.sha256(mac_address.encode()).hexdigest().upper()

def generate_signature(mac_address, token, params):
    # Create a signature using the MAC and token (adjust as per requirements)
    combined = mac_address + token + ''.join(params)
    return hashlib.sha256(combined.encode()).hexdigest().upper()


def getUrl(url, proxy=None):
    def parseResponse(url, data):
        java = data.text.replace(" ", "").replace("'", "").replace("+", "")
        try:
            pattern = re.search(r"\s*var\s*pattern.*\/(\(http.*)\/;", data.text).group(1)
            result = re.search(pattern, url)
            protocolIndex = re.search(r"this\.portal_protocol.*(\d).*;", java).group(1)
            ipIndex = re.search(r"this\.portal_ip.*(\d).*;", java).group(1)
            pathIndex = re.search(r"this\.portal_path.*(\d).*;", java).group(1)
            protocol = result.group(int(protocolIndex))
            ip = result.group(int(ipIndex))
            path = result.group(int(pathIndex))
            portalPatern = re.search(r"this\.ajax_loader=(.*\.php);", java).group(1)
            portal = (
                portalPatern.replace("this.portal_protocol", protocol)
                .replace("this.portal_ip", ip)
                .replace("this.portal_path", path)
            )
            return portal
        except:
            # If parsing fails, check if we're already at a load.php URL
            if url.endswith('load.php'):
                return url
            # Otherwise try to construct the load.php URL
            base = urlparse(url).scheme + "://" + urlparse(url).netloc
            return base + "/stalker_portal/server/load.php"

    # If the URL already ends with load.php, return it directly
    if url.endswith('load.php'):
        return url

    base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
    urls = [
        "/c/xpcom.common.js",
        "/client/xpcom.common.js",
        "/c_/xpcom.common.js",
        "/stalker_portal/c/xpcom.common.js",
        "/stalker_portal/c_/xpcom.common.js",
    ]

    proxies = {"http": proxy, "https": proxy} if proxy else None
    headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)"}

    # First try with proxy
    try:
        for i in urls:
            try:
                response = s.get(base_url + i, headers=headers, proxies=proxies)
                if response and response.status_code == 200:
                    result = parseResponse(base_url + i, response)
                    if result:
                        return result
            except:
                continue
    except:
        pass

    # Try without proxy
    try:
        for i in urls:
            try:
                response = s.get(base_url + i, headers=headers)
                if response and response.status_code == 200:
                    result = parseResponse(base_url + i, response)
                    if result:
                        return result
            except:
                continue
    except:
        pass

    # If all else fails, try to construct the load.php URL
    return base_url + "/stalker_portal/server/load.php"


def getToken(url, mac, proxy=None):
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"}
    try:
        response = s.get(
            url + "?type=stb&action=handshake&token=&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        token = response.json()["js"]["token"]
        if token:
            return token
    except:
        pass


def getProfile(url, mac, token, device_id, device_id2, signature,timestamp, proxy=None):

    # Generate device IDs
    # device_id = generate_device_id(mac_address)
    # device_id2 = device_id  # Often the same as device_id

    # # Generate signature and timestamp
    timestamp = int(time.time())
    # signature = generate_signature(mac_address, token, [str(timestamp)])
    # Construct request
    request_url = (
        f"?type=stb&action=get_profile&hd=1&ver=ImageDescription:0.2.18-r23-250;"
        f"ImageDate:Thu Sep 13 11:31:16 EEST 2018;PORTAL version:5.5.0;"
        f"API Version:JS API version:343;STB API version:146;Player Engine version:0x58c"
        f"&num_banks=2&sn=8F5EA4662E9AD&stb_type=MAG200&client_type=STB&image_version=218"
        f"&video_out=hdmi&device_id={device_id}&device_id2={device_id2}"
        f"&signature={signature}&auth_second_step=1&hw_version=1.7-BD-00"
        f"&not_valid_token=0&metrics=%7B%22mac%22%3A%22{mac.replace(':', '%3A')}%22"
        f"%2C%22sn%22%3A%228F5EA4662E9AD%22%2C%22type%22%3A%22STB%22%2C%22model%22%3A%22MAG250%22"
        f"%2C%22uid%22%3A%22%22%2C%22random%22%3A%22e19ac8911689fb4432bab570f0ec9dcada70ea3f%22%7D"
        f"&hw_version_2=e35eb542450b97c61341f7aa8208c2ec93c40966"
        f"&timestamp={timestamp}&api_signature=262&prehash=0f745136d021752337aba35d49bbb23327902654"
        f"&JsHttpRequest=1-xml"
)
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
    }
    try:
        response = s.get(
            url + request_url,
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        profile = response.json()["js"]
        if profile:
            return profile
    except:
        pass


def getExpires(url, mac, token, proxy=None):
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }
    try:
        response = s.get(
            url + "?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        expires = response.json()["js"]["phone"]
        expires2 = response.json()["js"]["end_date"]
        if expires2:
            return expires2
        if expires:
            return expires
    except:
        pass


def getAllChannels(url, mac, token, proxy=None):
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }
    try:
        response = s.get(
            url
            + "?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        channels = response.json()["js"]["data"]
        if channels:
            return channels
    except:
        pass


def getGenres(url, mac, token, proxy=None):
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }
    try:
        response = s.get(
            url + "?action=get_genres&type=itv&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        genreData = response.json()["js"]
        if genreData:
            return genreData
    except:
        pass


def getGenreNames(url, mac, token, proxy=None):
    try:
        genreData = getGenres(url, mac, token, proxy)
        genres = {}
        for i in genreData:
            gid = i["id"]
            name = i["title"]
            genres[gid] = name
        if genres:
            return genres
    except:
        pass


def getLink(url, mac, token, cmd, proxy=None):
    print(url, mac, token, cmd)
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG254; Link: WiFi",
    }
    try:
        response = s.get(
            url
            + "?type=itv&action=create_link&cmd="
            + cmd
            + "&series=0&forced_storage=0&disable_ad=0&download=0&force_ch_link_check=0&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        data = response.json()
        link = data["js"]["cmd"].split()[-1]
        if link:
            return link
    except:
        pass


def getEpg(url, mac, token, period, proxy=None):
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
        "Authorization": "Bearer " + token,
    }
    try:
        response = s.get(
            url
            + "?type=itv&action=get_epg_info&period="
            + str(period)
            + "&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
        )
        data = response.json()["js"]["data"]
        if data:
            return data
    except:
        pass

