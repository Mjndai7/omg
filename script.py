#!/usr/bin/env python3
import requests
import json
import logging
import sys
import re
import os
import urllib.request
import time

# Setup logging
def setup_logging():
    logging.basicConfig(
        filename="/app/channel_processing.log",  # Compatible with Docker /app directory
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

# Fetch Vavoo authentication signature
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

    try:
        response = requests.post("https://www.vavoo.tv/api/app/ping", json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("addonSig")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching signature: {e}")
        return None

# Broad Content Categories
CATEGORY_KEYWORDS = {
    "Sports": ["sport", "espn", "acc", "sec", "big ten", "mutv", "nbc sports", "sky sports", "bt sport", "tnt sports", "fox sports", "cbs sports", "tsn", "sportsnet", "eurosport", "bein", "premier sports"],
    "Movies": ["cinema", "movie", "hbo", "showtime", "starz", "amc", "fx", "paramount", "universal", "tnt", "tbs"],
    "TV Shows": ["entertainment", "e!", "mtv", "comedy central", "usa network", "syfy", "channel 4", "itv", "bbc one", "bbc two", "nbc", "abc", "cbs", "fox"],
    "Science": ["discovery", "nat geo", "history", "bbc earth", "animal planet", "science", "discovery science"],
    "Business": ["bloomberg", "cnbc", "fox business", "sky news business"],
    "News": ["news", "cnn", "bbc", "sky news", "nbc news", "abc news", "cbs news", "fox news", "itv news"],
    "Kids": ["cartoon", "nick", "disney", "pbs kids", "nick jr", "boomerang", "cbbc"],
    "Music": ["mtv", "vh1", "4music", "muchmusic"]
}

# Regional Provider Categories
CATEGORY_KEYWORDS2 = {
    "USA": ["abc", "nbc", "cbs", "fox", "hbo", "showtime", "amc", "fx", "tnt", "usa", "espn", "acc", "sec", "big ten", "cbs sports", "nbc sports", "bloomberg", "cnbc", "discovery", "nat geo"],
    "UK": ["bbc", "itv", "sky", "channel 4", "bt sport", "tnt sports", "mutv", "dave"],
    "Canada": ["cbc", "ctv", "tsn", "sportsnet", "muchmusic"],
    "Europe": ["eurosport", "bbc europe", "sky europe"]
}

# Channel Filters (Major Channels from UK, USA, Canada)
CHANNEL_FILTERS = [
    # USA - Sports
    "acc network", "sec network", "big ten network", "espn", "espn2", "espnu", "cbs sports network", "nbc sports", "fox sports 1", "fox sports 2", "nfl network", "nba tv", "mlb network", "nhl network",
    # USA - News
    "bloomberg", "cnn", "nbc news", "abc news", "cbs news", "fox news", "cnbc", "msnbc",
    # USA - Entertainment & Movies
    "paramount network", "usa network", "amc", "hbo", "showtime", "fx", "tnt", "tbs", "syfy", "comedy central", "e!", "mtv",
    # USA - Science
    "discovery", "discovery science", "nat geo", "nat geo wild", "history", "animal planet",
    # USA - General
    "abc", "nbc", "cbs", "fox", "cw",
    # UK - Sports
    "sky sports", "bt sport", "tnt sports", "mutv", "eurosport", "eurosport 2",
    # UK - News
    "bbc news", "sky news", "itv news",
    # UK - Entertainment & Movies
    "bbc one", "bbc two", "itv", "channel 4", "dave", "film4",
    # UK - Science
    "bbc earth",
    # Canada - Sports
    "tsn", "tsn2", "tsn3", "tsn4", "tsn5", "sportsnet", "sportsnet one", "sportsnet pacific", "sportsnet west",
    # Canada - General
    "cbc", "ctv", "global",
    # Kids
    "nickelodeon", "disney channel", "cartoon network", "pbs kids", "nick jr", "boomerang", "cbbc",
    # Music
    "mtv", "vh1", "4music", "muchmusic"
]

# Filters to Exclude Unwanted Categories
CHANNEL_REMOVE = [
    "adult", "xxx", "porn", "erotic", "18+", "playboy", "hustler", "sex", "brazzers",
    "religious", "church", "god", "jesus", "bible", "faith", "prayer", "gospel",
    "arab", "islam", "al jazeera", "mbc", "rotana", "quran", "dubai", "saudi", "emirates"
]

# Channel Logos (Key Channels)
CHANNEL_LOGOS = {
    "acc network": "https://upload.wikimedia.org/wikipedia/commons/8/8b/ACC_Network_logo.png",
    "sec network": "https://upload.wikimedia.org/wikipedia/en/5/5f/SEC_Network_logo.png",
    "big ten network": "https://upload.wikimedia.org/wikipedia/en/5/5b/Big_Ten_Network_logo.svg",
    "espn": "https://upload.wikimedia.org/wikipedia/commons/2/2f/ESPN_wordmark.svg",
    "mutv": "https://upload.wikimedia.org/wikipedia/en/7/7e/MUTV_logo.svg",
    "cbs sports network": "https://upload.wikimedia.org/wikipedia/en/6/6e/CBS_Sports_Network_logo.png",
    "nbc sports": "https://upload.wikimedia.org/wikipedia/commons/2/2e/NBC_Sports_logo.png",
    "bloomberg": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Bloomberg_Television_logo.svg",
    "cnn": "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg",
    "bbc one": "https://upload.wikimedia.org/wikipedia/en/5/5e/BBC_One_logo_2021.svg",
    "sky sports": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sports_logo_2017.png",
    "bt sport": "https://upload.wikimedia.org/wikipedia/en/5/5f/BT_Sport_logo.svg",
    "tnt sports": "https://upload.wikimedia.org/wikipedia/commons/2/2b/TNT_Sports_logo.svg",
    "tsn": "https://upload.wikimedia.org/wikipedia/en/5/5e/TSN_logo.svg",
    "sportsnet": "https://upload.wikimedia.org/wikipedia/en/5/5f/Sportsnet_logo.svg",
    "hbo": "https://upload.wikimedia.org/wikipedia/commons/d/de/HBO_logo.svg",
    "discovery": "https://upload.wikimedia.org/wikipedia/commons/6/64/Discovery_Channel_logo.svg",
    "nat geo": "https://upload.wikimedia.org/wikipedia/commons/8/8c/National_Geographic_Channel_logo.svg"
}

def clean_channel_name(name):
    name = re.sub(r"\s*(\|E|\|H|\(6\)|\(7\)|\.c|\.s)\s*", "", name)
    return f"{name} (V)"

def normalize_tvg_id(name):
    return " ".join(word.capitalize() for word in name.replace("(V)", "").strip().split())

def assign_category(name):
    name_lower = name.lower()
    category1 = next((category for category, keywords in CATEGORY_KEYWORDS.items() if any(keyword in name_lower for keyword in keywords)), "")
    category2 = next((category for category, keywords in CATEGORY_KEYWORDS2.items() if any(keyword in name_lower for keyword in keywords)), "")
    categories = ";".join(filter(None, [category1, category2]))
    return categories if categories else "Other"

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
            "region": "WW",  # Worldwide coverage
            "catalogId": "vto-iptv",
            "id": "vto-iptv",
            "adult": False,
            "search": "",
            "sort": "name",
            "filter": {},
            "cursor": cursor,
            "clientVersion": "3.0.2"
        }

        try:
            response = requests.post("https://vavoo.to/vto-cluster/mediahubmx-catalog.json", json=data, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            items = result.get("items", [])
            if not items:
                break
            all_items.extend(items)
            cursor += len(items)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching channels: {e}")
            break

    return {"items": all_items}

def test_stream(url, timeout=5):
    """Test if a stream URL is playable."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MediaHubMX/2"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return True
    except Exception as e:
        logging.warning(f"Stream test failed for {url}: {e}")
    return False

def generate_m3u(channels_json, filename="/app/generated_playlist.m3u"):  # Path compatible with Docker
    setup_logging()
    items = channels_json.get("items", [])
    if not items:
        logging.error("No channels available.")
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
            continue

        logging.info(f"Testing channel {idx}/{len(items)}: {display_name}")
        if test_stream(url):
            playable_count += 1
            category = assign_category(clean_name)
            logo_url = CHANNEL_LOGOS.get(tvg_id.lower(), "")
            m3u_content += (
                f'#EXTINF:-1 tvg-id="{tvg_id_clean}" tvg-name="{tvg_id}" tvg-logo="{logo_url}" group-title="{category}",{display_name}\n'
                f'#EXTVLCOPT:http-user-agent=MediaHubMX/2\n'
                f'{url}\n\n'
            )
        else:
            logging.warning(f"Channel {display_name} not playable, excluded")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    logging.info(f"Generated M3U8 file: {filename} with {playable_count} playable streams")
    return playable_count

def main():
    signature = get_auth_signature()
    if not signature:
        logging.error("Failed to get authentication signature.")
        sys.exit(1)

    channels_json = get_channel_list(signature)
    if not channels_json or not channels_json.get("items"):
        logging.error("Failed to get channel list.")
        sys.exit(1)

    playable_count = generate_m3u(channels_json)
    print(f"Generated playlist with {playable_count} playable streams at /app/generated_playlist.m3u")

if __name__ == "__main__":
    main()
