import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse
import re
import hashlib
import time
import json
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stb')

# Custom exceptions
class StalkerPortalError(Exception):
    """Base exception for StalkerPortal errors."""
    pass

class AuthenticationError(StalkerPortalError):
    """Exception raised when authentication fails."""
    pass

class StreamCreationError(StalkerPortalError):
    """Exception raised when creating a stream link fails."""
    pass

class OrderedListError(StalkerPortalError):
    """Exception raised when fetching the ordered list fails."""
    pass

# Global session
s = requests.Session()
retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
s.mount("http://", HTTPAdapter(max_retries=retries))
s.mount("https://", HTTPAdapter(max_retries=retries))

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
    """
    Gets authentication token from the portal.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        str: Authentication token

    Raises:
        AuthenticationError: If authentication fails
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"}

    try:
        logger.debug(f"Attempting to get token for MAC: {mac}")
        response = s.get(
            url + "?type=stb&action=handshake&token=&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data and "token" in data["js"]:
                    token = data["js"]["token"]
                    if token:
                        logger.info(f"Successfully obtained token for MAC: {mac}")
                        return token
                    else:
                        logger.error(f"Empty token received for MAC: {mac}")
                        raise AuthenticationError("Empty token received from server")
                else:
                    logger.error(f"Token not found in response for MAC: {mac}")
                    raise AuthenticationError("Token not found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise AuthenticationError(f"Failed to parse authentication response: {e}")
        else:
            logger.error(f"Authentication failed with status code: {response.status_code}")
            raise AuthenticationError(f"Authentication failed with status code: {response.status_code}")
    except AuthenticationError:
        # Re-raise AuthenticationError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getToken: {e}")
        traceback.print_exc()
        raise AuthenticationError(f"Authentication failed: {e}")


def getProfile(url, mac, token, device_id, device_id2, signature, timestamp, proxy=None):
    """
    Gets user profile information from the portal.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        device_id (str): Device ID
        device_id2 (str): Secondary device ID
        signature (str): Request signature
        timestamp (int): Request timestamp
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        dict: User profile information

    Raises:
        AuthenticationError: If profile retrieval fails
    """
    # Ensure timestamp is current
    timestamp = int(time.time())

    # Construct request URL
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
        logger.debug(f"Attempting to get profile for MAC: {mac}")
        response = s.get(
            url + request_url,
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data:
                    profile = data["js"]
                    if profile:
                        logger.info(f"Successfully retrieved profile for MAC: {mac}")
                        return profile
                    else:
                        logger.error(f"Empty profile received for MAC: {mac}")
                        raise AuthenticationError("Empty profile received from server")
                else:
                    logger.error(f"Profile not found in response for MAC: {mac}")
                    raise AuthenticationError("Profile not found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise AuthenticationError(f"Failed to parse profile response: {e}")
        else:
            logger.error(f"Profile retrieval failed with status code: {response.status_code}")
            raise AuthenticationError(f"Profile retrieval failed with status code: {response.status_code}")
    except AuthenticationError:
        # Re-raise AuthenticationError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getProfile: {e}")
        traceback.print_exc()
        raise AuthenticationError(f"Profile retrieval failed: {e}")


def getExpires(url, mac, token, proxy=None):
    """
    Gets account expiration date from the portal.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        str: Account expiration date

    Raises:
        AuthenticationError: If account info retrieval fails
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        logger.debug(f"Attempting to get account expiration for MAC: {mac}")
        response = s.get(
            url + "?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data:
                    js_data = data["js"]

                    # Try to get expiration date from different fields
                    expires2 = js_data.get("end_date")
                    expires = js_data.get("phone")

                    if expires2:
                        logger.info(f"Successfully retrieved account expiration (end_date) for MAC: {mac}: {expires2}")
                        return expires2
                    elif expires:
                        logger.info(f"Successfully retrieved account expiration (phone) for MAC: {mac}: {expires}")
                        return expires
                    else:
                        logger.warning(f"No expiration date found for MAC: {mac}")
                        return None
                else:
                    logger.error(f"Account info not found in response for MAC: {mac}")
                    raise AuthenticationError("Account info not found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise AuthenticationError(f"Failed to parse account info response: {e}")
        else:
            logger.error(f"Account info retrieval failed with status code: {response.status_code}")
            raise AuthenticationError(f"Account info retrieval failed with status code: {response.status_code}")
    except AuthenticationError:
        # Re-raise AuthenticationError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getExpires: {e}")
        traceback.print_exc()
        return None


def getAllChannels(url, mac, token, proxy=None):
    """
    Gets all TV channels from the portal.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        list: List of TV channels

    Raises:
        StalkerPortalError: If channel retrieval fails
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        logger.debug(f"Attempting to get all channels for MAC: {mac}")
        response = s.get(
            url + "?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data and "data" in data["js"]:
                    channels = data["js"]["data"]
                    if channels:
                        logger.info(f"Successfully retrieved {len(channels)} channels for MAC: {mac}")
                        return channels
                    else:
                        logger.warning(f"No channels found for MAC: {mac}")
                        return []
                else:
                    logger.error(f"Channel data not found in response for MAC: {mac}")
                    raise StalkerPortalError("Channel data not found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise StalkerPortalError(f"Failed to parse channel data response: {e}")
        else:
            logger.error(f"Channel retrieval failed with status code: {response.status_code}")
            raise StalkerPortalError(f"Channel retrieval failed with status code: {response.status_code}")
    except StalkerPortalError:
        # Re-raise StalkerPortalError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getAllChannels: {e}")
        traceback.print_exc()
        return None


def getGenres(url, mac, token, proxy=None):
    """
    Gets TV channel genres from the portal.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        list: List of TV channel genres

    Raises:
        StalkerPortalError: If genre retrieval fails
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        logger.debug(f"Attempting to get genres for MAC: {mac}")
        response = s.get(
            url + "?action=get_genres&type=itv&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data:
                    genres = data["js"]
                    if genres:
                        logger.info(f"Successfully retrieved {len(genres)} genres for MAC: {mac}")
                        return genres
                    else:
                        logger.warning(f"No genres found for MAC: {mac}")
                        return []
                else:
                    logger.error(f"Genre data not found in response for MAC: {mac}")
                    raise StalkerPortalError("Genre data not found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise StalkerPortalError(f"Failed to parse genre data response: {e}")
        else:
            logger.error(f"Genre retrieval failed with status code: {response.status_code}")
            raise StalkerPortalError(f"Genre retrieval failed with status code: {response.status_code}")
    except StalkerPortalError:
        # Re-raise StalkerPortalError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getGenres: {e}")
        traceback.print_exc()
        return None


def getGenreNames(url, mac, token, proxy=None):
    """
    Gets TV channel genre names as a dictionary mapping genre IDs to names.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        dict: Dictionary mapping genre IDs to names

    Raises:
        StalkerPortalError: If genre retrieval fails
    """
    try:
        logger.debug(f"Attempting to get genre names for MAC: {mac}")
        genreData = getGenres(url, mac, token, proxy)

        if genreData:
            genres = {}
            for i in genreData:
                if isinstance(i, dict) and "id" in i and "title" in i:
                    gid = i["id"]
                    name = i["title"]
                    genres[gid] = name

            if genres:
                logger.info(f"Successfully mapped {len(genres)} genre IDs to names for MAC: {mac}")
                return genres
            else:
                logger.warning(f"No valid genre mappings found for MAC: {mac}")
                return {}
        else:
            logger.warning(f"No genre data available for MAC: {mac}")
            return {}
    except StalkerPortalError as e:
        # Re-raise StalkerPortalError to allow specific handling
        logger.error(f"StalkerPortalError in getGenreNames: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in getGenreNames: {e}")
        traceback.print_exc()
        return None


def getLink(url, mac, token, cmd, proxy=None):
    """
    Gets a direct stream link for a TV channel.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        cmd (str): Channel command ID
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        str: Direct stream URL

    Raises:
        StreamCreationError: If stream link creation fails
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG254; Link: WiFi",
    }

    try:
        logger.debug(f"Attempting to create stream link for channel {cmd} for MAC: {mac}")
        response = s.get(
            url + "?type=itv&action=create_link&cmd=" + cmd + "&series=0&forced_storage=0&disable_ad=0&download=0&force_ch_link_check=0&JsHttpRequest=1-xml",
            cookies=cookies,
            headers=headers,
            proxies=proxies,
            timeout=10  # Add timeout to avoid hanging
        )

        # Check if response is valid
        if response.status_code == 200:
            try:
                data = response.json()
                if "js" in data and "cmd" in data["js"]:
                    cmd_value = data["js"]["cmd"]
                    if cmd_value:
                        # The URL is typically the last part of the cmd string
                        link = cmd_value.split()[-1]
                        if link:
                            logger.info(f"Successfully created stream link for channel {cmd}: {link}")
                            return link
                        else:
                            logger.error(f"Empty link in cmd value for channel {cmd}")
                            raise StreamCreationError(f"Empty link in cmd value for channel {cmd}")
                    else:
                        logger.error(f"Empty cmd value for channel {cmd}")
                        raise StreamCreationError(f"Empty cmd value for channel {cmd}")
                else:
                    logger.error(f"Stream link data not found in response for channel {cmd}")
                    raise StreamCreationError(f"Stream link data not found in response for channel {cmd}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise StreamCreationError(f"Failed to parse stream link response: {e}")
        else:
            logger.error(f"Stream link creation failed with status code: {response.status_code}")
            raise StreamCreationError(f"Stream link creation failed with status code: {response.status_code}")
    except StreamCreationError:
        # Re-raise StreamCreationError to allow specific handling
        raise
    except Exception as e:
        logger.error(f"Error in getLink: {e}")
        traceback.print_exc()
        raise StreamCreationError(f"Stream link creation failed: {e}")


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


def getVodCategories(url, mac, token, proxy=None):
    """
    Fetches VOD categories from the portal API.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        list: List of VOD category dictionaries or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Try different API endpoints that might work with this portal
        api_urls = [
            # Standard format
            f"{url}?type=vod&action=get_categories&JsHttpRequest=1-xml",
            # Alternative format
            f"{url}?action=get_categories&type=vod&JsHttpRequest=1-xml"
        ]

        # Try each API URL until one works
        for api_url in api_urls:
            try:
                logger.debug(f"Trying VOD categories URL: {api_url}")
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Only try to parse as JSON if there's actual content
                    if text.strip():
                        try:
                            data = response.json()

                            # Check for different response formats
                            if "js" in data:
                                categories = data["js"]
                                if categories:
                                    # Add type field to identify as VOD categories
                                    for category in categories:
                                        if isinstance(category, dict) and not category.get("type"):
                                            category["type"] = "VOD"
                                    logger.info(f"Successfully fetched {len(categories)} VOD categories")
                                    return categories
                            else:
                                logger.warning(f"Response JSON missing 'js' key: {list(data.keys())}")
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON decode error: {json_err}")
                            continue
                    else:
                        logger.warning("Empty response received from server")
                else:
                    logger.warning(f"Error response: {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching VOD categories with URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error("All VOD category API URLs failed")
        return None
    except Exception as e:
        logger.error(f"Error in getVodCategories: {e}")
        traceback.print_exc()
        return None


def getSeriesCategories(url, mac, token, proxy=None):
    """
    Fetches Series categories from the portal API.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.

    Returns:
        list: List of Series category dictionaries or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Try different API endpoints that might work with this portal
        api_urls = [
            # Standard format for series type
            f"{url}?type=series&action=get_categories&JsHttpRequest=1-xml",
            # Alternative format with different parameter order
            f"{url}?action=get_categories&type=series&JsHttpRequest=1-xml",
            # VOD type with series filter
            f"{url}?type=vod&action=get_categories&JsHttpRequest=1-xml"
        ]

        # Try each API URL until one works
        for api_url in api_urls:
            try:
                logger.debug(f"Trying Series categories URL: {api_url}")
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Only try to parse as JSON if there's actual content
                    if text.strip():
                        try:
                            data = response.json()

                            # Check for different response formats
                            if "js" in data:
                                categories = data["js"]
                                if categories:
                                    # If this is the VOD URL, filter for Series categories
                                    if "vod" in api_url:
                                        # Filter and mark Series categories
                                        series_categories = []
                                        for category in categories:
                                            # Check different ways a category might be identified as Series
                                            is_series = False
                                            if isinstance(category, dict):
                                                # Check explicit category_type
                                                if category.get("category_type") == "Series":
                                                    is_series = True
                                                # Check title for keywords
                                                elif category.get("title") and any(keyword in category["title"].lower() for keyword in ["series", "tv", "show", "season"]):
                                                    is_series = True
                                                # Check name for keywords
                                                elif category.get("name") and any(keyword in category["name"].lower() for keyword in ["series", "tv", "show", "season"]):
                                                    is_series = True

                                                if is_series:
                                                    category["type"] = "Series"
                                                    series_categories.append(category)

                                        if series_categories:
                                            logger.info(f"Successfully fetched {len(series_categories)} Series categories from VOD endpoint")
                                            return series_categories
                                    else:
                                        # For direct series endpoints, mark all as Series
                                        for category in categories:
                                            if isinstance(category, dict):
                                                category["type"] = "Series"
                                        logger.info(f"Successfully fetched {len(categories)} Series categories")
                                        return categories
                            else:
                                logger.warning(f"Response JSON missing 'js' key: {list(data.keys())}")
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON decode error: {json_err}")
                            continue
                    else:
                        logger.warning("Empty response received from server")
                else:
                    logger.warning(f"Error response: {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Series categories with URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error("All Series category API URLs failed")
        return None
    except Exception as e:
        logger.error(f"Error in getSeriesCategories: {e}")
        traceback.print_exc()
        return None


def getOrderedList(url, mac, token, proxy=None, content_type=None, category_id=None):
    """
    Fetches VOD or Series items for a specific category.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.
        content_type (str, optional): Type of content ('vod' or 'series'). Defaults to None.
        category_id (str, optional): Category ID. Defaults to None.

    Returns:
        list: List of VOD/Series items or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Ensure content_type and category_id are valid
        if not content_type:
            content_type = "vod"  # Default to VOD if not specified
        if not category_id:
            logger.error("Cannot fetch ordered list without a category ID")
            return None  # Cannot proceed without a category ID

        # Try different API endpoints and parameters that might work with this portal
        api_urls = [
            # Standard format
            f"{url}?type={content_type}&action=get_ordered_list&category={category_id}&force_ch_link_check=0&fav=0&sortby=number&hd=0&p=1&JsHttpRequest=1-xml",
            # Alternative format with different parameter order
            f"{url}?action=get_ordered_list&type={content_type}&category={category_id}&JsHttpRequest=1-xml",
            # Simplified format
            f"{url}?type={content_type}&action=get_ordered_list&category_id={category_id}&JsHttpRequest=1-xml",
            # Format with different category parameter name
            f"{url}?type={content_type}&action=get_ordered_list&cat={category_id}&JsHttpRequest=1-xml",
            # Try with movie_id parameter (some portals use this)
            f"{url}?type={content_type}&action=get_ordered_list&movie_id={category_id}&JsHttpRequest=1-xml",
            # Try with genre parameter (some portals use this for categories)
            f"{url}?type={content_type}&action=get_ordered_list&genre={category_id}&JsHttpRequest=1-xml",
            # Try with different action name
            f"{url}?type={content_type}&action=get_data_table&category={category_id}&JsHttpRequest=1-xml",
            # Try with different action and parameter order
            f"{url}?action=get_data_table&type={content_type}&category={category_id}&JsHttpRequest=1-xml",
            # Try with different JsHttpRequest format
            f"{url}?type={content_type}&action=get_ordered_list&category={category_id}&JsHttpRequest=1-xml",
            # Try with different JsHttpRequest format (no dash)
            f"{url}?type={content_type}&action=get_ordered_list&category={category_id}&JsHttpRequest=1xml",
            # Try with different JsHttpRequest format (no value)
            f"{url}?type={content_type}&action=get_ordered_list&category={category_id}&JsHttpRequest=",
            # Try with no JsHttpRequest parameter
            f"{url}?type={content_type}&action=get_ordered_list&category={category_id}"
        ]

        # Try each API URL until one works
        for api_url in api_urls:
            logger.debug(f"Trying API URL: {api_url}")

            try:
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {response.headers}")

                # Check if response is valid
                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Check for empty or invalid responses
                    if not text or not text.strip():
                        logger.warning(f"Empty response received from server for URL: {api_url}")
                        continue

                    # Check for authorization failure
                    if "Authorization failed" in text or "Access denied" in text:
                        logger.warning(f"Authorization failed for URL: {api_url}")
                        # Signal that token refresh is needed
                        raise AuthenticationError("Authorization failed, token may have expired")

                    # Check if the response is HTML instead of JSON (common error)
                    if text.strip().startswith('<!DOCTYPE') or text.strip().startswith('<html'):
                        logger.warning(f"Received HTML instead of JSON for URL: {api_url}")
                        continue

                    # Check if the response is XML instead of JSON (some portals return XML)
                    if text.strip().startswith('<?xml') or (text.strip().startswith('<') and '>' in text.strip() and not text.strip().startswith('{')):
                        logger.warning(f"Received XML instead of JSON for URL: {api_url}")
                        # TODO: Add XML parsing support if needed
                        continue

                    # Check Content-Type header
                    content_type_header = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type_header and not ('application/json' in content_type_header or 'text/javascript' in content_type_header):
                        logger.warning(f"Received Content-Type '{content_type_header}' instead of JSON for URL: {api_url}")
                        # Some portals return JSON with incorrect Content-Type, so we'll still try to parse it

                    # Try to parse as JSON
                    try:
                        data = response.json()

                        # Check for different response formats
                        if "js" in data:
                            if "data" in data["js"]:
                                items = data["js"]["data"]
                                if items:
                                    logger.info(f"Successfully fetched {len(items)} items for {content_type} category {category_id}")
                                    # Add content_type to each item for easier identification
                                    for item in items:
                                        if isinstance(item, dict):
                                            item["content_type"] = content_type
                                    return items
                                else:
                                    logger.warning(f"Empty data array in response for {content_type} category {category_id}")
                            else:
                                # Some portals might return data directly in js without a data key
                                js_data = data["js"]
                                if isinstance(js_data, list):
                                    logger.info(f"Successfully fetched {len(js_data)} items for {content_type} category {category_id} (direct js list)")
                                    # Add content_type to each item for easier identification
                                    for item in js_data:
                                        if isinstance(item, dict):
                                            item["content_type"] = content_type
                                    return js_data
                                elif isinstance(js_data, dict) and not js_data.get("error"):
                                    # Some portals might return a single item as a dict
                                    logger.info(f"Successfully fetched 1 item for {content_type} category {category_id} (direct js dict)")
                                    js_data["content_type"] = content_type
                                    return [js_data]
                                else:
                                    logger.warning(f"No data found in js object: {list(js_data.keys()) if isinstance(js_data, dict) else type(js_data)}")
                        elif "data" in data:
                            # Some portals might return data directly in the root
                            items = data["data"]
                            if items:
                                logger.info(f"Successfully fetched {len(items)} items for {content_type} category {category_id} (direct data)")
                                # Add content_type to each item for easier identification
                                for item in items:
                                    if isinstance(item, dict):
                                        item["content_type"] = content_type
                                return items
                            else:
                                logger.warning(f"Empty data array in root response for {content_type} category {category_id}")
                        elif isinstance(data, list):
                            # Some portals might return a list directly
                            logger.info(f"Successfully fetched {len(data)} items for {content_type} category {category_id} (direct list)")
                            # Add content_type to each item for easier identification
                            for item in data:
                                if isinstance(item, dict):
                                    item["content_type"] = content_type
                            return data
                        else:
                            logger.warning(f"Response JSON has unexpected format: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON decode error: {json_err}")
                        # Log more details about the response
                        logger.error(f"Response content causing JSON error: {text}")

                        # Try to clean up the response and parse it again
                        # Some portals return malformed JSON with extra characters
                        try:
                            # Try to find a JSON object in the response
                            if '{' in text and '}' in text:
                                start = text.find('{')
                                end = text.rfind('}')
                                if start < end:
                                    cleaned_text = text[start:end+1]
                                    logger.debug(f"Attempting to parse cleaned JSON: {cleaned_text[:200]}")
                                    data = json.loads(cleaned_text)
                                    logger.info(f"Successfully parsed cleaned JSON for {content_type} category {category_id}")

                                    # Process the data as a direct object
                                    if isinstance(data, dict):
                                        # Add content_type to the item
                                        data["content_type"] = content_type
                                        return [data]
                                    elif isinstance(data, list):
                                        # Add content_type to each item
                                        for item in data:
                                            if isinstance(item, dict):
                                                item["content_type"] = content_type
                                        return data
                            # If we get here, cleaning didn't work
                            logger.warning("Failed to clean and parse JSON response")
                        except Exception as e:
                            logger.error(f"Error cleaning JSON: {e}")

                        # Continue to the next URL if this one didn't work
                        continue
                else:
                    logger.warning(f"Error response: {response.status_code}")
                    # Continue to the next URL if this one didn't work
                    continue
            except Exception as e:
                logger.error(f"Error with API URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error(f"All API URLs failed for {content_type} category {category_id}")
        raise OrderedListError(f"Failed to fetch items for {content_type} category {category_id}")
    except AuthenticationError as e:
        # Token has expired, try to refresh it and retry once
        logger.warning(f"Authentication error in getOrderedList: {e}. Attempting to refresh token.")
        try:
            # Get a new token
            new_token = getToken(url, mac, proxy)
            if new_token:
                logger.info(f"Successfully refreshed token for MAC: {mac}")
                # Retry with the new token
                return getOrderedList(url, mac, new_token, proxy, content_type, category_id)
            else:
                logger.error("Failed to refresh token")
                raise OrderedListError(f"Failed to refresh token for {content_type} category {category_id}")
        except Exception as refresh_error:
            logger.error(f"Error refreshing token: {refresh_error}")
            traceback.print_exc()
            raise OrderedListError(f"Failed to refresh token: {refresh_error}")
    except OrderedListError as e:
        # Re-raise OrderedListError to allow specific handling
        logger.error(f"OrderedListError: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in getOrderedList: {e}")
        traceback.print_exc()
        return None


def getSeriesSeasons(url, mac, token, proxy=None, series_id=None):
    """
    Fetches seasons for a specific series.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.
        series_id (str, optional): Series ID. Defaults to None.

    Returns:
        list: List of seasons or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Ensure series_id is valid
        if not series_id:
            logger.error("Cannot fetch seasons without a series ID")
            return None  # Cannot proceed without a series ID

        # Try different API endpoints and parameters that might work with this portal
        api_urls = [
            # Standard format
            f"{url}?type=series&action=get_seasons&series_id={series_id}&JsHttpRequest=1-xml",
            # Alternative format with different parameter order
            f"{url}?action=get_seasons&type=series&series_id={series_id}&JsHttpRequest=1-xml",
            # Format with different parameter name
            f"{url}?type=series&action=get_seasons&id={series_id}&JsHttpRequest=1-xml",
            # Try VOD type as fallback
            f"{url}?type=vod&action=get_seasons&series_id={series_id}&JsHttpRequest=1-xml",
            # Try get_ordered_list with movie_id (some portals use this approach)
            f"{url}?type=vod&action=get_ordered_list&movie_id={series_id}&season_id=0&episode_id=0&JsHttpRequest=1-xml",
            # Try get_ordered_list with video_id (some portals use this approach)
            f"{url}?type=vod&action=get_ordered_list&video_id={series_id}&season_id=0&episode_id=0&JsHttpRequest=1-xml"
        ]

        # Try each API URL until one works
        for api_url in api_urls:
            logger.debug(f"Trying API URL for seasons: {api_url}")

            try:
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")

                # Check if response is valid
                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Check for empty or invalid responses
                    if not text or not text.strip():
                        logger.warning(f"Empty response received from server for URL: {api_url}")
                        continue

                    # Check for authorization failure
                    if "Authorization failed" in text or "Access denied" in text:
                        logger.warning(f"Authorization failed for URL: {api_url}")
                        # Signal that token refresh is needed
                        raise AuthenticationError("Authorization failed, token may have expired")

                    # Only try to parse as JSON if there's actual content
                    if text.strip():
                        try:
                            data = response.json()

                            # Check for different response formats
                            if "js" in data:
                                if "data" in data["js"]:
                                    seasons = data["js"]["data"]
                                    if seasons:
                                        # Process seasons to ensure they have the right format
                                        processed_seasons = []
                                        for season in seasons:
                                            if isinstance(season, dict):
                                                # Check if this is actually a season
                                                is_season = False

                                                # Check explicit is_season flag
                                                if season.get("is_season") in [True, 1, "1", "true", "True"]:
                                                    is_season = True
                                                # Check name for season indicators
                                                elif season.get("name") and ("season" in season["name"].lower() or "сезон" in season["name"].lower()):
                                                    is_season = True
                                                # Check title for season indicators
                                                elif season.get("title") and ("season" in season["title"].lower() or "сезон" in season["title"].lower()):
                                                    is_season = True
                                                # If it has season_id or season_number, it's likely a season
                                                elif season.get("season_id") or season.get("season_number"):
                                                    is_season = True

                                                if is_season:
                                                    # Ensure it has the necessary fields
                                                    season["item_type"] = "season"
                                                    # Make sure it has a season_id
                                                    if not season.get("season_id"):
                                                        season["season_id"] = season.get("id")
                                                    # Make sure it has a movie_id (parent series id)
                                                    if not season.get("movie_id"):
                                                        season["movie_id"] = series_id

                                                    processed_seasons.append(season)

                                        if processed_seasons:
                                            logger.info(f"Successfully fetched {len(processed_seasons)} seasons for series {series_id}")
                                            return processed_seasons
                                        else:
                                            logger.warning(f"No valid seasons found in data for series {series_id}")
                                    else:
                                        logger.warning(f"Empty data array in response for series {series_id}")
                                else:
                                    # Some portals might return data directly in js without a data key
                                    js_data = data["js"]
                                    if isinstance(js_data, list):
                                        # Process seasons to ensure they have the right format
                                        processed_seasons = []
                                        for season in js_data:
                                            if isinstance(season, dict):
                                                # Check if this is actually a season (similar logic as above)
                                                is_season = False

                                                # Check explicit is_season flag
                                                if season.get("is_season") in [True, 1, "1", "true", "True"]:
                                                    is_season = True
                                                # Check name for season indicators
                                                elif season.get("name") and ("season" in season["name"].lower() or "сезон" in season["name"].lower()):
                                                    is_season = True
                                                # Check title for season indicators
                                                elif season.get("title") and ("season" in season["title"].lower() or "сезон" in season["title"].lower()):
                                                    is_season = True
                                                # If it has season_id or season_number, it's likely a season
                                                elif season.get("season_id") or season.get("season_number"):
                                                    is_season = True

                                                if is_season:
                                                    # Ensure it has the necessary fields
                                                    season["item_type"] = "season"
                                                    # Make sure it has a season_id
                                                    if not season.get("season_id"):
                                                        season["season_id"] = season.get("id")
                                                    # Make sure it has a movie_id (parent series id)
                                                    if not season.get("movie_id"):
                                                        season["movie_id"] = series_id

                                                    processed_seasons.append(season)

                                        if processed_seasons:
                                            logger.info(f"Successfully fetched {len(processed_seasons)} seasons for series {series_id} (direct js list)")
                                            return processed_seasons
                                        else:
                                            logger.warning(f"No valid seasons found in js list for series {series_id}")
                                    elif isinstance(js_data, dict) and not js_data.get("error"):
                                        # Some portals might return a single season as a dict
                                        # Check if this is actually a season (similar logic as above)
                                        is_season = False

                                        # Check explicit is_season flag
                                        if js_data.get("is_season") in [True, 1, "1", "true", "True"]:
                                            is_season = True
                                        # Check name for season indicators
                                        elif js_data.get("name") and ("season" in js_data["name"].lower() or "сезон" in js_data["name"].lower()):
                                            is_season = True
                                        # Check title for season indicators
                                        elif js_data.get("title") and ("season" in js_data["title"].lower() or "сезон" in js_data["title"].lower()):
                                            is_season = True
                                        # If it has season_id or season_number, it's likely a season
                                        elif js_data.get("season_id") or js_data.get("season_number"):
                                            is_season = True

                                        if is_season:
                                            # Ensure it has the necessary fields
                                            js_data["item_type"] = "season"
                                            # Make sure it has a season_id
                                            if not js_data.get("season_id"):
                                                js_data["season_id"] = js_data.get("id")
                                            # Make sure it has a movie_id (parent series id)
                                            if not js_data.get("movie_id"):
                                                js_data["movie_id"] = series_id

                                            logger.info(f"Successfully fetched 1 season for series {series_id} (direct js dict)")
                                            return [js_data]
                                        else:
                                            logger.warning(f"No valid season found in js dict for series {series_id}")
                                    else:
                                        logger.warning(f"No data found in js object: {list(js_data.keys()) if isinstance(js_data, dict) else type(js_data)}")
                            elif "data" in data:
                                # Some portals might return data directly in the root
                                seasons = data["data"]
                                if seasons and isinstance(seasons, list):
                                    # Process seasons (similar logic as above)
                                    processed_seasons = []
                                    for season in seasons:
                                        if isinstance(season, dict):
                                            # Check if this is actually a season
                                            is_season = False

                                            # Check explicit is_season flag
                                            if season.get("is_season") in [True, 1, "1", "true", "True"]:
                                                is_season = True
                                            # Check name for season indicators
                                            elif season.get("name") and ("season" in season["name"].lower() or "сезон" in season["name"].lower()):
                                                is_season = True
                                            # Check title for season indicators
                                            elif season.get("title") and ("season" in season["title"].lower() or "сезон" in season["title"].lower()):
                                                is_season = True
                                            # If it has season_id or season_number, it's likely a season
                                            elif season.get("season_id") or season.get("season_number"):
                                                is_season = True

                                            if is_season:
                                                # Ensure it has the necessary fields
                                                season["item_type"] = "season"
                                                # Make sure it has a season_id
                                                if not season.get("season_id"):
                                                    season["season_id"] = season.get("id")
                                                # Make sure it has a movie_id (parent series id)
                                                if not season.get("movie_id"):
                                                    season["movie_id"] = series_id

                                                processed_seasons.append(season)

                                    if processed_seasons:
                                        logger.info(f"Successfully fetched {len(processed_seasons)} seasons for series {series_id} (direct data)")
                                        return processed_seasons
                                    else:
                                        logger.warning(f"No valid seasons found in data array for series {series_id}")
                                else:
                                    logger.warning(f"Empty or invalid data array in root response for series {series_id}")
                            elif isinstance(data, list):
                                # Some portals might return a list directly
                                # Process seasons (similar logic as above)
                                processed_seasons = []
                                for season in data:
                                    if isinstance(season, dict):
                                        # Check if this is actually a season
                                        is_season = False

                                        # Check explicit is_season flag
                                        if season.get("is_season") in [True, 1, "1", "true", "True"]:
                                            is_season = True
                                        # Check name for season indicators
                                        elif season.get("name") and ("season" in season["name"].lower() or "сезон" in season["name"].lower()):
                                            is_season = True
                                        # Check title for season indicators
                                        elif season.get("title") and ("season" in season["title"].lower() or "сезон" in season["title"].lower()):
                                            is_season = True
                                        # If it has season_id or season_number, it's likely a season
                                        elif season.get("season_id") or season.get("season_number"):
                                            is_season = True

                                        if is_season:
                                            # Ensure it has the necessary fields
                                            season["item_type"] = "season"
                                            # Make sure it has a season_id
                                            if not season.get("season_id"):
                                                season["season_id"] = season.get("id")
                                            # Make sure it has a movie_id (parent series id)
                                            if not season.get("movie_id"):
                                                season["movie_id"] = series_id

                                            processed_seasons.append(season)

                                if processed_seasons:
                                    logger.info(f"Successfully fetched {len(processed_seasons)} seasons for series {series_id} (direct list)")
                                    return processed_seasons
                                else:
                                    logger.warning(f"No valid seasons found in direct list for series {series_id}")
                            else:
                                logger.warning(f"Response JSON has unexpected format: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                                # Continue to the next URL if this one didn't work
                                continue
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON decode error: {json_err}")
                            # Continue to the next URL if this one didn't work
                            continue
                    else:
                        logger.warning("Empty response received from server")
                        # Continue to the next URL if this one didn't work
                        continue
                else:
                    logger.warning(f"Error response: {response.status_code}")
                    # Continue to the next URL if this one didn't work
                    continue
            except Exception as e:
                logger.error(f"Error with API URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error(f"All API URLs failed for series {series_id}")
        return None
    except AuthenticationError as e:
        # Token has expired, try to refresh it and retry once
        logger.warning(f"Authentication error in getSeriesSeasons: {e}. Attempting to refresh token.")
        try:
            # Get a new token
            new_token = getToken(url, mac, proxy)
            if new_token:
                logger.info(f"Successfully refreshed token for MAC: {mac}")
                # Retry with the new token
                return getSeriesSeasons(url, mac, new_token, proxy, series_id)
            else:
                logger.error("Failed to refresh token")
                return None
        except Exception as refresh_error:
            logger.error(f"Error refreshing token: {refresh_error}")
            traceback.print_exc()
            return None
    except Exception as e:
        logger.error(f"Error in getSeriesSeasons: {e}")
        traceback.print_exc()
        return None


def getSeasonEpisodes(url, mac, token, proxy=None, series_id=None, season_id=None):
    """
    Fetches episodes for a specific season of a series.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        proxy (str, optional): Proxy URL. Defaults to None.
        series_id (str, optional): Series ID. Defaults to None.
        season_id (str, optional): Season ID. Defaults to None.

    Returns:
        list: List of episodes or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Ensure series_id and season_id are valid
        if not series_id or not season_id:
            logger.error("Cannot fetch episodes without series_id and season_id")
            return None  # Cannot proceed without series ID and season ID

        # Try different API endpoints and parameters that might work with this portal
        api_urls = [
            # Standard format
            f"{url}?type=series&action=get_ordered_list&series_id={series_id}&season_id={season_id}&episode_id=all&JsHttpRequest=1-xml",
            # Alternative format with different parameter order
            f"{url}?action=get_ordered_list&type=series&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml",
            # Format with different parameter names
            f"{url}?type=series&action=get_episodes&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml",
            # Try VOD type as fallback
            f"{url}?type=vod&action=get_ordered_list&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml",
            # Try with movie_id and season_id
            f"{url}?type=vod&action=get_ordered_list&movie_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml",
            # Try with video_id and season_id
            f"{url}?type=vod&action=get_ordered_list&video_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml"
        ]

        # Try each API URL until one works
        for api_url in api_urls:
            logger.debug(f"Trying API URL for episodes: {api_url}")

            try:
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")

                # Check if response is valid
                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Only try to parse as JSON if there's actual content
                    if text.strip():
                        try:
                            data = response.json()

                            # Check for different response formats
                            if "js" in data:
                                if "data" in data["js"]:
                                    episodes = data["js"]["data"]
                                    if episodes:
                                        # Process episodes to ensure they have the right format
                                        processed_episodes = []
                                        for episode in episodes:
                                            if isinstance(episode, dict):
                                                # Check if this is actually an episode (not a season)
                                                is_episode = True

                                                # Skip if it's explicitly marked as a season
                                                if episode.get("is_season") in [True, 1, "1", "true", "True"]:
                                                    is_episode = False

                                                if is_episode:
                                                    # Ensure it has the necessary fields
                                                    episode["item_type"] = "episode"
                                                    # Make sure it has an episode_id
                                                    if not episode.get("episode_id"):
                                                        episode["episode_id"] = episode.get("id")
                                                    # Make sure it has a season_id
                                                    if not episode.get("season_id"):
                                                        episode["season_id"] = season_id
                                                    # Make sure it has a movie_id (parent series id)
                                                    if not episode.get("movie_id"):
                                                        episode["movie_id"] = series_id

                                                    processed_episodes.append(episode)

                                        if processed_episodes:
                                            logger.info(f"Successfully fetched {len(processed_episodes)} episodes for series {series_id}, season {season_id}")
                                            return processed_episodes
                                        else:
                                            logger.warning(f"No valid episodes found in data for series {series_id}, season {season_id}")
                                    else:
                                        logger.warning(f"Empty data array in response for series {series_id}, season {season_id}")
                                else:
                                    # Some portals might return data directly in js without a data key
                                    js_data = data["js"]
                                    if isinstance(js_data, list):
                                        # Process episodes (similar logic as above)
                                        processed_episodes = []
                                        for episode in js_data:
                                            if isinstance(episode, dict):
                                                # Check if this is actually an episode (not a season)
                                                is_episode = True

                                                # Skip if it's explicitly marked as a season
                                                if episode.get("is_season") in [True, 1, "1", "true", "True"]:
                                                    is_episode = False

                                                if is_episode:
                                                    # Ensure it has the necessary fields
                                                    episode["item_type"] = "episode"
                                                    # Make sure it has an episode_id
                                                    if not episode.get("episode_id"):
                                                        episode["episode_id"] = episode.get("id")
                                                    # Make sure it has a season_id
                                                    if not episode.get("season_id"):
                                                        episode["season_id"] = season_id
                                                    # Make sure it has a movie_id (parent series id)
                                                    if not episode.get("movie_id"):
                                                        episode["movie_id"] = series_id

                                                    processed_episodes.append(episode)

                                        if processed_episodes:
                                            logger.info(f"Successfully fetched {len(processed_episodes)} episodes for series {series_id}, season {season_id} (direct js list)")
                                            return processed_episodes
                                        else:
                                            logger.warning(f"No valid episodes found in js list for series {series_id}, season {season_id}")
                                    elif isinstance(js_data, dict) and not js_data.get("error"):
                                        # Some portals might return a single episode as a dict
                                        # Check if this is actually an episode (not a season)
                                        is_episode = True

                                        # Skip if it's explicitly marked as a season
                                        if js_data.get("is_season") in [True, 1, "1", "true", "True"]:
                                            is_episode = False

                                        if is_episode:
                                            # Ensure it has the necessary fields
                                            js_data["item_type"] = "episode"
                                            # Make sure it has an episode_id
                                            if not js_data.get("episode_id"):
                                                js_data["episode_id"] = js_data.get("id")
                                            # Make sure it has a season_id
                                            if not js_data.get("season_id"):
                                                js_data["season_id"] = season_id
                                            # Make sure it has a movie_id (parent series id)
                                            if not js_data.get("movie_id"):
                                                js_data["movie_id"] = series_id

                                            logger.info(f"Successfully fetched 1 episode for series {series_id}, season {season_id} (direct js dict)")
                                            return [js_data]
                                        else:
                                            logger.warning(f"No valid episode found in js dict for series {series_id}, season {season_id}")
                                    else:
                                        logger.warning(f"No data found in js object: {list(js_data.keys()) if isinstance(js_data, dict) else type(js_data)}")
                            elif "data" in data:
                                # Some portals might return data directly in the root
                                episodes = data["data"]
                                if episodes and isinstance(episodes, list):
                                    # Process episodes (similar logic as above)
                                    processed_episodes = []
                                    for episode in episodes:
                                        if isinstance(episode, dict):
                                            # Check if this is actually an episode (not a season)
                                            is_episode = True

                                            # Skip if it's explicitly marked as a season
                                            if episode.get("is_season") in [True, 1, "1", "true", "True"]:
                                                is_episode = False

                                            if is_episode:
                                                # Ensure it has the necessary fields
                                                episode["item_type"] = "episode"
                                                # Make sure it has an episode_id
                                                if not episode.get("episode_id"):
                                                    episode["episode_id"] = episode.get("id")
                                                # Make sure it has a season_id
                                                if not episode.get("season_id"):
                                                    episode["season_id"] = season_id
                                                # Make sure it has a movie_id (parent series id)
                                                if not episode.get("movie_id"):
                                                    episode["movie_id"] = series_id

                                                processed_episodes.append(episode)

                                    if processed_episodes:
                                        logger.info(f"Successfully fetched {len(processed_episodes)} episodes for series {series_id}, season {season_id} (direct data)")
                                        return processed_episodes
                                    else:
                                        logger.warning(f"No valid episodes found in data array for series {series_id}, season {season_id}")
                                else:
                                    logger.warning(f"Empty or invalid data array in root response for series {series_id}, season {season_id}")
                            elif isinstance(data, list):
                                # Some portals might return a list directly
                                # Process episodes (similar logic as above)
                                processed_episodes = []
                                for episode in data:
                                    if isinstance(episode, dict):
                                        # Check if this is actually an episode (not a season)
                                        is_episode = True

                                        # Skip if it's explicitly marked as a season
                                        if episode.get("is_season") in [True, 1, "1", "true", "True"]:
                                            is_episode = False

                                        if is_episode:
                                            # Ensure it has the necessary fields
                                            episode["item_type"] = "episode"
                                            # Make sure it has an episode_id
                                            if not episode.get("episode_id"):
                                                episode["episode_id"] = episode.get("id")
                                            # Make sure it has a season_id
                                            if not episode.get("season_id"):
                                                episode["season_id"] = season_id
                                            # Make sure it has a movie_id (parent series id)
                                            if not episode.get("movie_id"):
                                                episode["movie_id"] = series_id

                                            processed_episodes.append(episode)

                                if processed_episodes:
                                    logger.info(f"Successfully fetched {len(processed_episodes)} episodes for series {series_id}, season {season_id} (direct list)")
                                    return processed_episodes
                                else:
                                    logger.warning(f"No valid episodes found in direct list for series {series_id}, season {season_id}")
                            else:
                                logger.warning(f"Response JSON has unexpected format: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                                # Continue to the next URL if this one didn't work
                                continue
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON decode error: {json_err}")
                            # Continue to the next URL if this one didn't work
                            continue
                    else:
                        logger.warning("Empty response received from server")
                        # Continue to the next URL if this one didn't work
                        continue
                else:
                    logger.warning(f"Error response: {response.status_code}")
                    # Continue to the next URL if this one didn't work
                    continue
            except Exception as e:
                logger.error(f"Error with API URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error(f"All API URLs failed for series {series_id}, season {season_id}")
        return None
    except Exception as e:
        logger.error(f"Error in getSeasonEpisodes: {e}")
        traceback.print_exc()
        return None


def getVodSeriesLink(url, mac, token, item_id, content_type, series_info=None, proxy=None):
    """
    Gets the direct stream link for a VOD item or series episode.

    Args:
        url (str): Portal URL
        mac (str): MAC address
        token (str): Authentication token
        item_id (str): VOD item ID or episode ID
        content_type (str): Type of content ('vod' or 'episode')
        series_info (dict, optional): Series information for episodes
        proxy (str, optional): Proxy URL

    Returns:
        str: Direct stream URL or None if failed
    """
    proxies = {"http": proxy, "https": proxy}
    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/Paris"}
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Authorization": "Bearer " + token,
        "X-User-Agent": "Model: MAG250; Link: WiFi",
    }

    try:
        # Try different API endpoints and parameters that might work with this portal
        api_urls = []

        if content_type == "vod":
            # Standard format for VOD
            api_urls.append(f"{url}?type=vod&action=create_link&cmd={item_id}&JsHttpRequest=1-xml")
            # Alternative format with different parameter order
            api_urls.append(f"{url}?action=create_link&type=vod&cmd={item_id}&JsHttpRequest=1-xml")
            # Try with file_ prefix (some portals use this)
            api_urls.append(f"{url}?type=vod&action=create_link&cmd=/media/file_{item_id}.mpg&JsHttpRequest=1-xml")
        elif content_type == "episode":
            # For episodes, we need the series_id and season_id
            if not series_info:
                logger.error("Error: series_info is required for episode links")
                return None

            # Extract series_id and season_id from series_info
            series_id = series_info.get("id") or series_info.get("movie_id") or series_info.get("series_id")
            season_id = series_info.get("season_id")
            episode_id = item_id

            if not series_id or not season_id:
                logger.error("Error: series_id and season_id are required for episode links")
                return None

            # Standard format for episodes
            api_urls.append(f"{url}?type=vod&action=create_link&cmd={episode_id}&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml")
            # Alternative format with different parameter order
            api_urls.append(f"{url}?action=create_link&type=vod&cmd={episode_id}&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml")
            # Try with movie_id instead of series_id
            api_urls.append(f"{url}?type=vod&action=create_link&cmd={episode_id}&movie_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml")
            # Try with file_ prefix (some portals use this)
            api_urls.append(f"{url}?type=vod&action=create_link&cmd=/media/file_{episode_id}.mpg&series_id={series_id}&season_id={season_id}&JsHttpRequest=1-xml")
        else:
            logger.error(f"Error: Unsupported content type: {content_type}")
            return None

        # Try each API URL until one works
        for api_url in api_urls:
            logger.debug(f"Trying API URL for stream link: {api_url}")

            try:
                response = s.get(
                    api_url,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxies,
                    timeout=10  # Add timeout to avoid hanging
                )

                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")

                # Check if response is valid
                if response.status_code == 200:
                    # Get the raw text first for debugging
                    text = response.text
                    logger.debug(f"Response text (first 200 chars): {text[:200]}")

                    # Only try to parse as JSON if there's actual content
                    if text.strip():
                        try:
                            data = response.json()

                            # Check for different response formats
                            if "js" in data:
                                js_data = data["js"]

                                # Try to get the stream URL from different fields
                                stream_url = None

                                # Check for direct URL field
                                if "url" in js_data and js_data["url"]:
                                    stream_url = js_data["url"]
                                    logger.debug(f"Found stream URL in 'url' field: {stream_url}")
                                # Check for cmd field (common in many portals)
                                elif "cmd" in js_data and js_data["cmd"]:
                                    cmd = js_data["cmd"]
                                    logger.debug(f"Found cmd: {cmd}")

                                    # Handle ffmpeg prefix if present
                                    if cmd.lower().startswith("ffmpeg "):
                                        stream_url = cmd[7:].strip()  # Remove "ffmpeg " prefix
                                        logger.debug(f"Removed ffmpeg prefix, stream URL: {stream_url}")
                                    else:
                                        # The URL is typically the last part of the cmd string
                                        parts = cmd.split()
                                        if parts:
                                            stream_url = parts[-1]
                                            logger.debug(f"Extracted stream URL from cmd parts: {stream_url}")

                                # If we found a stream URL, validate and return it
                                if stream_url:
                                    # Check if it's a valid URL
                                    if stream_url.startswith("http://") or stream_url.startswith("https://") or stream_url.startswith("rtmp://") or stream_url.startswith("rtsp://"):
                                        logger.info(f"Successfully created stream link for {content_type} {item_id}: {stream_url}")
                                        return stream_url
                                    else:
                                        # If it's not a full URL, try to construct it using stream_base_url
                                        # Extract base URL from portal URL
                                        parsed_url = urlparse(url)
                                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                                        # Ensure stream_url starts with a slash if it's a path
                                        if not stream_url.startswith("/"):
                                            stream_url = "/" + stream_url

                                        full_url = base_url + stream_url
                                        logger.info(f"Constructed full stream URL: {full_url}")
                                        return full_url
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON decode error: {json_err}")
                            # Continue to the next URL if this one didn't work
                            continue
                    else:
                        logger.warning("Empty response received from server")
                        # Continue to the next URL if this one didn't work
                        continue
                else:
                    logger.warning(f"Error response: {response.status_code}")
                    # Continue to the next URL if this one didn't work
                    continue
            except Exception as e:
                logger.error(f"Error with API URL {api_url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error(f"All API URLs failed for {content_type} {item_id}")
        raise StreamCreationError(f"Failed to create stream link for {content_type} {item_id}")
    except StreamCreationError as e:
        # Re-raise StreamCreationError to allow specific handling
        logger.error(f"StreamCreationError: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in getVodSeriesLink: {e}")
        traceback.print_exc()
        return None

