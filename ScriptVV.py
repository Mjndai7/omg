#!/usr/bin/env python3
import requests
import json
import logging
import sys
import re
import os

def get_auth_signature():
    headers = {
        "user-agent": "okhttp/4.11.0",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "content-length": "1106",
        "accept-encoding": "gzip"
    }

    data = {
        "token": "8Us2TfjeOFrzqFFTEjL3E5KfdAWGa5PV3wQe60uK4BmzlkJRMYFu0ufaM_eeDXKS2U04XUuhbDTgGRJrJARUwzDyCcRToXhW5AcDekfFMfwNUjuieeQ1uzeDB9YWyBL2cn5Al3L3gTnF8Vk1t7rPwkBob0swvxA",
        "reason": "player.enter",
        "locale": "de",
        "theme": "dark",
        "metadata": {
            "device": {
                "type": "Handset",
                "brand": "google",
                "model": "Nexus 5",
                "name": "21081111RG",
                "uniqueId": "d10e5d99ab665233"
            },
            "os": {
                "name": "android",
                "version": "7.1.2",
                "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"],
                "host": "android"
            },
            "app": {
                "platform": "android",
                "version": "3.0.2",
                "buildId": "288045000",
                "engine": "jsc",
                "signatures": ["09f4e07040149486e541a1cb34000b6e12527265252fa2178dfe2bd1af6b815a"],
                "installer": "com.android.secex"
            },
            "version": {
                "package": "tv.vavoo.app",
                "binary": "3.0.2",
                "js": "3.1.4"
            }
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
        "proxy": {
            "supported": ["ss"],
            "engine": "ss",
            "enabled": False,
            "autoServer": True,
            "id": "ca-bhs"
        },
        "iap": {
            "supported": False
        }
    }

    try:
        response = requests.post("https://www.vavoo.tv/api/app/ping", json=data, headers=headers)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get("addonSig")
    except Exception as e:
        print(f"Errore durante il recupero della firma: {e}")
        return None

