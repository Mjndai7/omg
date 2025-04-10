#!/usr/bin/env python3
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
import sys
import logging

# Constants
NUM_CHANNELS = 10000  # Kept high to accommodate all channels
DADDY_JSON_FILE = "daddyliveSchedule.json"  # Unused here, kept for consistency
M3U8_OUTPUT_FILE = "247world.m3u8"
EPG_OUTPUT_FILE = "247world.xml"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"
daddyLiveChannelsFileName = '247channels.html'
daddyLiveChannelsURL = 'https://thedaddy.to/24-7-channels.php'
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

# Channels to exclude (adult, religious, shopping, Indian, etc.)
CHANNEL_REMOVE = [
    "adult", "xxx", "porn", "erotic", "18+", "playboy", "hustler", "sex", "brazzers",
    "religious", "church", "god", "jesus", "bible", "faith", "prayer", "gospel",
    "shopping", "qvc", "hsn", "telemarketing", "deal", "shop",
    "india", "indian", "zee", "sony", "star", "colors", "sun tv", "ndtv", "aaj tak"
]

# Remove existing M3U8 file if it exists (like fullita.py)
if os.path.exists(M3U8_OUTPUT_FILE):
    os.remove(M3U8_OUTPUT_FILE)

def setup_logging():
    logging.basicConfig(filename="247world.log", level=logging.INFO, format="%(asctime)s - %(message)s")

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def fetch_with_debug(filename, url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, 'wb') as file:
            file.write(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        logging.error(f"Failed to fetch {url}: {e}")

def get_stream_link(dlhd_id, channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {channel_name}...")

    base_timeout = 10
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"https://daddylive.mp/embed/stream-{dlhd_id}.php",
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
                server_key_headers["Referer"] = f"https://newembedplay.xyz/premiumtv/daddylivehd.php?id={dlhd_id}"
                server_key_headers["Origin"] = "https://newembedplay.xyz"
                server_key_headers["Sec-Fetch-Site"] = "same-origin"
                response_key = requests.get(server_key_link, headers=server_key_headers, allow_redirects=False, timeout=base_timeout)
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
                    print(f"Stream URL retrieved for channel ID: {dlhd_id} - {channel_name}")
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
    logging.error(f"Failed to get stream for {dlhd_id} after {max_retries} attempts")
    return None

def clean_group_title(sport_key):
    """Clean the sport key to create a proper group-title"""
    import re
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip()
    return clean_key.title() if clean_key else sport_key.strip().title()

def should_exclude_channel(channel_name):
    """Check if channel should be excluded based on keywords"""
    name_lower = channel_name.lower()
    return any(exclude_word in name_lower for exclude_word in CHANNEL_REMOVE)

def search_streams(file_path):
    matches = []
    total_channels = 0
    excluded_channels = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file.read(), 'html.parser')
            links = soup.find_all('a', href=True)
        for link in links:
            if 'stream-' in link['href']:
                href = link['href']
                stream_number = href.split('-')[-1].replace('.php', '')
                stream_name = link.text.strip()
                total_channels += 1
                if should_exclude_channel(stream_name):
                    excluded_channels += 1
                    logging.info(f"Excluded channel: {stream_name}")
                    continue
                matches.append((stream_number, stream_name))
        print(f"\n=== Channel Processing Summary ===")
        print(f"Total channels found: {total_channels}")
        print(f"Channels excluded (adult, religious, shopping, Indian): {excluded_channels}")
        print(f"Channels included: {len(matches)}")
        print(f"===========================\n")
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
    return matches

def process_channels():
    # Fetch 24/7 channels
    fetch_with_debug(daddyLiveChannelsFileName, daddyLiveChannelsURL)
    channel_matches = search_streams(daddyLiveChannelsFileName)

    # Counters
    processed_channels = 0

    # Open M3U8 file with header
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Process all channels
    for channel_id, channel_name in channel_matches:
        stream_url = get_stream_link(channel_id, channel_name)
        if stream_url:
            with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                file.write(f'#EXTINF:-1 tvg-id="{channel_name.lower().replace(" ", "")}" tvg-name="{channel_name}" tvg-logo="{LOGO}" group-title="24/7 Channels", {channel_name}\n')
                file.write('#EXTVLCOPT:http-referrer=https://webxzplay.cfd/\n')
                file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36\n')
                file.write('#EXTVLCOPT:http-origin=https://webxzplay.cfd\n')
                file.write(f"{stream_url}\n\n")
            processed_channels += 1
        else:
            print(f"Failed to get stream URL for channel ID: {channel_id}")

    # Generate EPG
    root = ET.Element('tv')
    for channel_id, channel_name in channel_matches:
        tvg_id = channel_name.lower().replace(" ", "")
        channel_elem = ET.SubElement(root, "channel", id=tvg_id)
        ET.SubElement(channel_elem, "display-name").text = channel_name
    tree = ET.ElementTree(root)
    tree.write(EPG_OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

    return processed_channels

def main():
    setup_logging()
    for file in [M3U8_OUTPUT_FILE, EPG_OUTPUT_FILE, daddyLiveChannelsFileName]:
        if os.path.exists(file):
            os.remove(file)

    # Process channels and generate M3U8
    total_processed_channels = process_channels()

    # Verify if any valid channels were created
    if total_processed_channels == 0:
        print("No valid channels found.")
    else:
        print(f"M3U8 generated with {total_processed_channels} channels.")

if __name__ == "__main__":
    main()

