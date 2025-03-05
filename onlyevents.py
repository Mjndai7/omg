import random
import uuid
import fetcher
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
M3U8_OUTPUT_FILE = "itaevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

# Define keywords for filtering channels
EVENT_KEYWORDS = ["italy", "atp", "tennis", "formula uno", "f1", "motogp", "moto gp", "volley", "serie a", "serie b", "serie c", "uefa champions", "uefa europa",
                 "conference league", "coppa italia"]

# Headers for requests
headers = {
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,ru;q=0.5",
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

# Remove existing M3U8 file if it exists
if os.path.exists(M3U8_OUTPUT_FILE):
    os.remove(M3U8_OUTPUT_FILE)

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_stream_link(dlhd_id, event_name="", channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {event_name} on {channel_name}...")

    base_timeout = 10  # Base timeout in seconds

    for attempt in range(max_retries):
        try:
            # Use timeout for all requests
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
                    # Calculate exponential backoff with jitter
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
                server_key_link = (f'{parent_site_domain}/server_lookup.php?channel_id=premium{dlhd_id}')
                server_key_headers = headers.copy()
                server_key_headers["Referer"] = f"https://newembedplay.xyz/premiumtv/daddylivehd.php?id={dlhd_id}"
                server_key_headers["Origin"] = "https://newembedplay.xyz"
                server_key_headers["Sec-Fetch-Site"] = "same-origin"

                response_key = requests.get(
                    server_key_link,
                    headers=server_key_headers,
                    allow_redirects=False,
                    timeout=base_timeout
                )

                # Add adaptive delay between requests
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
                    stream_url = f"https://{server_key}new.iosplayer.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
                    print(f"Stream URL retrieved for channel ID: {dlhd_id} - {event_name} on {channel_name}")
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

    return None  # If we get here, all retries failed

def clean_group_title(sport_key):
    """Clean the sport key to create a proper group-title"""
    # More robust HTML tag removal
    import re
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip()

    # If empty after cleaning, return original key
    if not clean_key:
        clean_key = sport_key.strip()

    # Convert to title case to standardize
    return clean_key.title()

def should_include_channel(channel_name, event_name, sport_key):
    """Check if channel should be included based on keywords"""
    combined_text = (channel_name + " " + event_name + " " + sport_key).lower()

    # Check if any keyword is present in the combined text
    for keyword in EVENT_KEYWORDS:
        if keyword.lower() in combined_text:
            return True

    return False

def process_events():
    # Fetch JSON schedule
    fetcher.fetchHTML(DADDY_JSON_FILE, "https://daddylive.mp/schedule/schedule-generated.json")

    # Load JSON data
    dadjson = loadJSON(DADDY_JSON_FILE)

    # Counters
    total_events = 0
    skipped_events = 0
    filtered_channels = 0
    processed_channels = 0

    # Define categories to exclude
    excluded_categories = [
        "TV Shows", "Cricket", "Aussie rules", "Snooker", "Baseball",
        "Biathlon", "Cross Country", "Horse Racing", "Ice Hockey",
        "Waterpolo", "Golf", "Darts", "Cycling"
    ]

    # First pass to gather category statistics
    category_stats = {}
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
            clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                if clean_sport_key not in category_stats:
                    category_stats[clean_sport_key] = 0
                category_stats[clean_sport_key] += len(sport_events)
        except (KeyError, TypeError):
            pass

    # Print category statistics
    print("\n=== Available Categories ===")
    for category, count in sorted(category_stats.items()):
        excluded = "EXCLUDED" if category in excluded_categories else ""
        print(f"{category}: {count} events {excluded}")
    print("===========================\n")

    # Generate unique IDs for channels
    unique_ids = generate_unique_ids(NUM_CHANNELS)

    # Open M3U8 file with header
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Second pass to process events
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
            clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                total_events += len(sport_events)

                # Skip only exact category matches
                if clean_sport_key in excluded_categories:
                    skipped_events += len(sport_events)
                    continue

                for game in sport_events:
                    for channel in game.get("channels", []):
                        try:
                            # Clean and format day
                            clean_day = day.replace(" - Schedule Time UK GMT", "").replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
                            day_parts = clean_day.split()

                            if len(day_parts) >= 4:
                                day_num = day_parts[1]
                                month_name = day_parts[2]
                                year = day_parts[3]

                                # Get time from game data
                                time_str = game.get("time", "00:00")

                                # Convert time from UK to CET (add 1 hour)
                                time_parts = time_str.split(":")
                                if len(time_parts) == 2:
                                    hour = int(time_parts[0])
                                    minute = time_parts[1]
                                    hour_cet = (hour + 1) % 24
                                    hour_cet_str = f"{hour_cet:02d}"
                                    time_str_cet = f"{hour_cet_str}:{minute}"
                                else:
                                    time_str_cet = time_str

                                # Month map for conversion
                                month_map = {
                                    "January": "01", "February": "02", "March": "03", "April": "04",
                                    "May": "05", "June": "06", "July": "07", "August": "08",
                                    "September": "09", "October": "10", "November": "11", "December": "12"
                                }
                                month_num = month_map.get(month_name, "01")

                                # Ensure day has leading zero if needed
                                if len(day_num) == 1:
                                    day_num = f"0{day_num}"

                                # Create formatted date time
                                year_short = year[2:4]
                                formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                            else:
                                print(f"Invalid date format after cleaning: {clean_day}")
                                continue

                        except Exception as e:
                            print(f"Error processing date '{day}': {e}")
                            print(f"Game time: {game.get('time', 'No time found')}")
                            continue

                        # Build channel name with new date format
                        #channelName = game["event"] + " " + formatted_date_time + "  " + channel["channel_name"]
                        channelName = formatted_date_time + "  " + channel["channel_name"]
                        # Extract event and channel parts for analysis
                        #event_part = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                        #channel_part = channel["channel_name"].strip()
                        # Extract event name for the tvg-id
                        event_name = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                        event_details = game["event"]  # Keep the full event details for tvg-name
                        # Check if channel should be included based on keywords
                        if should_include_channel(channelName, event_name, sport_key):
                            # Process channel information
                            channelID = f"{channel['channel_id']}"
                            tvgName = channelName

                            # Get stream URL
                            stream_url_dynamic = get_stream_link(channelID, event_details, channel["channel_name"])

                            if stream_url_dynamic:
                                # Append to M3U8 file
                                with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                    #file.write(f'#EXTINF:-1 tvg-id="{event_part} - {channel_part}" tvg-name="{tvgName}" tvg-logo="{LOGO}" group-title="{clean_group_title(sport_key)}", {channel_part} (D)\n')
                                    file.write(f'#EXTINF:-1 tvg-id="{event_name} - {event_details.split(":", 1)[1].strip() if ":" in event_details else event_details}" tvg-name="{event_details} {formatted_date_time}" tvg-logo="{LOGO}" group-title="{clean_sport_key}", {formatted_date_time}  {channel["channel_name"]}\n')
                                    file.write('#EXTVLCOPT:http-referrer=https://ilovetoplay.xyz/\n')
                                    file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36\n')
                                    file.write('#EXTVLCOPT:http-origin=https://ilovetoplay.xyz\n')
                                    file.write(f"{stream_url_dynamic}\n\n")

                                processed_channels += 1
                                filtered_channels += 1
                            else:
                                print(f"Failed to get stream URL for channel ID: {channelID}")
                        else:
                            print(f"Skipping channel (no keyword match): {clean_group_title(sport_key)} - {event_details} - {channelName}")

        except KeyError as e:
            print(f"KeyError: {e} - Key may not exist in JSON structure")

    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Total events found: {total_events}")
    print(f"Events skipped due to category filters: {skipped_events}")
    print(f"Channels included due to keyword match: {filtered_channels}")
    print(f"Channels successfully processed: {processed_channels}")
    print(f"Keywords used for filtering: {EVENT_KEYWORDS}")
    print(f"===========================\n")

    return processed_channels

def main():
    # Process events and generate M3U8
    total_processed_channels = process_events()

    # Verify if any valid channels were created
    if total_processed_channels == 0:
        print("No valid channels found matching the keywords.")
    else:
        print(f"M3U8 generated with {total_processed_channels} channels filtered by keywords.")

if __name__ == "__main__":
    main()
ubuntu@omg:~/daddy/ok$ cat only.py
import random
import uuid
import fetcher
import json
import os
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import time
# Costanti
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "onlyevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

mStartTime = 0
mStopTime = 0

# Headers and related constants from the first code block (assuming these are needed for requests)
Referer = "https://ilovetoplay.xyz/"
Origin = "https://ilovetoplay.xyz"
key_url = "https%3A%2F%2Fkey2.keylocking.ru%2F"

headers = { # **Define base headers *without* Referer and Origin**
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,ru;q=0.5",
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
# Simulated client and credentials - Replace with your actual client and credentials if needed
client = requests # Using requests as a synchronous client

def get_stream_link(dlhd_id, event_name="", channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {event_name} on {channel_name}...")

    base_timeout = 10  # Base timeout in seconds

    for attempt in range(max_retries):
        try:
            # Use timeout for all requests
            response = client.get(
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
                    # Calculate exponential backoff with jitter
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
                server_key_link = (f'{parent_site_domain}/server_lookup.php?channel_id=premium{dlhd_id}')
                server_key_headers = headers.copy()
                server_key_headers["Referer"] = f"https://newembedplay.xyz/premiumtv/daddylivehd.php?id={dlhd_id}"
                server_key_headers["Origin"] = "https://newembedplay.xyz"
                server_key_headers["Sec-Fetch-Site"] = "same-origin"

                response_key = client.get(
                    server_key_link,
                    headers=server_key_headers,
                    allow_redirects=False,
                    timeout=base_timeout
                )

                # Add adaptive delay between requests
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
                    stream_url = f"https://{server_key}new.iosplayer.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
                    print(f"Stream URL retrieved for channel ID: {dlhd_id} - {event_name} on {channel_name}")
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

    return None  # If we get here, all retries failed

# Rimuove i file esistenti per garantirne la rigenerazione
for file in [M3U8_OUTPUT_FILE, DADDY_JSON_FILE]: # daddyLiveChannelsFileName kept for file removal consistency, but not used
    if os.path.exists(file):
        os.remove(file)

# Funzioni prima parte dello script
def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)


def addChannelsByLeagueSport():
    global channelCount
    processed_schedule_channels = 0  # Counter for schedule channels

    # Define categories to exclude - these must match exact category names in JSON
    excluded_categories = [
        "TV Shows", "Cricket", "Aussie rules", "Snooker", "Baseball",
        "Biathlon", "Cross Country", "Horse Racing", "Ice Hockey",
        "Waterpolo", "Golf", "Darts", "Cycling",
        "TV Shows</span>", "Cricket</span>", "Aussie rules</span>", "Snooker</span>", "Baseball</span>",
        "Biathlon</span>", "Cross Country</span>", "Horse Racing</span>", "Ice Hockey</span>",
        "Waterpolo</span>", "Golf</span>", "Darts</span>", "Cycling</span>", "Handball</span>", "Squash</span>"
    ]

    # Debug counters
    total_events = 0
    skipped_events = 0
    category_stats = {}  # To track how many events per category

    # First pass to gather category statistics
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                # Clean the sport key by removing HTML tags
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()

               #sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                if clean_sport_key not in category_stats:
                    category_stats[clean_sport_key] = 0
                category_stats[clean_sport_key] += len(sport_events)
        except (KeyError, TypeError):
            pass  # Skip problematic days

    # Print category statistics
    print("\n=== Available Categories ===")
    for category, count in sorted(category_stats.items()):
        excluded = "EXCLUDED" if category in excluded_categories else ""
        print(f"{category}: {count} events {excluded}")
    print("===========================\n")

    # Second pass to process events
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                # Clean the sport key by removing HTML tags
                #sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()

                total_events += len(sport_events)

                # Skip only exact category matches
                if clean_sport_key in excluded_categories:
                    skipped_events += len(sport_events)
                    continue

                for game in sport_events:
                    for channel in game.get("channels", []):
                        try:
                            # Remove the "Schedule Time UK GMT" part and split the remaining string
                            clean_day = day.replace(" - Schedule Time UK GMT", "")

                            # Remove ordinal suffixes (st, nd, rd, th)
                            clean_day = clean_day.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")

                            # Split the cleaned string
                            day_parts = clean_day.split()

                            if len(day_parts) >= 4:  # Make sure we have enough parts
                                day_num = day_parts[1]
                                month_name = day_parts[2]
                                year = day_parts[3]

                                # Get time from game data
                                time_str = game.get("time", "00:00")

                                # Converti l'orario da UK a CET (aggiungi 1 ora)
                                time_parts = time_str.split(":")
                                if len(time_parts) == 2:
                                    hour = int(time_parts[0])
                                    minute = time_parts[1]
                                    # Aggiungi un'ora all'orario UK
                                    hour_cet = (hour + 1) % 24
                                    # Assicura che l'ora abbia due cifre
                                    hour_cet_str = f"{hour_cet:02d}"
                                    # Nuovo time_str con orario CET
                                    time_str_cet = f"{hour_cet_str}:{minute}"
                                else:
                                    # Se il formato dell'orario non è corretto, mantieni l'originale
                                    time_str_cet = time_str

                                # Convert month name to number
                                month_map = {
                                    "January": "01", "February": "02", "March": "03", "April": "04",
                                    "May": "05", "June": "06", "July": "07", "August": "08",
                                    "September": "09", "October": "10", "November": "11", "December": "12"
                                }
                                month_num = month_map.get(month_name, "01")  # Default to January if not found

                                # Ensure day has leading zero if needed
                                if len(day_num) == 1:
                                    day_num = f"0{day_num}"

                                # Create a datetime object in UTC (no timezone conversion yet)
                                year_short = year[2:4]  # Extract last two digits of year

                                # Format as requested: "01/03/25 - 10:10" con orario CET
                                formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                                # Also create proper datetime objects for EPG
                                # Make sure we're using clean numbers for the date components
                                date_str = f"{year}-{month_num}-{day_num} {time_str}:00"
                                start_date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

                                # Convert to Amsterdam timezone
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                start_date_amsterdam = start_date_utc.replace(tzinfo=pytz.UTC).astimezone(amsterdam_timezone)

                                # Format for EPG
                                mStartTime = start_date_amsterdam.strftime("%Y%m%d%H%M%S")
                                mStopTime = (start_date_amsterdam + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")

                            else:
                                print(f"Invalid date format after cleaning: {clean_day}")
                                continue

                        except Exception as e:
                            print(f"Error processing date '{day}': {e}")
                            print(f"Game time: {game.get('time', 'No time found')}")
                            continue

                        # Get next unique ID
                        UniqueID = unique_ids.pop(0)

                        try:
                            # Build channel name with new date format
                          # channelName = game["event"] + " " + formatted_date_time + "  " + channel["channel_name"]
                            channelName = formatted_date_time + "  " + channel["channel_name"]

                            # Extract event part and channel part for TVG ID
                           #if ":" in game["event"]:
                           #    event_part = game["event"].split(":")[0].strip()
                           #else:
                           #    event_part = game["event"].strip()
                            event_name = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                            event_details = game["event"]  # Keep the full event details for tvg-name

                           #channel_part = channel["channel_name"].strip()
                           #custom_tvg_id = f"{event_part} - {channel_part}"

                        except (TypeError, KeyError) as e:
                            print(f"Error processing event: {e}")
                            continue

                        # Process channel information
                        channelID = f"{channel['channel_id']}"
                        tvgName = channelName
                        tvLabel = tvgName
                        channelCount += 1
                        print(f"Processing channel {channelCount}: {clean_sport_key} - {channelName}")

                        # Get stream URL
                        stream_url_dynamic = get_stream_link(channelID, game["event"], channel["channel_name"])

                        if stream_url_dynamic:
                            # Write to M3U8 file
                            with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                if channelCount == 1:
                                    file.write('#EXTM3U\n')

                            with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                file.write(f'#EXTINF:-1 tvg-id="{event_name} - {event_details.split(":", 1)[1].strip() if ":" in event_details else event_details}" tvg-name="{event_details} {formatted_date_time}" tvg-logo="{LOGO}" group-title="{clean_sport_key}", {formatted_date_time}  {channel["channel_name"]}\n')
                                file.write('#EXTVLCOPT:http-referrer=https://ilovetoplay.xyz/\n')
                                file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36\n')
                                file.write('#EXTVLCOPT:http-origin=https://ilovetoplay.xyz\n')
                                file.write(f"{stream_url_dynamic}\n\n")

                            processed_schedule_channels += 1
                        else:
                            print(f"Failed to get stream URL for channel ID: {channelID}")


        except KeyError as e:
            print(f"KeyError: {e} - Key may not exist in JSON structure")

    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Total events found: {total_events}")
    print(f"Events skipped due to category filters: {skipped_events}")
    print(f"Channels successfully processed: {processed_schedule_channels}")
    print(f"===========================\n")

    return processed_schedule_channels

STATIC_LOGOS = {
    "sky uno": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-uno-it.png",
    "dazn 1": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/DAZN_1_Logo.svg/774px-DAZN_1_Logo.svg.png"
}

STATIC_TVG_IDS = {
    "sky uno": "sky uno",
    "20 mediaset": "Mediaset 20",
}

STATIC_CATEGORIES = {
    "sky uno": "Sky",
    "20 mediaset": "Mediaset",
}

def fetch_with_debug(filename, url):
    try:
        #print(f'Downloading {url}...') # Debug removed
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(filename, 'wb') as file:
            file.write(response.content)

        #print(f'File {filename} downloaded successfully.') # Debug removed
    except requests.exceptions.RequestException as e:
        #print(f'Error downloading {url}: {e}') # Debug removed
        pass # No debug print, just skip


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
        #print(f'The file {file_path} does not exist.') # Debug removed
        pass # No debug print, just skip
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

def generate_m3u8_247(matches): # Rinominata per evitare conflitti, ma non sarà usata
    if not matches:
        #print("No matches found for 24/7 channels. Skipping M3U8 generation.") # Debug removed
        return 0 # Return 0 as no 24/7 channels processed

    processed_247_channels = 0 # Counter for 24/7 channels, but will remain 0
    with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file: # Appende al file esistente
        pass # 24/7 generation is skipped, so the loop and content writing are removed

    #print("M3U8 file updated with 24/7 channels.") # Debug removed, and incorrect message
    return processed_247_channels # Return count of processed 24/7 channels (always 0 now)


# Inizio del codice principale

# Inizializza contatore e genera ID univoci
channelCount = 0
unique_ids = generate_unique_ids(NUM_CHANNELS)
total_schedule_channels = 0 # Counter for total schedule channels attempted
total_247_channels = 0 # Counter for total 24/7 channels attempted - will remain 0

# Scarica il file JSON con la programmazione
fetcher.fetchHTML(DADDY_JSON_FILE, "https://daddylive.mp/schedule/schedule-generated.json")

# Carica i dati dal JSON
dadjson = loadJSON(DADDY_JSON_FILE)

# Aggiunge i canali reali
total_schedule_channels = addChannelsByLeagueSport()

# Verifica se sono stati creati canali validi
if channelCount == 0:
    print("Nessun canale valido trovato dalla programmazione.") # Modificata la frase
    pass


# Fetch e generazione M3U8 per i canali 24/7 - RIMOSSO COMPLETAMENTE
# fetch_with_debug(daddyLiveChannelsFileName, daddyLiveChannelsURL)
# matches_247 = search_streams(daddyLiveChannelsFileName, "Italy") # Cerca tutti i canali
# total_247_channels = generate_m3u8_247(matches_247)

print(f"Script completato. Canali eventi aggiunti: {total_schedule_channels}") # Messaggio finale modificato, solo canali eventi
