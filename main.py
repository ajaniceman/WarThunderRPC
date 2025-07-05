import requests
import json
import time
import os
import re
import urllib.parse
import traceback
from PIL import Image
import imagehash
from pypresence import Presence

#region Project Imports
import telemetry # Custom module for War Thunder telemetry API interaction
#endregion

#region Global Configuration & Constants
# Discord Application Client ID for Rich Presence
CLIENT_ID = "1390355314699796520" 

# Directory to save downloaded map images
MAP_PICTURES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mapPictures')
os.makedirs(MAP_PICTURES_DIR, exist_ok=True) # Ensure the directory exists

# Status messages for different game states
STATUS_MESSAGES = {
    telemetry.IN_FLIGHT: "In Flight / In Match",
    telemetry.IN_MENU: "In Hangar / Menu",
    telemetry.NO_MISSION: "Game running, but no active mission",
    telemetry.WT_NOT_RUNNING: "War Thunder is not running",
    telemetry.OTHER_ERROR: "Other error during telemetry fetch"
}

# Mapping of internal country codes to display names
COUNTRY_DISPLAY_MAP = {
    'ussr': 'USSR', 'germ': 'Germany', 'usa': 'USA', 'uk': 'UK', 'jp': 'Japan',
    'fr': 'France', 'it': 'Italy', 'swe': 'Sweden', 'cn': 'China', 'sw': 'Sweden'
}

# List of known country prefixes for vehicle names
COUNTRY_PREFIXES = list(COUNTRY_DISPLAY_MAP.keys())
#endregion

#region RPC & Telemetry Initialization
RPC = Presence(CLIENT_ID)
RPC.connect() # Connect to Discord RPC
telem_interface = telemetry.TelemInterface() # Initialize telemetry interface
# CLOCK_TIMER is no longer a fixed start time, removed.
#endregion

#region State Tracking Variables (for console logging to avoid redundant prints)
_last_map_name = None
_last_vehicle_name = None # Added for explicit vehicle change tracking
_last_objective = None
_last_rpc_state = None
_last_rpc_details = None
_last_rpc_large_image = None
_last_rpc_small_image = None
_last_rpc_large_text = None
_last_rpc_small_text = None
_last_rpc_update_timestamp = 0 # New: Tracks the last time RPC.update was called
#endregion

#region Cache for Battle Ratings
BR_CACHE = {}
#endregion

