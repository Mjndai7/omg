#!/usr/bin/env python3
import requests
import json
import logging
import sys
import re
import os
import urllib.request
import time

# Setup logging to Docker-compatible path
def setup_logging():
    logging.basicConfig(
        filename="/app/channel_processing.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

# Retry decorator for resilience
def retry_on_failure(max_retries=3, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.warning(f"Attempt {attempt + 1}/{max_retries} failed in {func.__name__}: {e}")
                    if attempt + 1 == max_retries:
                        logging.error(f"Max retries reached for {func.__name__}")
                        return None
                    time.sleep(delay)
        return wrapper
    return decorator

# Fetch Vavoo authentication signature
@retry_on_failure(max_retries=3, delay=2)
def get_auth_signature():
    headers = {
        "user-agent": "okhttp/4.11.0",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }

    data = {
        "token": "8Us2TfjeOFrzqFFTEjL3E5KfdAWGa5PV3wQe60uK4BmzlkJRMYFu0ufaM_eeDXKS2U04XUuhbDTgGRJrJARUwzDyCcRToXhW5AcDekfFMfwNUjuieeQ1uzeDB9YWyBL2cn5Al3L3gTnF8Vk1t7rPwkBob0swvxA",
        "reason": "player.enter",
        "locale": "en",
        "theme": "dark",
        "metadata": {
            "device": {"type": "Handset", "brand": "google", "model": "Nexus 5", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"},
            "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"], "host": "android"},
            "app": {"platform": "android", "version": "3.0.2", "buildId": "288045000", "engine": "jsc", "signatures": ["09f4e07040149486e541a1cb34000b6e12527265252fa2178dfe2bd1af6b815a"], "installer": "com.android.secex"},
            "version": {"package": "tv.vavoo.app", "binary": "3.0.2", "js": "3.1.4"}
        },
        "appFocusTime": 27229,
        "playerActive": True,
        "playDuration": 0,
        "devMode": False,
        "hasAddon": True,
        "castConnected": False,
        "package": "tv.vavoo.app",
        "version": "3.1.4",
        "process": "app",
        "firstAppStart": 1728674705639,
        "lastAppStart": 1728674705639,
        "ipLocation": "",
        "adblockEnabled": True,
        "proxy": {"supported": ["ss"], "engine": "ss", "enabled": False, "autoServer": True, "id": "ca-bhs"},
        "iap": {"supported": False}
    }

    response = requests.post("https://www.vavoo.tv/api/app/ping", json=data, headers=headers, timeout=10)
    response.raise_for_status()
    sig = response.json().get("addonSig")
    logging.info("Authentication signature obtained")
    return sig

# Fetch Vavoo channels
@retry_on_failure(max_retries=3, delay=2)
def get_channel_list(signature):
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "MediaHubMX/2",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "mediahubmx-signature": signature
    }

    cursor = 0
    all_items = []

    while True:
        data = {
            "language": "en",
            "region": "WW",
            "catalogId": "vto-iptv",
            "id": "vto-iptv",
            "adult": False,
            "search": "",
            "sort": "name",
            "filter": {},
            "cursor": cursor,
            "clientVersion": "3.0.2"
        }

        response = requests.post("https://vavoo.to/vto-cluster/mediahubmx-catalog.json", json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        items = result.get("items", [])
        if not items:
            break
        all_items.extend(items)
        cursor += len(items)
        logging.info(f"Fetched {len(items)} channels at cursor {cursor}")
    return {"items": all_items}

# Resolver for Vavoo URLs
@retry_on_failure(max_retries=2, delay=1)
def resolve_url(url, signature):
    if not url.startswith("https://vavoo.to/"):
        return url

    headers = {
        "User-Agent": "MediaHubMX/2",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "mediahubmx-signature": signature
    }

    resolve_url = "https://vavoo.to/vto-cluster/mediahubmx-resolve.json"
    try:
        response = requests.post(resolve_url, json={"url": url}, headers=headers, timeout=5)
        response.raise_for_status()
        result = response.json()
        resolved_url = result.get("stream_url", url)
        logging.info(f"Resolved URL {url} to {resolved_url}")
        return resolved_url
    except Exception as e:
        logging.warning(f"Failed to resolve URL {url}: {e}")
        try:
            response = requests.head(url, headers={"User-Agent": "MediaHubMX/2"}, allow_redirects=True, timeout=5)
            resolved_url = response.url if response.status_code == 200 else url
            logging.info(f"Fallback resolved URL {url} to {resolved_url}")
            return resolved_url
        except Exception:
            logging.warning(f"Fallback resolution failed for {url}, using original")
            return url

# Parse M3U fallback
@retry_on_failure(max_retries=2, delay=1)
def parse_m3u_file(url, temp_dir="/app/temp"):
    os.makedirs(temp_dir, exist_ok=True)
    filename = os.path.join(temp_dir, "247worldold.m3u8")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        logging.info(f"Downloaded M3U: {url} to {filename}")

        channels = []
        current_channel = {}
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    parts = line.split(',', 1)
                    if len(parts) > 1:
                        attrs = parts[0].replace("#EXTINF:", "").strip()
                        name = parts[1].strip()
                        current_channel = {"name": name}
                        for attr in attrs.split():
                            if attr.startswith('tvg-id='):
                                current_channel["tvg-id"] = attr.split('=')[1].strip('"')
                            elif attr.startswith('tvg-name='):
                                current_channel["tvg-name"] = attr.split('=')[1].strip('"')
                            elif attr.startswith('tvg-logo='):
                                current_channel["tvg-logo"] = attr.split('=')[1].strip('"')
                            elif attr.startswith('group-title='):
                                current_channel["group"] = attr.split('=')[1].strip('"')
                elif line and not line.startswith("#") and current_channel:
                    current_channel["url"] = line
                    channels.append(current_channel)
                    current_channel = {}
        logging.info(f"Parsed {len(channels)} channels from {url}")
        return {"items": channels}
    except Exception as e:
        logging.error(f"Failed to parse M3U {url}: {e}")
        return {"items": []}

# Categories and Filters
CATEGORY_KEYWORDS = {
    "Sports": ["sport", "espn", "acc", "sec", "big ten", "tsn", "tnt", "mutv", "viaplay", "nbc sports", "premier sports", "fubo", "directv", "sky sports", "bt sport", "fox sports", "cbs sports", "bein", "astro", "supersport"],
    "Movies": ["cinema", "movie", "hbo", "showtime", "starz", "netflix", "amc", "fx", "paramount", "disney", "universal"],
    "News": ["news", "cnn", "bbc", "sky news", "nbc news", "abc news", "cbs news", "fox news", "bloomberg", "itv news", "rte news"],
    "Entertainment": ["entertainment", "e!", "mtv", "comedy central", "tnt", "usa network", "syfy", "channel 4", "itv", "bbc one", "bbc two"],
    "Kids": ["cartoon", "nick", "disney", "cbstv", "pbs kids", "nick jr", "boomerang", "cbbc"],
    "Science & Documentaries": ["discovery", "nat geo", "history", "bbc earth", "animal planet", "science", "discovery science"],
    "Music": ["mtv", "vh1", "cmttv", "4music", "muchmusic"]
}

CATEGORY_KEYWORDS2 = {
    "USA": ["abc", "nbc", "cbs", "fox", "hbo", "showtime", "amc", "fx", "tnt", "usa", "espn", "acc", "sec", "big ten", "cbs sports", "nbc sports", "paramount", "bloomberg", "discovery", "fubo", "directv"],
    "UK": ["bbc", "itv", "sky", "channel 4", "channel 5", "bt sport", "tnt sports", "mutv", "viaplay", "dave", "uk tv"],
    "Canada": ["cbc", "ctv", "tsn", "sportsnet", "muchmusic"],
    "Europe": ["eurosport", "bbc europe", "sky europe", "france tv", "viaplay"],
    "Ireland": ["rte", "tg4", "virgin media", "premier sports"],
    "Scotland": ["bbc scotland", "stv", "sky sports"],
    "Australia/NZ": ["nine", "ten", "seven", "sky nz", "foxtel", "abc au", "sbs"],
    "South Africa": ["supersport", "dstv"],
    "Bein/Astro": ["bein", "astro sports"]
}

CHANNEL_FILTERS = [
    "acc network", "sec network", "big ten network", "espn", "espn2", "espn3", "espnu", "cbs sports network", "nbc sports", "fox sports 1", "fox sports 2", "nfl network", "nba tv", "mlb network", "nhl network", "pac-12 network", "golf channel", "olympic channel", "tennis channel", "msg", "yes network", "nesn", "root sports", "altitude", "masn", "fubo sports", "directv sports",
    "bloomberg", "cnn", "nbc news", "abc news", "cbs news", "fox news", "msnbc",
    "paramount network", "usa network", "amc", "hbo", "showtime", "starz", "fx", "tnt", "tbs", "syfy", "comedy central", "e!", "mtv", "universal",
    "discovery", "discovery science", "nat geo", "nat geo wild", "history", "animal planet",
    "abc", "nbc", "cbs", "fox", "pbs", "cw",
    "sky sports", "bt sport", "tnt sports", "mutv", "viaplay", "bbc sport", "eurosport", "eurosport 2", "premier sports 1", "premier sports 2",
    "bbc news", "sky news", "itv news",
    "bbc one", "bbc two", "itv", "channel 4", "channel 5", "dave", "uk tv", "film4",
    "tsn", "tsn2", "tsn3", "tsn4", "tsn5", "sportsnet", "sportsnet one", "sportsnet pacific", "sportsnet west", "sportsnet east", "sportsnet ontario",
    "cbc", "ctv", "global",
    "rte sport", "virgin media one", "virgin media two", "rte", "rte2", "tg4",
    "bbc scotland", "stv",
    "fox sports au", "sky sport nz", "espn au", "bein sports au",
    "nine", "ten", "seven", "abc au", "sbs", "foxtel", "sky nz",
    "bein sports", "bein sports 2", "bein sports 3",
    "bbc europe", "sky europe", "france 24",
    "supersport", "dstv",
    "astro sports", "astro supersport",
    "nickelodeon", "disney channel", "cartoon network", "pbs kids", "nick jr", "boomerang", "cbbc", "cbeebies",
    "mtv", "vh1", "cmttv", "4music", "muchmusic"
]

CHANNEL_REMOVE = [
    "adult", "xxx", "porn", "erotic", "18+", "playboy", "hustler", "sex", "brazzers",
    "religious", "church", "god", "jesus", "bible", "faith", "prayer", "gospel",
    "arab", "al jazeera", "mbc", "rotana", "quran", "islam",
    "india", "indian", "zee", "sony", "star", "colors", "sun tv", "ndtv", "aaj tak"
]

CHANNEL_LOGOS = {
    "acc network": "https://upload.wikimedia.org/wikipedia/commons/8/8b/ACC_Network_logo.png",
    "sec network": "https://upload.wikimedia.org/wikipedia/en/5/5f/SEC_Network_logo.png",
    "big ten network": "https://upload.wikimedia.org/wikipedia/en/5/5b/Big_Ten_Network_logo.svg",
    "espn": "https://upload.wikimedia.org/wikipedia/commons/2/2f/ESPN_wordmark.svg",
    "espn2": "https://upload.wikimedia.org/wikipedia/commons/6/63/ESPN2_Logo.svg",
    "espnu": "https://upload.wikimedia.org/wikipedia/en/5/5e/ESPNU_logo.svg",
    "cbs sports network": "https://upload.wikimedia.org/wikipedia/en/6/6e/CBS_Sports_Network_logo.png",
    "nbc sports": "https://upload.wikimedia.org/wikipedia/commons/2/2e/NBC_Sports_logo.png",
    "fox sports 1": "https://upload.wikimedia.org/wikipedia/en/3/3b/Fox_Sports_1_logo.svg",
    "nfl network": "https://upload.wikimedia.org/wikipedia/en/0/0e/NFL_Network_logo.svg",
    "nba tv": "https://upload.wikimedia.org/wikipedia/en/d/d2/NBA_TV.svg",
    "mlb network": "https://upload.wikimedia.org/wikipedia/en/5/5f/MLB_Network_logo.svg",
    "bloomberg": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Bloomberg_Television_logo.svg",
    "cnn": "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg",
    "nbc news": "https://upload.wikimedia.org/wikipedia/commons/4/43/NBC_News_2013_logo.svg",
    "abc news": "https://upload.wikimedia.org/wikipedia/commons/5/5e/ABC_News_logo_2013.svg",
    "cbs news": "https://upload.wikimedia.org/wikipedia/commons/6/6d/CBS_News_logo.svg",
    "fox news": "https://upload.wikimedia.org/wikipedia/en/6/67/Fox_News_Channel_logo.svg",
    "paramount network": "https://upload.wikimedia.org/wikipedia/en/8/8f/Paramount_Network_logo.svg",
    "usa network": "https://upload.wikimedia.org/wikipedia/commons/9/9b/USA_Network_logo_%282016%29.svg",
    "amc": "https://upload.wikimedia.org/wikipedia/en/8/8e/AMC_logo_2016.svg",
    "hbo": "https://upload.wikimedia.org/wikipedia/commons/d/de/HBO_logo.svg",
    "showtime": "https://upload.wikimedia.org/wikipedia/en/0/0e/Showtime_logo.svg",
    "fx": "https://upload.wikimedia.org/wikipedia/en/8/8e/FX_logo.svg",
    "tnt": "https://upload.wikimedia.org/wikipedia/commons/7/7b/TNT_logo_2016.svg",
    "discovery": "https://upload.wikimedia.org/wikipedia/commons/6/64/Discovery_Channel_logo.svg",
    "discovery science": "https://upload.wikimedia.org/wikipedia/en/8/8f/Discovery_Science_logo.svg",
    "nat geo": "https://upload.wikimedia.org/wikipedia/commons/8/8c/National_Geographic_Channel_logo.svg",
    "history": "https://upload.wikimedia.org/wikipedia/commons/8/8e/History_logo.svg",
    "abc": "https://upload.wikimedia.org/wikipedia/commons/6/67/ABC_logo_%282015-present%29.svg",
    "nbc": "https://upload.wikimedia.org/wikipedia/commons/2/2f/NBC_logo.svg",
    "cbs": "https://upload.wikimedia.org/wikipedia/commons/5/5f/CBS_logo.svg",
    "fox": "https://upload.wikimedia.org/wikipedia/en/9/9d/Fox_Broadcasting_Company_logo_%282019%29.svg",
    "sky sports": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sports_logo_2017.png",
    "bt sport": "https://upload.wikimedia.org/wikipedia/en/5/5f/BT_Sport_logo.svg",
    "tnt sports": "https://upload.wikimedia.org/wikipedia/commons/2/2b/TNT_Sports_logo.svg",
    "mutv": "https://upload.wikimedia.org/wikipedia/en/7/7e/MUTV_logo.svg",
    "bbc news": "https://upload.wikimedia.org/wikipedia/en/f/ff/BBC_News.svg",
    "sky news": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_News_logo.svg",
    "bbc one": "https://upload.wikimedia.org/wikipedia/en/5/5e/BBC_One_logo_2021.svg",
    "itv": "https://upload.wikimedia.org/wikipedia/en/5/5e/ITV_logo_2013.svg",
    "channel 4": "https://upload.wikimedia.org/wikipedia/en/5/5e/Channel_4_logo_2015.svg",
    "tsn": "https://upload.wikimedia.org/wikipedia/en/5/5e/TSN_logo.svg",
    "sportsnet": "https://upload.wikimedia.org/wikipedia/en/5/5f/Sportsnet_logo.svg",
    "cbc": "https://upload.wikimedia.org/wikipedia/commons/5/5e/CBC_Logo_1986.svg",
    "ctv": "https://upload.wikimedia.org/wikipedia/en/5/5e/CTV_logo_2018.svg",
    "premier sports 1": "https://upload.wikimedia.org/wikipedia/en/5/5e/Premier_Sports_logo.png",
    "rte": "https://upload.wikimedia.org/wikipedia/en/5/5e/RT%C3%89_logo.svg",
    "nine": "https://upload.wikimedia.org/wikipedia/en/5/5e/Nine_Network_logo.svg",
    "sky sport nz": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sport_NZ_logo.png",
    "supersport": "https://upload.wikimedia.org/wikipedia/commons/6/6e/SuperSport_Logo.png",
    "bein sports": "https://upload.wikimedia.org/wikipedia/commons/1/1f/BeIN_Sports_logo.png",
    "astro sports": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Astro_logo.png"
}

def clean_channel_name(name):
    name = re.sub(r"\s*(\|E|\|H|\(6\)|\(7\)|\.c|\.s)\s*", "", name)
    return f"{name} (V)"

def normalize_tvg_id(name):
    return " ".join(word.capitalize() for word in name.replace("(V)", "").strip().split())

def assign_category(name):
    name_lower = name.lower()
    category1 = next((cat for cat, keywords in CATEGORY_KEYWORDS.items() if any(kw in name_lower for kw in keywords)), "")
    category2 = next((cat for cat, keywords in CATEGORY_KEYWORDS2.items() if any(kw in name_lower for kw in keywords)), "")
    categories = ";".join(filter(None, [category1, category2]))
    return categories if categories else "Other"

def test_stream(url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MediaHubMX/2"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        logging.warning(f"Stream {url} failed: HTTP Error {e.code}: {e.reason}")
        return e.code == 500  # Include 500 errors for potential resolution
    except Exception as e:
        logging.warning(f"Stream {url} failed: {e}")
        return False

def generate_m3u(channels_json, signature=None, filename="/app/generated_playlist.m3u"):
    setup_logging()
    items = channels_json.get("items", [])
    if not items:
        logging.error("No channels available.")
        print("No channels available.")
        # Create an empty M3U to avoid frontend error
        m3u_content = '#EXTM3U url-tvg="http://epg-guide.com/world.gz"\n\n'
        with open(filename, "w", encoding="utf-8") as f:
            f.write(m3u_content)
        return 0

    logging.info(f"Processing {len(items)} channels...")
    seen_names = {}
    playable_count = 0
    m3u_content = '#EXTM3U url-tvg="http://epg-guide.com/world.gz"\n\n'

    for idx, item in enumerate(items, 1):
        original_name = item.get("name", "Unknown")
        
        if any(remove_word.lower() in original_name.lower() for remove_word in CHANNEL_REMOVE):
            logging.info(f"Skipping channel {original_name} (in CHANNEL_REMOVE)")
            continue

        if not any(filter_word.lower() in original_name.lower() for filter_word in CHANNEL_FILTERS):
            logging.info(f"Excluded channel: {original_name}")
            continue

        clean_name = clean_channel_name(original_name)
        count = seen_names.get(clean_name, 0) + 1
        seen_names[clean_name] = count
        display_name = f"{clean_name} ({count})" if count > 1 else clean_name
        
        tvg_id = normalize_tvg_id(clean_name)
        tvg_id_clean = re.sub(r"\s*\(\d+\)$", "", tvg_id)
        
        url = item.get("url", "")
        if not url:
            logging.warning(f"No URL for channel {display_name}")
            continue

        # Resolve URL if signature provided (Vavoo channels)
        resolved_url = resolve_url(url, signature) if signature else url

        logging.info(f"Processing channel {idx}/{len(items)}: {display_name}")
        # Include all filtered channels to ensure non-empty playlist
        playable_count += 1
        category = assign_category(clean_name)
        logo_url = CHANNEL_LOGOS.get(tvg_id.lower(), item.get("tvg-logo", ""))
        m3u_content += (
            f'#EXTINF:-1 tvg-id="{tvg_id_clean}" tvg-name="{tvg_id}" tvg-logo="{logo_url}" group-title="{category}",{display_name}\n'
            f'#EXTVLCOPT:http-user-agent=MediaHubMX/2\n'
            f'{resolved_url}\n\n'
        )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    logging.info(f"Generated M3U8 file: {filename} with {playable_count} streams")
    print(f"M3U8 distanza file generated successfully: {filename} with {playable_count} streams")
    return playable_count

def main():
    # Ensure output directory exists
    os.makedirs(os.path.dirname("/app/generated_playlist.m3u"), exist_ok=True)

    # Try Vavoo API
    signature = get_auth_signature()
    channels_json = None
    if signature:
        channels_json = get_channel_list(signature)

    # Fallback to M3U if API fails
    if not channels_json or not channels_json.get("items"):
        logging.warning("Vavoo API failed, falling back to GitHub M3U")
        print("Vavoo API failed, falling back to GitHub M3U")
        m3u_url = "https://github.com/Mjndai7/omg/raw/refs/heads/main/247worldold.m3u8"
        channels_json = parse_m3u_file(m3u_url)
        signature = None

    playable_count = generate_m3u(channels_json, signature)
    if playable_count == 0:
        logging.error("No streams included in playlist, but empty M3U created.")
        print("No streams included in playlist, but empty M3U created.")

if __name__ == "__main__":
    main()
