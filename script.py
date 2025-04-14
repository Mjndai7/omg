import xml.etree.ElementTree as ET
import random
import uuid
import json
import os
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import time

# Constants
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "247world.m3u8"
EPG_OUTPUT_FILE = "247world.xml"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

mStartTime = 0
mStopTime = 0

# File and URL for channels
daddyLiveChannelsFileName = '247channels.html'
daddyLiveChannelsURL = 'https://thedaddy.to/24-7-channels.php'

# Headers
Referer = "https://ilovetoplay.xyz/"
Origin = "https://ilovetoplay.xyz"
key_url = "https%3A%2F%2Fkey2.keylocking.ru%2F"

headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "Sec-Ch-UA-Mobile": "?0",
    "Sec-Ch-UA-Platform": "Windows",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Storage-Access": "active",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

client = requests

def get_stream_link(dlhd_id, max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id}...")

    base_timeout = 10

    for attempt in range(max_retries):
        try:
            response = client.get(
                f"https://thedaddy.to/embed/stream-{dlhd_id}.php",
                headers=headers,
                timeout=base_timeout
            )
            response.raise_for_status()
            response.encoding = 'utf-8'

            response_text = response.text
            if not response_text:
                print(f"Warning: Empty response received for channel ID: {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

            soup = BeautifulSoup(response_text, 'html.parser')
            iframe = soup.find('iframe', id='thatframe')

            if iframe is None:
                print(f"Debug: iframe with id 'thatframe' NOT FOUND for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

            if iframe and iframe.get('src'):
                real_link = iframe.get('src')
                parent_site_domain = real_link.split('/premiumtv')[0]
                server_key_link = f'{parent_site_domain}/server_lookup.php?channel_id=premium{dlhd_id}'
                server_key_headers = headers.copy()
                server_key_headers["Referer"] = f"https://newembedplay.xyz/premiumtv/daddyhd.php?id={dlhd_id}"
                server_key_headers["Origin"] = "https://newembedplay.xyz"
                server_key_headers["Sec-Fetch-Site"] = "same-origin"

                response_key = client.get(
                    server_key_link,
                    headers=server_key_headers,
                    allow_redirects=False,
                    timeout=base_timeout
                )

                time.sleep(random.uniform(1, 3))
                response_key.raise_for_status()

                try:
                    server_key_data = response_key.json()
                except json.JSONDecodeError:
                    print(f"JSON Decode Error for channel ID {dlhd_id}: Invalid JSON response: {response_key.text[:100]}...")
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                        continue
                    return None

                if 'server_key' in server_key_data:
                    server_key = server_key_data['server_key']
                    stream_url = f"https://{server_key}new.newkso.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
                    print(f"Stream URL retrieved for channel ID: {dlhd_id}")
                    return stream_url
                else:
                    print(f"Error: 'server_key' not found in JSON response from {server_key_link} (attempt {attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                        continue
                    return None
            else:
                print(f"Error: iframe with id 'thatframe' found, but 'src' attribute is missing for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

        except requests.exceptions.Timeout:
            print(f"Timeout error for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            return None

        except requests.exceptions.RequestException as e:
            print(f"Request Exception for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            return None

        except Exception as e:
            print(f"General Exception for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            return None

    return None

# Remove existing files
for file in [M3U8_OUTPUT_FILE, EPG_OUTPUT_FILE, DADDY_JSON_FILE, daddyLiveChannelsFileName]:
    if os.path.exists(file):
        os.remove(file)

# Channel Data (restructured for your channels)
STATIC_LOGOS = {
    "acc network": "https://upload.wikimedia.org/wikipedia/commons/8/8b/ACC_Network_logo.png",
    "sec network": "https://upload.wikimedia.org/wikipedia/en/5/5f/SEC_Network_logo.png",
    "big ten network": "https://upload.wikimedia.org/wikipedia/en/5/5b/Big_Ten_Network_logo.svg",
    "espn": "https://upload.wikimedia.org/wikipedia/commons/2/2f/ESPN_wordmark.svg",
    "espn2": "https://upload.wikimedia.org/wikipedia/commons/6/63/ESPN2_Logo.svg",
    "cbs sports network": "https://upload.wikimedia.org/wikipedia/en/6/6e/CBS_Sports_Network_logo.png",
    "nbc sports": "https://upload.wikimedia.org/wikipedia/commons/2/2e/NBC_Sports_logo.png",
    "fox sports 1": "https://upload.wikimedia.org/wikipedia/en/3/3b/Fox_Sports_1_logo.svg",
    "nfl network": "https://upload.wikimedia.org/wikipedia/en/0/0e/NFL_Network_logo.svg",
    "bloomberg": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Bloomberg_Television_logo.svg",
    "cnn": "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg",
    "abc news": "https://upload.wikimedia.org/wikipedia/commons/5/5e/ABC_News_logo_2013.svg",
    "paramount network": "https://upload.wikimedia.org/wikipedia/en/8/8f/Paramount_Network_logo.svg",
    "usa network": "https://upload.wikimedia.org/wikipedia/commons/9/9b/USA_Network_logo_%282016%29.svg",
    "amc": "https://upload.wikimedia.org/wikipedia/en/8/8e/AMC_logo_2016.svg",
    "hbo": "https://upload.wikimedia.org/wikipedia/commons/d/de/HBO_logo.svg",
    "discovery": "https://upload.wikimedia.org/wikipedia/commons/6/64/Discovery_Channel_logo.svg",
    "abc": "https://upload.wikimedia.org/wikipedia/commons/6/67/ABC_logo_%282015-present%29.svg",
    "nbc": "https://upload.wikimedia.org/wikipedia/commons/2/2f/NBC_logo.svg",
    "cbs": "https://upload.wikimedia.org/wikipedia/commons/5/5f/CBS_logo.svg",
    "sky sports": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_Sports_logo_2017.png",
    "tnt sports": "https://upload.wikimedia.org/wikipedia/commons/2/2b/TNT_Sports_logo.svg",
    "mutv": "https://upload.wikimedia.org/wikipedia/en/7/7e/MUTV_logo.svg",
    "bbc news": "https://upload.wikimedia.org/wikipedia/en/f/ff/BBC_News.svg",
    "sky news": "https://upload.wikimedia.org/wikipedia/en/5/5e/Sky_News_logo.svg",
    "bbc one": "https://upload.wikimedia.org/wikipedia/en/5/5e/BBC_One_logo_2021.svg",
    "itv": "https://upload.wikimedia.org/wikipedia/en/5/5e/ITV_logo_2013.svg",
    "tsn": "https://upload.wikimedia.org/wikipedia/en/5/5e/TSN_logo.svg",
    "sportsnet": "https://upload.wikimedia.org/wikipedia/en/5/5f/Sportsnet_logo.svg",
    "cbc": "https://upload.wikimedia.org/wikipedia/commons/5/5e/CBC_Logo_1986.svg",
    "rte": "https://upload.wikimedia.org/wikipedia/en/5/5e/RT%C3%89_logo.svg",
    "nine": "https://upload.wikimedia.org/wikipedia/en/5/5e/Nine_Network_logo.svg",
    "supersport": "https://upload.wikimedia.org/wikipedia/commons/6/6e/SuperSport_Logo.png",
    "bein sports": "https://upload.wikimedia.org/wikipedia/commons/1/1f/BeIN_Sports_logo.png",
    "nickelodeon": "https://upload.wikimedia.org/wikipedia/commons/7/7e/Nickelodeon_2009_logo.svg",
    "disney channel": "https://upload.wikimedia.org/wikipedia/en/7/73/Disney_Channel_logo.svg",
    "mtv": "https://upload.wikimedia.org/wikipedia/commons/6/6e/MTV_Logo.svg"
}

STATIC_TVG_IDS = {
    "acc network": "accnetwork.us",
    "sec network": "secnetwork.us",
    "big ten network": "bigtennetwork.us",
    "espn": "espn.us",
    "espn2": "espn2.us",
    "cbs sports network": "cbssports.us",
    "nbc sports": "nbcsports.us",
    "fox sports 1": "foxsports1.us",
    "nfl network": "nflnetwork.us",
    "bloomberg": "bloomberg.us",
    "cnn": "cnn.us",
    "abc news": "abcnews.us",
    "paramount network": "paramount.us",
    "usa network": "usanetwork.us",
    "amc": "amc.us",
    "hbo": "hbo.us",
    "discovery": "discovery.us",
    "abc": "abc.us",
    "nbc": "nbc.us",
    "cbs": "cbs.us",
    "sky sports": "skysports.uk",
    "tnt sports": "tntsports.uk",
    "mutv": "mutv.uk",
    "bbc news": "bbcnews.uk",
    "sky news": "skynews.uk",
    "bbc one": "bbc1.uk",
    "itv": "itv.uk",
    "tsn": "tsn.ca",
    "sportsnet": "sportsnet.ca",
    "cbc": "cbc.ca",
    "rte": "rte.ie",
    "nine": "nine.au",
    "supersport": "supersport.za",
    "bein sports": "beinsports.qa",
    "nickelodeon": "nickelodeon.us",
    "disney channel": "disneychannel.us",
    "mtv": "mtv.us"
}

STATIC_CATEGORIES = {
    "acc network": "Sports",
    "sec network": "Sports",
    "big ten network": "Sports",
    "espn": "Sports",
    "espn2": "Sports",
    "cbs sports network": "Sports",
    "nbc sports": "Sports",
    "fox sports 1": "Sports",
    "nfl network": "Sports",
    "bloomberg": "News",
    "cnn": "News",
    "abc news": "News",
    "paramount network": "Entertainment",
    "usa network": "Entertainment",
    "amc": "Entertainment",
    "hbo": "Movies",
    "discovery": "Documentaries",
    "abc": "Entertainment",
    "nbc": "Entertainment",
    "cbs": "Entertainment",
    "sky sports": "Sports",
    "tnt sports": "Sports",
    "mutv": "Sports",
    "bbc news": "News",
    "sky news": "News",
    "bbc one": "Entertainment",
    "itv": "Entertainment",
    "tsn": "Sports",
    "sportsnet": "Sports",
    "cbc": "Entertainment",
    "rte": "Entertainment",
    "nine": "Entertainment",
    "supersport": "Sports",
    "bein sports": "Sports",
    "nickelodeon": "Kids",
    "disney channel": "Kids",
    "mtv": "Music"
}

def fetch_with_debug(filename, url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, 'wb') as file:
            file.write(response.content)
    except requests.exceptions.RequestException as e:
        pass

def search_category(channel_name):
    return STATIC_CATEGORIES.get(channel_name.lower().strip(), "Undefined")

def search_streams(file_path, keyword):
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file.read(), 'html.parser')
            links = soup.find_all('a', href=True)
        for link in links:
            if keyword.lower() in link.text.lower():
                href = link['href']
                stream_number = href.split('-')[-1].replace('.php', '')
                stream_name = link.text.strip()
                match = (stream_number, stream_name)
                if match not in matches:
                    matches.append(match)
    except FileNotFoundError:
        pass
    return matches

def search_logo(channel_name):
    channel_name_lower = channel_name.lower().strip()
    for key, url in STATIC_LOGOS.items():
        if key in channel_name_lower:
            return url
    return "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddlive.png"

def search_tvg_id(channel_name):
    channel_name_lower = channel_name.lower().strip()
    for key, tvg_id in STATIC_TVG_IDS.items():
        if key in channel_name_lower:
            return tvg_id
    return "unknown"

def generate_m3u8_247(matches):
    if not matches:
        return 0

    processed_247_channels = 0
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write("#EXTM3U\n\n")
        for channel in matches:
            channel_id = channel[0]
            channel_name = channel[1].replace("HD+", "").strip()
            tvicon_path = search_logo(channel_name)
            tvg_id = search_tvg_id(channel_name)
            category = search_category(channel_name)
            print(f"Processing 24/7 channel: {channel_name} - Channel Count (24/7): {processed_247_channels + 1}")

            stream_url_dynamic = get_stream_link(channel_id)

            if stream_url_dynamic:
                file.write(f"#EXTINF:-1 tvg-id=\"{tvg_id}\" tvg-name=\"{channel_name}\" tvg-logo=\"{tvicon_path}\" group-title=\"{category}\", {channel_name}\n")
                file.write(f'#EXTVLCOPT:http-referrer=https://webxzplay.cfd/\n')
                file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3\n')
                file.write('#EXTVLCOPT:http-origin=https://webxzplay.cfd\n')
                file.write(f"{stream_url_dynamic}\n\n")
                processed_247_channels += 1
            else:
                pass
    return processed_247_channels

# Main execution
channelCount = 0
total_247_channels = 0

root = ET.Element('tv')

if channelCount == 0:
    pass
else:
    tree = ET.ElementTree(root)
    tree.write(EPG_OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    pass

fetch_with_debug(daddyLiveChannelsFileName, daddyLiveChannelsURL)
matches_247 = search_streams(daddyLiveChannelsFileName, "")
total_247_channels = generate_m3u8_247(matches_247)

print(f"Script completed. 24/7 channels added: {total_247_channels}")