#region Helper Functions
def get_vehicle_br_from_wiki(vehicle_name_for_url):
    """
    Fetches the Battle Rating (BR) for a given vehicle from the War Thunder Wiki.
    It attempts multiple common URL patterns and uses a specific regex to parse the HTML.
    This method is designed to be robust to common wiki URL and content variations.
    """
    if vehicle_name_for_url in BR_CACHE:
        return BR_CACHE[vehicle_name_for_url]

    stripped_vehicle_name = vehicle_name_for_url.replace("tankModels/", "").replace("planeModels/", "")
    
    # Attempt to remove country prefix for cleaner base name attempts
    parts = stripped_vehicle_name.split('_')
    base_name = '_'.join(parts[1:]) if len(parts) > 1 and parts[0] in COUNTRY_PREFIXES else stripped_vehicle_name

    # Define a list of potential wiki page paths to try
    # These are ordered by common patterns observed on the War Thunder Wiki
    candidate_wiki_paths = []

    # 1. Common pattern: remove country prefix, replace underscores with hyphens, capitalize words
    candidate_wiki_paths.append(base_name.replace('_', '-').title())

    # 2. Specific known full-caps names or unique formats not covered by general title()
    # These are hardcoded overrides for specific vehicle names that don't follow general patterns
    if 'bmp-2m' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('BMP-2M')
    if 'm1a2_sep' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('M1A2_SEP')
    if 't-90m_2020' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('T-90M_(2020)')
    if 't-80bvm' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('T-80BVM')
    if 'tornado_f_3' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('Tornado_F.3')
    if 'mirage_2000_5f' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('Mirage_2000-5F')
    if 'apache_ah_mk_1' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('Apache_AH_Mk.1')
    if 'j_11' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('J-11')
    if 'mi_28nm' in stripped_vehicle_name.lower():
        candidate_wiki_paths.append('Mi-28NM')

    # 3. 'unit/' prefix with the original stripped vehicle name (often used for specific game units)
    candidate_wiki_paths.append(f"unit/{stripped_vehicle_name}")

    # 4. Fallback: original base name with underscores (no title case)
    candidate_wiki_paths.append(base_name)

    # 5. Fallback: base name with underscores and capitalized first letter of each part
    candidate_wiki_paths.append('_'.join([p.capitalize() for p in base_name.split('_')]))

    # Iterate through candidate paths and try to fetch BR
    for wiki_path_name_attempt in list(set(candidate_wiki_paths)): # Use set to avoid duplicate attempts
        final_wiki_url_path = urllib.parse.quote(wiki_path_name_attempt)
        wiki_url = f"https://wiki.warthunder.com/{final_wiki_url_path}"

        try:
            response = requests.get(wiki_url, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            html_content = response.text

            # Regex to find the BR value based on the provided HTML snippet
            br_match = re.search(
                r'<div class="game-unit_br-item">\s*<div class="mode">RB</div>\s*<div class="value">(.*?)</div>\s*</div>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            
            if br_match:
                br_value = br_match.group(1).strip()
                # Remove any HTML tags (like <sup> for footnotes) that might be inside the BR value
                br_value = re.sub(r'<.*?>', '', br_value)
                BR_CACHE[vehicle_name_for_url] = br_value
                return br_value
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            # Ignore timeouts or request errors for this specific URL attempt, try next
            pass
        except Exception as e:
            # Log unexpected parsing errors but continue trying other URLs
            print(f"ERROR: Failed to parse BR for {vehicle_name_for_url} from {wiki_url}: {e}")
    
    # If all attempts fail
    BR_CACHE[vehicle_name_for_url] = "N/A"
    return "N/A"
#endregion

#region Main RPC Update Loop
while True:
    try:
        #region Game State Check
        is_connected = telem_interface.get_telemetry()
        game_running = (telem_interface.status not in [telemetry.WT_NOT_RUNNING, telemetry.OTHER_ERROR])

        if not game_running:
            current_rpc_state = "Not running"
            current_rpc_details = "Waiting for War Thunder..."
            current_rpc_large_image = "logo"
            current_rpc_large_text = "War Thunder"
            current_rpc_small_image = None
            current_rpc_small_text = None

            # Clear _last_map_name when game is not running
            _last_map_name = None 
            _last_vehicle_name = None # Also clear last vehicle name

            # Always send RPC update when game is not running to ensure status is cleared/set
            # Only print to console if there's a change or a periodic update
            if (_last_rpc_state != current_rpc_state or _last_rpc_details != current_rpc_details or
                _last_rpc_large_image != current_rpc_large_image or _last_rpc_large_text != current_rpc_large_text or
                time.time() - _last_rpc_update_timestamp > 15): # Force update every 15 seconds for heartbeat
                
                print(f"War Thunder is {current_rpc_state.lower()}. {current_rpc_details}")
                print(f"RPC Update (Not Running): Large Image='{current_rpc_large_image}', Small Image='{current_rpc_small_image}'")
                
                RPC.update(state=current_rpc_state, details=current_rpc_details, start=int(time.time()), large_image=current_rpc_large_image, large_text=current_rpc_large_text)
                _last_rpc_update_timestamp = int(time.time()) # Update timestamp on successful RPC call
            
            # Update last state variables
            _last_rpc_state, _last_rpc_details, _last_rpc_large_image, _last_rpc_small_image, _last_rpc_large_text, _last_rpc_small_text = \
                current_rpc_state, current_rpc_details, current_rpc_large_image, current_rpc_small_image, current_rpc_large_text, current_rpc_small_text
            
            time.sleep(0.5) # Reduced sleep time
            continue

        # Force is_connected to True if in a recognized hangar/menu state
        if telem_interface.status in [telemetry.IN_MENU, telemetry.NO_MISSION]:
            is_connected = True
        #endregion

        #region Telemetry Data Processing
        # Fetch raw telemetry data
        api_speed_tas = telem_interface.state.get('TAS, km/h', 9999)
        api_throttle1 = telem_interface.state.get('throttle 1, %', 9999)
        api_altitude_h = telem_interface.state.get('H, m', 9999)
        
        isinVehicle = telem_interface.indicators.get('valid', False)
        vehicleName = telem_interface.indicators.get('type', 'Unknown')
        vehicleType = telem_interface.indicators.get('army', 'Unknown')

        mainObjective = "false"
        inMatch = False
        if isinstance(telem_interface.full_telemetry.get("objectives"), list) and len(telem_interface.full_telemetry.get("objectives", [])) > 0:
            inMatch = True # Considered in a match if any objective is present
            mainObjective = telem_interface.full_telemetry["objectives"][0].get('text', "false")

        currentMap = "UNKNOWN"
        map_asset_key = "logo" # Default large image
        if telem_interface.map_info.map_valid:
            currentMap = telem_interface.map_info.grid_info.get('name', 'UNKNOWN') if telem_interface.map_info.grid_info else 'UNKNOWN'
            map_asset_key = currentMap.lower().replace(' ', '_')
            if map_asset_key == "unknown" or not map_asset_key: # Ensure it's not empty or "unknown"
                map_asset_key = "logo"
            
            # Save map image if new and recognized
            map_img_path_for_hash = os.path.join(telemetry.mapinfo.LOCAL_PATH, 'map.jpg')
            # Only attempt to save if the map_asset_key is not 'hangar' and it's a new map
            if os.path.exists(map_img_path_for_hash) and map_asset_key != _last_map_name and map_asset_key != 'hangar':
                try:
                    map_image_for_saving = Image.open(map_img_path_for_hash)
                    save_path = os.path.join(MAP_PICTURES_DIR, f"{map_asset_key}.jpg")
                    map_image_for_saving.save(save_path)
                    _last_map_name = map_asset_key # Update _last_map_name only on successful save
                except Exception as save_e:
                    print(f"Error saving recognized map image: {save_e}")
        else:
            # If map info is not valid, ensure map_asset_key defaults to hangar/logo
            currentMap = "Hangar" # Explicitly set currentMap for hangar context
            map_asset_key = "hangar" # Default to hangar asset
            _last_map_name = None # Clear last map name if map info is invalid
            
        # Process vehicle name for display and wiki lookup
        strippedVehicleName = vehicleName.replace("tankModels/", "").replace("planeModels/", "")
        encodedVehicleName = urllib.parse.quote(strippedVehicleName)

        # Extract country and format vehicle name for display (e.g., "T 90M 2020 (USSR)")
        country_code_display = ""
        base_vehicle_name_for_display = strippedVehicleName
        first_underscore_index = strippedVehicleName.find('_')
        
        if first_underscore_index != -1 and strippedVehicleName[:first_underscore_index] in COUNTRY_PREFIXES:
            country_code_raw = strippedVehicleName[:first_underscore_index]
            base_vehicle_name_for_display = strippedVehicleName[first_underscore_index + 1:]
            country_code_display = f" ({COUNTRY_DISPLAY_MAP.get(country_code_raw, country_code_raw.upper())})"
        
        truncatedVehicleNameForDisplay = base_vehicle_name_for_display.replace('_', ' ').title()

        # Get Battle Rating (BR) dynamically from wiki
        vehicle_br_text = ""
        if strippedVehicleName and strippedVehicleName != 'Unknown' and "DUMMY" not in strippedVehicleName.upper():
            br_value = get_vehicle_br_from_wiki(strippedVehicleName)
            if br_value and br_value != "N/A":
                vehicle_br_text = f"\nBR: {br_value}"
        #endregion

        #region RPC State Determination
        condition_hangar = telem_interface.status in [telemetry.IN_MENU, telemetry.NO_MISSION] or \
                           (telem_interface.status == telemetry.IN_FLIGHT and \
                            abs(api_speed_tas) < 5 and abs(telem_interface.indicators.get('speed', 9999)) < 5 and \
                            api_throttle1 < 5 and api_altitude_h < 100)
        
        condition_in_match_robust = telem_interface.map_info.map_valid and (currentMap != 'Hangar')

        if condition_in_match_robust:
            if inMatch: # Actual in-match with objectives
                if vehicleType == "air":
                    current_rpc_state = f"Piloting a {truncatedVehicleNameForDisplay}"
                    if mainObjective.startswith("Capture and maintain superiority over the airfields") or \
                       mainObjective.startswith("Capture and hold airfields.") or \
                       mainObjective.startswith("Capture and maintain superiority over the air zone") or \
                       mainObjective.startswith("Capture and hold the airfield"):
                        current_rpc_details = f"Air Domination Match on {currentMap}"
                    elif mainObjective.startswith("Destroy the enemy ground vehicles"):
                        current_rpc_details = f"Air Ground Strike Match on {currentMap}"
                    elif mainObjective.startswith("Destroy the highlighted targets"):
                        current_rpc_details = f"Air Frontline Match on {currentMap}"
                    elif mainObjective.startswith("Capture and maintain superiority over the points") or \
                         mainObjective.startswith("Capture the enemy point") or \
                         mainObjective.startswith("Prevent capture of allied point") or \
                         mainObjective.startswith("Capture and keep hold of the point"):
                        current_rpc_details = f"Air/Ground Mixed Battle on {currentMap}"
                    elif mainObjective and mainObjective != "false":
                        current_rpc_details = f"Air Operations Match on {currentMap}"
                    else:
                        current_rpc_details = f"Air Match on {currentMap}" 
                    current_rpc_large_image = map_asset_key
                    current_rpc_large_text = currentMap
                    current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                    current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"

                elif vehicleType == "tank":
                    current_rpc_state = f"Driving a {truncatedVehicleNameForDisplay}"
                    if mainObjective.startswith("Capture and maintain superiority over the points"):
                        current_rpc_details = f"Ground Domination Match on {currentMap}"
                    elif mainObjective.startswith("Capture the enemy point") or \
                         mainObjective.startswith("Prevent the capture of the allied point"):
                        current_rpc_details = f"Ground Battle Match on {currentMap}"
                    elif mainObjective.startswith("Capture and keep hold of the point"):
                        current_rpc_details = f"Ground Conquest Match on {currentMap}"
                    elif mainObjective and mainObjective != "false":
                        current_rpc_details = f"Ground Operations Match on {currentMap}"
                    else:
                        current_rpc_details = f"Ground Match on {currentMap}" # Changed from "Tank Match" to "Ground Match"
                    current_rpc_large_image = map_asset_key
                    current_rpc_large_text = currentMap
                    current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                    current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"

                else: # Other vehicle types in match
                    current_rpc_state = f"{truncatedVehicleNameForDisplay}"
                    current_rpc_details = f"Match on {currentMap}" # Default for other types, can be refined
                    current_rpc_large_image = "logo" # Default to logo if no specific map asset
                    current_rpc_large_text = currentMap
                    current_rpc_small_image = "logo"
                    current_rpc_small_text = f"War Thunder Vehicle{vehicle_br_text}"

            else: # Map valid, not Hangar, but no objectives (e.g., loading screen, test drive)
                if "DUMMY" in vehicleName.upper(): # Common placeholder for loading
                    current_rpc_state = "Loading into a match.."
                    current_rpc_details = f"Match on {currentMap}" 
                    current_rpc_large_image = map_asset_key
                    current_rpc_large_text = currentMap
                    current_rpc_small_image = "logo"
                    current_rpc_small_text = "War Thunder"
                else: # In a match-like state with a specific vehicle, but no active objective
                    current_rpc_state = f"Driving a {truncatedVehicleNameForDisplay}" if vehicleType == "tank" else f"Piloting a {truncatedVehicleNameForDisplay}"
                    # This is the line that needs to be changed for "Ground Match"
                    if vehicleType == "tank":
                        current_rpc_details = f"Ground Match on {currentMap}"
                    else:
                        current_rpc_details = f"{vehicleType.capitalize()} Match on {currentMap}" 
                    current_rpc_large_image = map_asset_key
                    current_rpc_large_text = currentMap
                    current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                    current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"

        elif condition_hangar: # In hangar or menu
            current_rpc_state = "In the hangar"
            current_rpc_large_image = "hangar" # Always use "hangar" asset in hangar
            current_rpc_large_text = "In the Hangar"
            
            if isinVehicle and strippedVehicleName and strippedVehicleName != 'Unknown' and "DUMMY" not in strippedVehicleName.upper():
                current_rpc_details = f"Looking at {truncatedVehicleNameForDisplay}"
                current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"
            else:
                current_rpc_details = "Browsing vehicles..."
                current_rpc_small_image = None
                current_rpc_small_text = None

        else: # Unhandled or transient states
            current_rpc_state = "In-game"
            current_rpc_details = "Unknown activity"
            current_rpc_large_image = "logo"
            current_rpc_large_text = "War Thunder"
            current_rpc_small_image = None
            current_rpc_small_text = None
        #endregion

        #region Update Discord Rich Presence
        # Determine if a console log is needed (only on actual content change or periodic heartbeat)
        log_to_console = False
        if (_last_rpc_state != current_rpc_state or _last_rpc_details != current_rpc_details or
            _last_rpc_large_image != current_rpc_large_image or _last_rpc_small_image != current_rpc_small_image or
            _last_rpc_large_text != current_rpc_large_text or current_rpc_small_text != _last_rpc_small_text or
            _last_vehicle_name != strippedVehicleName or # Explicit check for vehicle name change
            time.time() - _last_rpc_update_timestamp > 15): # Force update every 15 seconds for console log
            log_to_console = True

        # Always send RPC update when game is running and connected
        if is_connected:
            # Add a small delay before updating RPC, especially in hangar state
            if condition_hangar:
                time.sleep(1) 

            RPC.update(
                state=current_rpc_state,
                details=current_rpc_details,
                start=int(time.time()), # Update start time on every RPC update
                large_image=current_rpc_large_image,
                large_text=current_rpc_large_text,
                small_image=current_rpc_small_image,
                small_text=current_rpc_small_text
            )
            
            if log_to_console:
                print(f"Updated Presence: State='{current_rpc_state}', Details='{current_rpc_details}', Vehicle='{truncatedVehicleNameForDisplay}{country_code_display}', BR='{vehicle_br_text.strip()}'")
                print(f"RPC Update Sent: Large Image='{current_rpc_large_image}', Small Image='{current_rpc_small_image}'")

            _last_rpc_update_timestamp = int(time.time()) # Update timestamp on successful RPC call


        # Update last state variables for the next loop iteration
        _last_rpc_state = current_rpc_state
        _last_rpc_details = current_rpc_details
        _last_rpc_large_image = current_rpc_large_image
        _last_rpc_small_image = current_rpc_small_image
        _last_rpc_large_text = current_rpc_large_text
        _last_rpc_small_text = current_rpc_small_text
        _last_vehicle_name = strippedVehicleName # Update last vehicle name
        #endregion

    #region Error Handling for Main Loop
    except Exception as e:
        print(f"An unexpected error occurred in the main loop: {e}")
        traceback.print_exc()
        # Fallback RPC state in case of an error
        current_rpc_state = "Error occurred"
        current_rpc_details = "Waiting for game to restart"
        current_rpc_large_image = "logo"
        current_rpc_large_text = "War Thunder"
        current_rpc_small_image = None
        current_rpc_small_text = None
        
        # Clear _last_map_name and _last_vehicle_name on error
        _last_map_name = None 
        _last_vehicle_name = None

        # Always send RPC update on error to clear/set status, but only log if changed or periodic
        if (_last_rpc_state != current_rpc_state or _last_rpc_details != current_rpc_details or
            _last_rpc_large_image != current_rpc_large_image or _last_rpc_large_text != current_rpc_large_text or
            time.time() - _last_rpc_update_timestamp > 15): # Force update every 15 seconds even on error
            
            print(f"RPC Update (Error State): Large Image='{current_rpc_large_image}', Small Image='{current_rpc_small_image}'")
            RPC.update(state=current_rpc_state, details=current_rpc_details, start=int(time.time()), large_image=current_rpc_large_image, large_text=current_rpc_large_text)
            _last_rpc_update_timestamp = int(time.time()) # Update timestamp on successful RPC call
        
        _last_rpc_state = current_rpc_state
        _last_rpc_details = current_rpc_details
        _last_rpc_large_image = current_rpc_large_image
        _last_rpc_small_image = current_rpc_small_image
        _last_rpc_large_text = current_rpc_large_text
        _last_rpc_small_text = current_rpc_small_text
        
    time.sleep(0.5) # Reduced sleep time
    #endregion
