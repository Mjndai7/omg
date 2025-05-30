import xml.etree.ElementTree as ET
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
import re
from urllib.parse import quote_plus  # Add this import

# Constants
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "itaevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

# Add a cache for logos to avoid repeated requests
LOGO_CACHE = {}

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

# Move the get_dynamic_logo function here, before it's called
def get_dynamic_logo(event_name):
    """
    Cerca immagini dinamiche solo per eventi di Serie A e Serie B italiani
    """
    # Check if we already have this logo in cache
    if event_name in LOGO_CACHE:
        print(f"Logo trovato in cache per: {event_name}")
        return LOGO_CACHE[event_name]
    
    # Verifica se l'evento è di Serie A o Serie B
    is_serie_a_or_b = False
    if "Italy - Serie A :" in event_name or "Italy - Serie B :" in event_name:
        is_serie_a_or_b = True
        print(f"Evento Serie A/B rilevato: {event_name}")
    else:
        print(f"Evento non di Serie A/B: {event_name}")
    
    # Se non è Serie A o Serie B, usa il logo predefinito
    if not is_serie_a_or_b:
        LOGO_CACHE[event_name] = LOGO
        return LOGO
    
    # Try to extract team names from event format like "League : Team1 vs Team2"
    teams_match = re.search(r':\s*([^:]+?)\s+vs\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)
    
    if not teams_match:
        # Try alternative format "Team1 - Team2"
        teams_match = re.search(r'([^:]+?)\s+-\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)
    
    if not teams_match:
        # If no team names found, return default logo
        print(f"Non sono riuscito a estrarre i nomi delle squadre da: {event_name}")
        return LOGO
    
    team1 = teams_match.group(1).strip()
    team2 = teams_match.group(2).strip()
    print(f"Squadre estratte: '{team1}' vs '{team2}'")
    
    try:
        # First try to get logos from guardacalcio.cam
        guardacalcio_url = "https://guardacalcio.cam/partite-streaming.html"
        headers_guardacalcio = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        print(f"Cercando logo per {team1} vs {team2} su guardacalcio.cam...")
        
        response = requests.get(guardacalcio_url, headers=headers_guardacalcio, timeout=10)
        html_content = response.text
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Normalizza i nomi delle squadre per la ricerca
        team1_normalized = team1.lower().replace(" ", "").replace("-", "")
        team2_normalized = team2.lower().replace(" ", "").replace("-", "")
        
        # Cerca tutte le immagini nella pagina
        img_tags = soup.find_all('img')
        print(f"Trovate {len(img_tags)} immagini su guardacalcio.cam")
        
        # Cerca immagini che contengono i nomi delle squadre nel src o nell'alt
        for img in img_tags:
            if img.has_attr('src'):
                src = img['src']
                alt = img.get('alt', '')
                
                # Normalizza src e alt per la ricerca
                src_normalized = src.lower()
                alt_normalized = alt.lower()
                
                # Verifica se il nome di una delle squadre è presente nel src o nell'alt
                if (team1_normalized in src_normalized or team1.lower() in src_normalized or 
                    team1_normalized in alt_normalized or team1.lower() in alt_normalized or
                    team2_normalized in src_normalized or team2.lower() in src_normalized or
                    team2_normalized in alt_normalized or team2.lower() in alt_normalized):
                    
                    # Assicurati che l'URL sia assoluto
                    if src.startswith('http'):
                        logo_url = src
                    else:
                        # Costruisci URL assoluto
                        base_url = "https://guardacalcio.cam"
                        if src.startswith('/'):
                            logo_url = base_url + src
                        else:
                            logo_url = base_url + '/' + src
                    
                    print(f"Trovato logo su guardacalcio.cam: {logo_url}")
                    LOGO_CACHE[event_name] = logo_url
                    return logo_url
        
        # Se non troviamo immagini specifiche, cerchiamo immagini che contengono "serie-a" o "serie-b"
        for img in img_tags:
            if img.has_attr('src'):
                src = img['src']
                
                if "serie-a" in src.lower() or "serie-b" in src.lower():
                    # Assicurati che l'URL sia assoluto
                    if src.startswith('http'):
                        logo_url = src
                    else:
                        # Costruisci URL assoluto
                        base_url = "https://guardacalcio.cam"
                        if src.startswith('/'):
                            logo_url = base_url + src
                        else:
                            logo_url = base_url + '/' + src
                    
                    print(f"Trovato logo generico Serie A/B: {logo_url}")
                    LOGO_CACHE[event_name] = logo_url
                    return logo_url
        
        # Se non troviamo nulla su guardacalcio.cam, usa il logo di default
        print(f"Nessun logo trovato su guardacalcio.cam, uso il logo di default")
        LOGO_CACHE[event_name] = LOGO
        return LOGO
        
    except Exception as e:
        print(f"Error fetching logo for {team1} vs {team2}: {e}")
        import traceback
        traceback.print_exc()
        return LOGO

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
                    stream_url = f"https://{server_key}new.newkso.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
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
    # fetcher.fetchHTML(DADDY_JSON_FILE, "https://daddylive.mp/schedule/schedule-generated.json")

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
                            clean_day = day.replace(" - Schedule Time UK GMT", "")
                            # Rimuovi completamente i suffissi ordinali (st, nd, rd, th)
                            clean_day = clean_day.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
                            # Rimuovi anche i suffissi attaccati al numero (1st, 2nd, 3rd, etc.)
                            import re
                            clean_day = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_day)
                            
                            print(f"Original day: '{day}'")
                            print(f"Clean day after processing: '{clean_day}'")
                            
                            day_parts = clean_day.split()
                            print(f"Day parts: {day_parts}")  # Debug per vedere i componenti della data

                            # Handle various date formats with better validation
                            day_num = None
                            month_name = None
                            year = None
                            
                            if len(day_parts) >= 4:  # Standard format: Weekday Month Day Year
                                weekday = day_parts[0]
                                # Verifica se il secondo elemento contiene lettere (è il mese) o numeri (è il giorno)
                                if any(c.isalpha() for c in day_parts[1]):
                                    # Formato: Weekday Month Day Year
                                    month_name = day_parts[1]
                                    day_num = day_parts[2]
                                elif any(c.isalpha() for c in day_parts[2]):
                                    # Formato: Weekday Day Month Year
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                else:
                                    # Se non riusciamo a determinare, assumiamo il formato più comune
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                year = day_parts[3]
                                print(f"Parsed date components: weekday={weekday}, day={day_num}, month={month_name}, year={year}")
                            elif len(day_parts) == 3:
                                # Format could be: "Weekday Day Year" (missing month) or "Day Month Year"
                                if day_parts[0].lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                                    # It's "Weekday Day Year" format (missing month)
                                    day_num = day_parts[1]
                                    # Get current month for Rome timezone
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                    month_name = current_month
                                    year = day_parts[2]
                                else:
                                    # Assume Day Month Year
                                    day_num = day_parts[0]
                                    month_name = day_parts[1]
                                    year = day_parts[2]
                            else:
                                # Use current date from Rome timezone
                                rome_tz = pytz.timezone('Europe/Rome')
                                now = datetime.datetime.now(rome_tz)
                                day_num = now.strftime('%d')
                                month_name = now.strftime('%B')
                                year = now.strftime('%Y')
                                print(f"Using current Rome date for: {clean_day}")

                            # Validate day_num - ensure it's a number and extract only digits
                            if day_num:
                                # Extract only digits from day_num
                                day_num_digits = re.sub(r'[^0-9]', '', str(day_num))
                                if day_num_digits:
                                    day_num = day_num_digits
                                else:
                                    # If no digits found, use current day
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Warning: Invalid day number '{day_num}', using current day: {day_num}")
                            else:
                                # If day_num is None, use current day
                                rome_tz = pytz.timezone('Europe/Rome')
                                day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                print(f"Warning: Missing day number, using current day: {day_num}")
                            
                            # Get time from game data
                            time_str = game.get("time", "00:00")

                            # Converti l'orario da UK a CET (aggiungi 2 ore invece di 1)
                            time_parts = time_str.split(":")
                            if len(time_parts) == 2:
                                hour = int(time_parts[0])
                                minute = time_parts[1]
                                # Aggiungi due ore all'orario UK
                                hour_cet = (hour + 2) % 24
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
                            
                            # Aggiungi controllo per il mese
                            if not month_name or month_name not in month_map:
                                print(f"Warning: Invalid month name '{month_name}', using current month")
                                rome_tz = pytz.timezone('Europe/Rome')
                                current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                month_name = current_month
                                
                            month_num = month_map.get(month_name, "01")  # Default to January if not found

                            # Ensure day has leading zero if needed
                            if len(str(day_num)) == 1:
                                day_num = f"0{day_num}"

                            # Create formatted date time
                            year_short = str(year)[-2:]  # Extract last two digits of year
                            formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                            # Also create proper datetime objects for EPG
                            # Make sure we're using clean numbers for the date components
                            try:
                                # Ensure all date components are valid
                                if not day_num or day_num == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Using current day as fallback: {day_num}")
                                
                                if not month_num or month_num == "":
                                    month_num = "01"  # Default to January
                                    print(f"Using January as fallback month")
                                
                                if not year or year == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    year = datetime.datetime.now(rome_tz).strftime('%Y')
                                    print(f"Using current year as fallback: {year}")
                                
                                if not time_str or time_str == "":
                                    time_str = "00:00"
                                    print(f"Using 00:00 as fallback time")
                                
                                # Ensure day_num has proper format (1-31)
                                try:
                                    day_int = int(day_num)
                                    if day_int < 1 or day_int > 31:
                                        day_num = "01"  # Default to first day of month
                                        print(f"Day number out of range, using 01 as fallback")
                                except ValueError:
                                    day_num = "01"  # Default to first day of month
                                    print(f"Invalid day number format, using 01 as fallback")
                                
                                # Ensure day has leading zero if needed
                                if len(str(day_num)) == 1:
                                    day_num = f"0{day_num}"
                                
                                date_str = f"{year}-{month_num}-{day_num} {time_str}:00"
                                print(f"Attempting to parse date: '{date_str}'")
                                start_date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                
                                # Convert to Amsterdam timezone
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                start_date_amsterdam = start_date_utc.replace(tzinfo=pytz.UTC).astimezone(amsterdam_timezone)
                                
                                # Format for EPG
                                mStartTime = start_date_amsterdam.strftime("%Y%m%d%H%M%S")
                                mStopTime = (start_date_amsterdam + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")
                            except ValueError as e:
                                # Definisci date_str qui se non è già definita
                                error_msg = str(e)
                                if 'date_str' not in locals():
                                    date_str = f"Error with: {year}-{month_num}-{day_num} {time_str}:00"
                                
                                print(f"Date parsing error: {error_msg} for date string '{date_str}'")
                                # Use current time as fallback
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                now = datetime.datetime.now(amsterdam_timezone)
                                mStartTime = now.strftime("%Y%m%d%H%M%S")
                                mStopTime = (now + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")

                            # Build channel name with new date format
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channelName = formatted_date_time + "  " + channel["channel_name"]
                            else:
                                channelName = formatted_date_time + "  " + str(channel)

                            # Extract event name for the tvg-id
                            event_name = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                            event_details = game["event"]  # Keep the full event details for tvg-name

                        except Exception as e:
                            print(f"Error processing date '{day}': {e}")
                            print(f"Game time: {game.get('time', 'No time found')}")
                            continue

                        # Check if channel should be included based on keywords
                        if should_include_channel(channelName, event_name, sport_key):
                            # Process channel information
                            if isinstance(channel, dict) and "channel_id" in channel:
                                channelID = f"{channel['channel_id']}"
                            else:
                                # Generate a fallback ID
                                channelID = str(uuid.uuid4())

                            # Around line 353 where you access channel["channel_name"]
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channel_name_str = channel["channel_name"]
                            else:
                                channel_name_str = str(channel)
                            stream_url_dynamic = get_stream_link(channelID, event_details, channel_name_str)

                            if stream_url_dynamic:
                                # Around line 361 where you access channel["channel_name"] again
                                if isinstance(channel, dict) and "channel_name" in channel:
                                    channel_name_str = channel["channel_name"]
                                else:
                                    channel_name_str = str(channel)

                                with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                    # Estrai l'orario dal formatted_date_time
                                    time_only = time_str_cet if time_str_cet else "00:00"

                                    # Crea il nuovo formato per tvg-name con l'orario all'inizio e la data alla fine
                                    tvg_name = f"{time_only} {event_details} - {day_num}/{month_num}/{year_short}"
                                    
                                    # Get dynamic logo for this event
                                    event_logo = get_dynamic_logo(game["event"])

                                    file.write(f'#EXTINF:-1 tvg-id="{event_name} - {event_details.split(":", 1)[1].strip() if ":" in event_details else event_details}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{clean_sport_key}", {channel_name_str}\n')
                                    file.write('#EXTVLCOPT:http-referrer=https://webxzplay.cfd/\n')
                                    file.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36\n')
                                    file.write('#EXTVLCOPT:http-origin=https://webxzplay.cfd\n')
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