def setup_logging():
    logging.basicConfig(filename="excluded_channels.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Broad Content Categories
CATEGORY_KEYWORDS = {
    "Sports": ["sport", "espn", "acc", "sec", "big ten", "tsn", "tnt", "mutv", "viaplay", "nbc sports", "premier sports", "fubo", "directv", "sky sports", "bt sport", "fox sports", "cbs sports", "bein", "astro", "supersport"],
    "Movies": ["cinema", "movie", "hbo", "showtime", "starz", "netflix", "amc", "fx", "paramount", "disney", "universal"],
    "News": ["news", "cnn", "bbc", "sky news", "nbc news", "abc news", "cbs news", "fox news", "bloomberg", "itv news", "rte news"],
    "Entertainment": ["entertainment", "e!", "mtv", "comedy central", "tnt", "usa network", "syfy", "channel 4", "itv", "bbc one", "bbc two"],
    "Kids": ["cartoon", "nick", "disney", "cbstv", "pbs kids", "nick jr", "boomerang", "cbbc"],
    "Science & Documentaries": ["discovery", "nat geo", "history", "bbc earth", "animal planet", "science", "discovery science"],
    "Music": ["mtv", "vh1", "cmttv", "4music", "muchmusic"]
}

# Regional Provider Categories
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

# Expanded Channel Filters (Major Channels from Multiple Countries)
CHANNEL_FILTERS = [
    # USA - Sports
    "acc network", "sec network", "espn", "espn2", "espn3", "espnu", "big ten network", "cbs sports network", "nbc sports", "fox sports 1", "fox sports 2", "nfl network", "nba tv", "mlb network", "nhl network",
    # USA - News
    "bloomberg", "cnn", "nbc news", "abc news", "cbs news", "fox news", "msnbc",
    # USA - Entertainment & Movies
    "paramount network", "usa network", "amc", "hbo", "showtime", "starz", "fx", "tnt", "tbs", "syfy", "comedy central", "e!", "mtv", "universal",
    # USA - Science & Documentaries
    "discovery", "discovery science", "nat geo", "nat geo wild", "history", "animal planet",
    # USA - General
    "abc", "nbc", "cbs", "fox", "pbs", "cw", "fubo sports", "directv sports",
    # UK - Sports
    "sky sports", "bt sport", "tnt sports", "mutv", "viaplay", "bbc sport",
    # UK - News
    "bbc news", "sky news", "itv news",
    # UK - Entertainment & Movies
    "bbc one", "bbc two", "itv", "channel 4", "channel 5", "dave", "uk tv", "film4",
    # Canada - Sports
    "tsn", "tsn2", "tsn3", "tsn4", "tsn5", "sportsnet", "sportsnet one", "sportsnet pacific", "sportsnet west", "sportsnet east", "sportsnet ontario",
    # Canada - General
    "cbc", "ctv", "global",
    # Ireland - Sports
    "premier sports 1", "premier sports 2", "rte sport",
    # Ireland - General
    "rte", "rte2", "tg4", "virgin media one", "virgin media two",
    # Scotland
    "bbc scotland", "stv",
    # Australia/New Zealand - Sports
    "fox sports au", "sky sport nz", "espn au", "bein sports au",
    # Australia/New Zealand - General
    "nine", "ten", "seven", "abc au", "sbs", "foxtel", "sky nz",
    # Europe - Sports
    "eurosport", "eurosport 2", "viaplay", "bein sports",
    # Europe - General
    "bbc europe", "sky europe", "france 24",
    # South Africa - Sports
    "supersport", "dstv",
    # Bein/Astro - Sports
    "bein sports", "bein sports 2", "bein sports 3", "astro sports", "astro supersport",
    # Kids
    "nickelodeon", "disney channel", "cartoon network", "pbs kids", "nick jr", "boomerang", "cbbc", "cbeebies",
    # Music
    "mtv", "vh1", "cmttv", "4music", "muchmusic",
    # Additional FuboTV/DirecTV Channels
    "pac-12 network", "golf channel", "olympic channel", "tennis channel", "msg", "yes network", "nesn", "root sports", "altitude", "masn"
]

# Filters to Exclude Unwanted Categories
CHANNEL_REMOVE = [
    "adult", "xxx", "porn", "erotic", "18+", "playboy", "hustler", "sex", "brazzers",
    "religious", "church", "god", "jesus", "bible", "faith", "prayer", "gospel",
    "arab", "al jazeera", "mbc", "rotana", "quran", "islam",
    "india", "indian", "zee", "sony", "star", "colors", "sun tv", "ndtv", "aaj tak"
]

# Expanded Channel Logos (Covering Major Channels)
CHANNEL_LOGOS = {
    # USA - Sports
    "acc network": "https://upload.wikimedia.org/wikipedia/commons/8/8b/ACC_Network_logo.png",
    "sec network": "https://upload.wikimedia.org/wikipedia/en/5/5f/SEC_Network_logo.png",
    "espn": "https://upload.wikimedia.org/wikipedia/commons/2/2f/ESPN_wordmark.svg",
    "espn2": "https://upload.wikimedia.org/wikipedia/commons/6/63/ESPN2_Logo.svg",
    "espnu": "https://upload.wikimedia.org/wikipedia/en/5/5e/ESPNU_logo.svg",
    "big ten network": "https://upload.wikimedia.org/wikipedia/en/5/5b/Big_Ten_Network_logo.svg",
    "cbs sports network": "https://upload.wikimedia.org/wikipedia/en/6/6e/CBS_Sports_Network_logo.png",
    "nbc sports": "https://upload.wikimedia.org/wikipedia/commons/2/2e/NBC_Sports_logo.png",
    "fox sports 1": "https://upload.wikimedia.org/wikipedia/en/3/3b/Fox_Sports_1_logo.svg",
    "nfl network": "https://upload.wikimedia.org/wikipedia/en/0/0e/NFL_Network_logo.svg",
    "nba tv": "https://upload.wikimedia.org/wikipedia/en/d/d2/NBA_TV.svg",
    "mlb network": "https://upload.wikimedia.org/wikipedia/en/5/5f/MLB_Network_logo.svg",
    # USA - News
    "bloomberg": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Bloomberg_Television_logo.svg",
    "cnn": "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg",
    "nbc news": "https://upload.wikimedia.org/wikipedia/commons/4/43/NBC_News_2013_logo.svg",
    "abc news": "https://upload.wikimedia.org/wikipedia/commons/5/5e/ABC_News_logo_2013.svg",
    "cbs news": "https://upload.wikimedia.org/wikipedia/commons/6/6d/CBS_News_logo.svg",
    "fox news": "https://upload.wikimedia.org/wikipedia/en/6/67/Fox_News_Channel_logo.svg",
    # USA - Entertainment & Movies
    "paramount network": "https://upload.wikimedia.org/wikipedia/en/8/8f/Paramount_Network_logo.svg",
    "usa network": "https://upload.wikimedia.org/wikipedia/commons/9/9b/USA_Network_logo_%282016%29.svg",
    "amc": "https://upload.wikimedia.org/wikipedia/en/8/8e/AMC_logo_2016.svg",
    "hbo": "https://upload.wikimedia.org/wikipedia/commons/d/de/HBO_logo.svg",
    "showtime": "https://upload.wikimedia.org/wikipedia/en/0/0e/Showtime_logo.svg",
    "fx": "https://upload.wikimedia.org/wikipedia/en/8/8e/FX_logo.svg",
    "tnt": "https://upload.wikimedia.org/wikipedia/commons/7/7b/TNT_logo_2016.svg",
    # USA - Science & Documentaries
    "discovery": "https://upload.wikimedia.org/wikipedia/commons/6/64/Discovery_Channel_logo.svg",
    "discovery science": "https://upload.wikimedia.org/wikipedia/en/8/8f/Discovery_Science_logo.svg",
    "nat geo": "https://upload.wikimedia.org/wikipedia/commons/8/8c/National_Geographic_Channel_logo.svg",
    "history": "https://upload.wikimedia.org/wikipedia/commons/8/8e/History_logo.svg",
    # USA - General
    "abc": "https://upload.wikimedia.org/wikipedia/commons/6/67/ABC_logo_%282015-present%29.svg",
    "nbc": "https://upload.wikimedia.org/wikipedia/commons/2/2f/NBC_logo.svg",
    "cbs": "https://upload.wikimedia.org/wikipedia/commons/5/5f/CBS_logo.svg",
    "fox": "https://upload.wikimedia.org/wikipedia/en/9/9d/Fox_Broadcasting_Company_logo_%282019%29.svg",
    # UK - Sports
    "sky sports": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sports_logo_2017.png",
    "bt sport": "https://upload.wikimedia.org/wikipedia/en/5/5f/BT_Sport_logo.svg",
    "tnt sports": "https://upload.wikimedia.org/wikipedia/commons/2/2b/TNT_Sports_logo.svg",
    "mutv": "https://upload.wikimedia.org/wikipedia/en/7/7e/MUTV_logo.svg",
    # UK - News
    "bbc news": "https://upload.wikimedia.org/wikipedia/en/f/ff/BBC_News.svg",
    "sky news": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_News_logo.svg",
    # UK - Entertainment
    "bbc one": "https://upload.wikimedia.org/wikipedia/en/5/5e/BBC_One_logo_2021.svg",
    "itv": "https://upload.wikimedia.org/wikipedia/en/5/5e/ITV_logo_2013.svg",
    "channel 4": "https://upload.wikimedia.org/wikipedia/en/5/5e/Channel_4_logo_2015.svg",
    # Canada - Sports
    "tsn": "https://upload.wikimedia.org/wikipedia/en/5/5e/TSN_logo.svg",
    "sportsnet": "https://upload.wikimedia.org/wikipedia/en/5/5f/Sportsnet_logo.svg",
    # Canada - General
    "cbc": "https://upload.wikimedia.org/wikipedia/commons/5/5e/CBC_Logo_1986.svg",
    "ctv": "https://upload.wikimedia.org/wikipedia/en/5/5e/CTV_logo_2018.svg",
    # Ireland
    "premier sports 1": "https://upload.wikimedia.org/wikipedia/en/5/5e/Premier_Sports_logo.png",
    "rte": "https://upload.wikimedia.org/wikipedia/en/5/5e/RT%C3%89_logo.svg",
    # Australia/NZ
    "nine": "https://upload.wikimedia.org/wikipedia/en/5/5e/Nine_Network_logo.svg",
    "sky sport nz": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sport_NZ_logo.png",
    # South Africa
    "supersport": "https://upload.wikimedia.org/wikipedia/commons/6/6e/SuperSport_Logo.png",
    # Bein/Astro
    "bein sports": "https://upload.wikimedia.org/wikipedia/commons/1/1f/BeIN_Sports_logo.png",
    "astro sports": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Astro_logo.png"
}

def clean_channel_name(name):
    """Pulisce e modifica il nome del canale aggiungendo (V)."""
    name = re.sub(r"\s*(\|E|\|H|\(6\)|\(7\)|\.c|\.s)\s*", "", name)
    return f"{name} (V)"

def normalize_tvg_id(name):
    """Normalizza il tvg-id con solo la prima lettera maiuscola."""
    return " ".join(word.capitalize() for word in name.replace("(V)", "").strip().split())

def assign_category(name):
    """Assegna la categoria in base ai due dizionari."""
    name_lower = name.lower()
    category1 = next((category for category, keywords in CATEGORY_KEYWORDS.items() if any(keyword in name_lower for keyword in keywords)), "")
    category2 = next((category for category, keywords in CATEGORY_KEYWORDS2.items() if any(keyword in name_lower for keyword in keywords)), "")
    categories = ";".join(filter(None, [category1, category2]))
    return categories if categories else "Altro"

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
            "region": "US",
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
            response = requests.post("https://vavoo.to/vto-cluster/mediahubmx-catalog.json", json=data, headers=headers)
            response.raise_for_status()
            result = response.json()

            items = result.get("items", [])
            if not items:
                break

            all_items.extend(items)
            cursor += len(items)

        except Exception as e:
            print(f"Errore durante il recupero della lista dei canali: {e}")
            break

    return {"items": all_items}

def generate_m3u(channels_json, signature, filename="channels.m3u8"):
    setup_logging()
    items = channels_json.get("items", [])
    if not items:
        print("Nessun canale disponibile.")
        return

    print(f"Generating M3U8 file with {len(items)} channels...")
    
    seen_names = {}

    with open(filename, "w", encoding="utf-8") as f:
        f.write('#EXTM3U url-tvg="http://epg-guide.com/it.gz"\n\n')

        for idx, item in enumerate(items, 1):
            original_name = item.get("name", "Unknown")
            
            if any(remove_word.lower() in original_name.lower() for remove_word in CHANNEL_REMOVE):
                print(f"Skipping channel {original_name} (in CHANNEL_REMOVE)")
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
            
            original_link = item.get("url")
            if not original_link:
                continue

            print(f"Processing channel {idx}/{len(items)}: {display_name}")
            
            category = assign_category(clean_name)
            base_tvg_id = tvg_id.lower()
            logo_url = CHANNEL_LOGOS.get(base_tvg_id, "")
            
            f.write(f'#EXTINF:-1 tvg-id="{tvg_id_clean}" tvg-name="{tvg_id}" tvg-logo="{logo_url}" group-title="{category}",{display_name}\n')
            f.write('#EXTVLCOPT:http-user-agent=MediaHubMX/2\n')
            f.write(f'{original_link}\n\n')

    print(f"M3U8 file generated successfully: {filename}")

def main():
    print("Getting authentication signature...")
    signature = get_auth_signature()
    if not signature:
        print("Failed to get authentication signature.")
        sys.exit(1)

    print("Getting channel list...")
    channels_json = get_channel_list(signature)
    if not channels_json:
        print("Failed to get channel list.")
        sys.exit(1)

    print("Generating M3U8 file...")
    generate_m3u(channels_json, signature)
    print("Done!")

if __name__ == "__main__":
    main()
