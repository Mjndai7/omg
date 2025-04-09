#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import random
import json
import os
import requests
from bs4 import BeautifulSoup
import time
import sys
import logging

# Constants
NUM_CHANNELS = 10000
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

# Filters for UK, US, Europe focus
CHANNEL_FILTERS = [
    "bbc", "itv", "channel 4", "channel 5", "sky", "bt sport", "eurosport",
    "cnn", "nbc", "abc", "cbs", "fox", "hbo", "espn", "disney", "nick",
    "mtv", "discovery", "nat geo", "history", "amc", "paramount", "pbs",
    "zdf", "arte"
]

CHANNEL_REMOVE = [
    "adult", "xxx", "porn", "erotic", "18+", "playboy", "hustler",
    "religious", "shopping", "qvc", "hsn", "telemarketing"
]

def setup_logging():
    logging.basicConfig(filename="247world.log", level=logging.INFO, format="%(asctime)s - %(message)s")

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
    print(f"Getting stream link for channel ID: {dlhd_id} - {channel_name}...", file=sys.stderr)
    base_timeout = 10
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"https://thedaddy.to/embed/stream-{dlhd_id}.php",
                headers=headers,
                timeout=base_timeout
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            response_text = response.text
            if not response_text:
                print(f"Warning: Empty response for {dlhd_id} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...", file=sys.stderr)
                    time.sleep(sleep_time)
                    continue
                return None
            soup = BeautifulSoup(response_text, 'html.parser')
            iframe = soup.find('iframe', id='thatframe')
            if iframe is None:
                print(f"iframe 'thatframe' not found for {dlhd_id} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
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
                response_key = requests.get(server_key_link, headers=server_key_headers, allow_redirects=False, timeout=base_timeout)
                time.sleep(random.uniform(1, 3))
                response_key.raise_for_status()
                try:
                    server_key_data = response_key.json()
                except json.JSONDecodeError:
                    print(f"JSON Decode Error for {dlhd_id}: {response_key.text[:100]}...", file=sys.stderr)
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                        continue
                    return None
                if 'server_key' in server_key_data:
                    server_key = server_key_data['server_key']
                    return f"https://{server_key}new.newkso.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
                else:
                    print(f"'server_key' not found for {dlhd_id} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                        continue
                    return None
            else:
                print(f"iframe 'src' missing for {dlhd_id} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                    continue
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout for {dlhd_id} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
                continue
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request Exception for {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
                continue
            return None
        except Exception as e:
            print(f"General Exception for {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
                continue
            return None
    logging.error(f"Failed to get stream for {dlhd_id} after {max_retries} attempts")
    return None

def search_streams(file_path):
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file.read(), 'html.parser')
            links = soup.find_all('a', href=True)
        for link in links:
            if 'stream-' in link['href']:
                href = link['href']
                stream_number = href.split('-')[-1].replace('.php', '')
                stream_name = link.text.strip()
                name_lower = stream_name.lower()
                if any(remove_word in name_lower for remove_word in CHANNEL_REMOVE):
                    logging.info(f"Excluded channel: {stream_name}")
                    continue
                if not any(filter_word in name_lower for filter_word in CHANNEL_FILTERS):
                    logging.info(f"Excluded channel: {stream_name}")
                    continue
                matches.append((stream_number, stream_name))
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.", file=sys.stderr)
    return matches

def generate_m3u8_247(matches):
    if not matches:
        print("No matches found for 24/7 channels.", file=sys.stderr)
        return 0
    processed_channels = 0
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')
    for idx, (channel_id, channel_name) in enumerate(matches, 1):
        print(f"Processing 24/7 channel {idx}/{len(matches)}: {channel_name}", file=sys.stderr)
        stream_url = get_stream_link(channel_id, channel_name)
        if stream_url:
            with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                file.write(f'#EXTINF:-1 tvg-id="{channel_name.lower().replace(" ", "")}" tvg-name="{channel_name}" tvg-logo="{LOGO}" group-title="24/7 Channels", {channel_name}\n')
                file.write('#EXTVLCOPT:http-referrer=https://webxzplay.cfd/\n')
                file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3\n')
                file.write('#EXTVLCOPT:http-origin=https://webxzplay.cfd\n')
                file.write(f"{stream_url}\n\n")
            processed_channels += 1
    return processed_channels

def generate_epg(channels):
    root = ET.Element('tv')
    for channel_id, channel_name in channels:
        tvg_id = channel_name.lower().replace(" ", "")
        channel_elem = ET.SubElement(root, "channel", id=tvg_id)
        ET.SubElement(channel_elem, "display-name").text = channel_name
    tree = ET.ElementTree(root)
    tree.write(EPG_OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

def main():
    setup_logging()
    for file in [M3U8_OUTPUT_FILE, EPG_OUTPUT_FILE, daddyLiveChannelsFileName]:
        if os.path.exists(file):
            os.remove(file)

    print("Fetching 24/7 channels...", file=sys.stderr)
    fetch_with_debug(daddyLiveChannelsFileName, daddyLiveChannelsURL)
    matches = search_streams(daddyLiveChannelsFileName)

    if not matches:
        print("No valid 24/7 channels found.", file=sys.stderr)
        sys.exit(1)

    print("Generating M3U8 for 24/7 channels...", file=sys.stderr)
    total_channels = generate_m3u8_247(matches)

    print("Generating EPG...", file=sys.stderr)
    generate_epg(matches)

    print(f"Script completed. Processed {total_channels} 24/7 channels.", file=sys.stderr)

if __name__ == "__main__":
    main()
