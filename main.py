import os
import re
import urllib.parse
import traceback
import sys
import time
import argparse
import queue
import json # Added: Import json for loading config in non-frozen mode

# Use a try-except block for critical external imports to provide better feedback
try:
    import requests
    from PIL import Image
    import imagehash
    from pypresence import Presence, exceptions
    import html
except ImportError as e:
    # Log the import error if the logger is available, otherwise print to stderr
    if 'logger_config' in sys.modules and hasattr(sys.modules['logger_config'], 'logger'):
        sys.modules['logger_config'].logger.error(f"FATAL ERROR: Missing required module. Please ensure all dependencies are installed and bundled correctly: {e}")
        sys.modules['logger_config'].logger.error(traceback.format_exc())
    else:
        print(f"FATAL ERROR: Missing required module. Please ensure all dependencies are installed and bundled correctly: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    sys.exit(1) # Exit if critical imports fail

#region Project Imports
import telemetry # Custom module for War Thunder telemetry API interaction
import logger_config # Import the logging configuration
import logging # Added: Import logging module here for getLogger
#endregion

# Get the logger instance
logger = logging.getLogger('WarThunderRPC')

# Global flag to control the RPC loop (used by gui_launcher to stop)
_rpc_running = False

# Global RPC client instance (will be initialized in run_rpc)
RPC = None

#region Global Configuration & Constants
# Directory to save downloaded map images
# This is the primary definition for mapPictures directory.
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
    'ussr': 'USSR', 'germ': 'Germany', 'us': 'USA', 'uk': 'UK', 'jp': 'Japan',
    'fr': 'France', 'it': 'Italy', 'swe': 'Sweden', 'cn': 'China', 'sw': 'Sweden'
}

# List of known country prefixes for vehicle names
COUNTRY_PREFIXES = list(COUNTRY_DISPLAY_MAP.keys())

# Default message templates (will be overridden by custom_message_templates if provided)
DEFAULT_MESSAGE_TEMPLATES = {
    'hangar_state': "In the hangar",
    'hangar_details': "Looking at {vehicle_display_name}",
    'hangar_details_browsing': "Browsing vehicles...",
    'match_state': "{vehicle_type_action} a {vehicle_display_name}",
    'match_details': "{match_type} on {map_display_name}",
    'loading_match_state': "Loading into a match..",
    'loading_match_details': "Loading into a match on {map_display_name}..",
    'test_drive_state': "{vehicle_type_action} a {vehicle_display_name} (Test Drive)",
    'test_drive_details': "In Test Drive on Western Europe",
    'vehicle_br_text': "BR: {br_value}",
    'vehicle_country_text': "({country_display_name})",
}
#endregion

#region State Tracking Variables (for console logging to avoid redundant prints)
_last_map_name = None
_last_vehicle_name = None
_last_objective = None
_last_rpc_state = None
_last_rpc_details = None
_last_rpc_large_image = None
_last_rpc_small_image = None
_last_rpc_large_text = None
_last_rpc_small_text = None
_last_rpc_update_timestamp = 0
_current_activity_start_time = None
#endregion

#region Cache for Battle Ratings and Display Names
BR_CACHE = {}
#endregion

#region Helper Functions
def get_vehicle_br_from_wiki(vehicle_name_for_url):
    """
    Fetches the Battle Rating (BR) and the official display name for a given vehicle from the War Thunder Wiki.
    It attempts multiple common URL patterns and uses regex to parse the HTML.
    
    Args:
        vehicle_name_for_url (str): The vehicle name formatted for URL lookup (e.g., "ussr_bmp_2m").

    Returns:
        tuple: A tuple containing (br_value, display_name_from_wiki).
               br_value will be "N/A" if not found.
               display_name_from_wiki will be None if not found.
    """
    if vehicle_name_for_url in BR_CACHE:
        return BR_CACHE[vehicle_name_for_url]

    stripped_vehicle_name = vehicle_name_for_url.replace("tankModels/", "").replace("planeModels/", "")
    
    # Attempt to remove country prefix for cleaner base name attempts
    parts = stripped_vehicle_name.split('_')
    base_name = '_'.join(parts[1:]) if len(parts) > 1 and parts[0] in COUNTRY_PREFIXES else stripped_vehicle_name

    # Define a list of potential wiki page paths to try
    candidate_wiki_paths = []

    candidate_wiki_paths.append(base_name.replace('_', '-').title())
    candidate_wiki_paths.append(f"unit/{stripped_vehicle_name}")
    candidate_wiki_paths.append(base_name)
    candidate_wiki_paths.append('_'.join([p.capitalize() for p in base_name.split('_')]))

    for wiki_path_name_attempt in list(set(candidate_wiki_paths)):
        final_wiki_url_path = urllib.parse.quote(wiki_path_name_attempt)
        wiki_url = f"https://wiki.warthunder.com/{final_wiki_url_path}"

        br_value = "N/A"
        display_name_from_wiki = None

        try:
            response = requests.get(wiki_url, timeout=20) 
            response.raise_for_status()
            html_content = response.text

            br_match = re.search(
                r'<div class="game-unit_br-item">\s*<div class="mode">RB</div>\s*<div class="value">(.*?)</div>\s*</div>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            if br_match:
                br_value = br_match.group(1).strip()
                br_value = re.sub(r'<.*?>', '', br_value)

            game_unit_name_match = re.search(
                r'<div class="game-unit_name">(.*?)</div>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            if game_unit_name_match:
                raw_name = game_unit_name_match.group(1).strip()
                cleaned_name = html.unescape(re.sub(r'<.*?>', '', raw_name))
                cleaned_name = cleaned_name.replace('\xa0', ' ')
                display_name_from_wiki = cleaned_name.strip()
            else:
                name_match = re.search(
                    r'<h1[^>]*id="firstHeading"[^>]*>(.*?)<\/h1>',
                    html_content,
                    re.DOTALL | re.IGNORECASE
                )
                if name_match:
                    raw_name = name_match.group(1).strip()
                    cleaned_name = html.unescape(re.sub(r'<.*?>', '', raw_name))
                    cleaned_name = cleaned_name.replace('\xa0', ' ')
                    display_name_from_wiki = cleaned_name.strip()

            if br_value != "N/A" or display_name_from_wiki is not None:
                BR_CACHE[vehicle_name_for_url] = (br_value, display_name_from_wiki)
                return br_value, display_name_from_wiki

        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            logger.debug(f"Timeout or request error fetching BR/Name for {vehicle_name_for_url} from {wiki_url}")
            pass
        except Exception as e:
            logger.error(f"Failed to parse BR/Name for {vehicle_name_for_url} from {wiki_url}: {e}")
            logger.debug(traceback.format_exc())
    
    BR_CACHE[vehicle_name_for_url] = ("N/A", None)
    return "N/A", None

def _load_config_for_main():
    """
    Loads configuration from config.json for main.py when not run as frozen.
    This is a simplified version for main.py's direct use.
    """
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding config.json: {e}")
        except Exception as e:
            logger.error(f"Error loading config.json: {e}")
    return {}

#endregion

def run_rpc(client_id: str = None, custom_message_templates: dict = None):
    """
    Main function to run the War Thunder Discord Rich Presence.
    This function contains the continuous loop for updating RPC.
    
    Args:
        client_id (str): The Discord Application Client ID.
        custom_message_templates (dict): Dictionary of custom message templates.
    """
    global _last_map_name, _last_vehicle_name, _last_objective, \
           _last_rpc_state, _last_rpc_details, _last_rpc_large_image, \
           _last_rpc_small_image, _last_rpc_large_text, _last_rpc_small_text, \
           _last_rpc_update_timestamp, _current_activity_start_time, _rpc_running, RPC

    logger.debug("Console logging level controlled by GUI.")

    logger.debug(f"sys.path in run_rpc: {sys.path}")
    logger.debug(f"Current working directory in run_rpc: {os.getcwd()}")

    if client_id is None:
        logger.error("Client ID was not provided to run_rpc. Exiting.")
        return

    RPC = Presence(client_id)

    telem_interface = telemetry.TelemInterface()
    
    # Load templates: prioritize passed templates, then config file, then defaults
    current_templates = DEFAULT_MESSAGE_TEMPLATES.copy()
    if not custom_message_templates: # If no templates passed (e.g., when run directly)
        config_from_file = _load_config_for_main()
        for key, value in config_from_file.items():
            if key in current_templates: # Only update known template keys
                current_templates[key] = value
    else: # If templates were passed from GUI (frozen mode)
        current_templates.update(custom_message_templates)

    logger.debug(f"Using message templates: {current_templates}")

    try:
        logger.info("Attempting to connect to Discord RPC...")
        RPC.connect()
        logger.info("Successfully connected to Discord RPC.")
    except exceptions.InvalidID:
        logger.error(f"Invalid CLIENT_ID '{client_id}'. Please ensure it's correct and configured in Discord Developer Portal.")
        return
    except Exception as e:
        logger.error(f"Failed to connect to Discord RPC: {e}. Is Discord running?")
        logger.debug(traceback.format_exc())
        return

    _rpc_running = True

    while _rpc_running:
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
                _current_activity_start_time = None

                _last_map_name = None 
                _last_vehicle_name = None

                if (_last_rpc_state != current_rpc_state or _last_rpc_details != current_rpc_details or
                    _last_rpc_large_image != current_rpc_large_image or _last_rpc_large_text != current_rpc_large_text or
                    time.time() - _last_rpc_update_timestamp > 30): # Force update every 30 seconds for heartbeat
                    
                    logger.info(f"War Thunder is {current_rpc_state.lower()}. {current_rpc_details}")
                    
                    payload = {
                        "state": current_rpc_state,
                        "details": current_rpc_details,
                        "start": int(time.time()),
                        "large_image": current_rpc_large_image,
                        "large_text": current_rpc_large_text,
                        "small_image": current_rpc_small_image,
                        "small_text": current_rpc_small_text
                    }
                    logger.debug(f"Attempting RPC update with payload (Not Running): {payload}")
                    
                    try:
                        RPC.update(**payload)
                        logger.debug("RPC update successful for 'Not Running' state.")
                    except exceptions.PipeClosed:
                        logger.error("Discord pipe closed. Discord might have been closed or restarted. Attempting to reconnect on next loop.")
                        RPC = None
                    except Exception as rpc_e:
                        logger.error(f"Failed to send RPC update for 'Not Running' state: {rpc_e}")
                        logger.debug(traceback.format_exc())

                    _last_rpc_update_timestamp = int(time.time())

                _last_rpc_state, _last_rpc_details, _last_rpc_large_image, _last_rpc_small_image, _last_rpc_large_text, _last_rpc_small_text = \
                    current_rpc_state, current_rpc_details, current_rpc_large_image, current_rpc_small_image, current_rpc_large_text, current_rpc_small_text
                
                time.sleep(1)
                continue

            # Log the current connection status before the RPC update logic
            logger.debug(f"Telemetry Connection Status: is_connected={is_connected}, telem_interface.status={STATUS_MESSAGES.get(telem_interface.status, 'Unknown Status')}")

            #region Telemetry Data Processing
            api_speed_tas = telem_interface.state.get('TAS, km/h', 9999)
            api_throttle1 = telem_interface.state.get('throttle 1, %', 9999)
            api_altitude_h = telem_interface.state.get('H, m', 9999)
            
            isinVehicle = telem_interface.indicators.get('valid', False)
            vehicleName = telem_interface.indicators.get('type', 'Unknown')
            vehicleType = telem_interface.indicators.get('army', 'Unknown')

            mainObjective = "false"
            inMatch = False
            if isinstance(telem_interface.full_telemetry.get("objectives"), list) and len(telem_interface.full_telemetry.get("objectives", [])) > 0:
                inMatch = True
                mainObjective = telem_interface.full_telemetry["objectives"][0].get('text', "false")

            currentMap = "UNKNOWN"
            map_asset_key = "logo"
            if telem_interface.map_info.map_valid:
                currentMap = telem_interface.map_info.grid_info.get('name', 'UNKNOWN') if telem_interface.map_info.grid_info else 'UNKNOWN'
                map_asset_key = currentMap.lower().replace(' ', '_')
                if map_asset_key == "unknown" or not map_asset_key:
                    map_asset_key = "logo"
                
                map_img_path_for_hash = os.path.join(telemetry.mapinfo.LOCAL_PATH, 'map.jpg')
                if os.path.exists(map_img_path_for_hash) and map_asset_key != _last_map_name and map_asset_key != 'hangar':
                    try:
                        map_image_for_saving = Image.open(map_img_path_for_hash)
                        # Use the MAP_PICTURES_DIR defined at the top of main.py
                        save_path = os.path.join(MAP_PICTURES_DIR, f"{map_asset_key}.jpg") 
                        map_image_for_saving.save(save_path)
                    except Exception as save_e:
                        logger.error(f"Error saving recognized map image: {save_e}")
            else:
                currentMap = "Hangar"
                map_asset_key = "hangar"
                _last_map_name = None
                
            strippedVehicleName = vehicleName.replace("tankModels/", "").replace("planeModels/", "")
            encodedVehicleName = urllib.parse.quote(strippedVehicleName)

            br_value, wiki_display_name = "N/A", None
            if strippedVehicleName and strippedVehicleName != 'Unknown' and "DUMMY" not in strippedVehicleName.upper():
                br_value, wiki_display_name = get_vehicle_br_from_wiki(strippedVehicleName)

            truncatedVehicleNameForDisplay = ""
            country_code_display = ""
            country_display_name_raw = ""
            
            parts = strippedVehicleName.split('_')
            if len(parts) > 1 and parts[0] in COUNTRY_PREFIXES:
                country_code_raw = parts[0]
                country_display_name_raw = COUNTRY_DISPLAY_MAP.get(country_code_raw, country_code_raw.upper())
                country_code_display = current_templates['vehicle_country_text'].format(country_display_name=country_display_name_raw)
            else:
                country_code_display = ""

            if wiki_display_name:
                truncatedVehicleNameForDisplay = wiki_display_name
            else:
                base_name_for_display = strippedVehicleName
                if len(parts) > 1 and parts[0] in COUNTRY_PREFIXES:
                    base_name_for_display = '_'.join(parts[1:])
                truncatedVehicleNameForDisplay = base_name_for_display.replace('_', ' ').title()


            vehicle_br_text = ""
            if br_value and br_value != "N/A":
                vehicle_br_text = current_templates['vehicle_br_text'].format(br_value=br_value)
            #endregion

            #region RPC State Determination
            condition_hangar = telem_interface.status in [telemetry.IN_MENU, telemetry.NO_MISSION] or \
                               (telem_interface.status == telemetry.IN_FLIGHT and \
                                abs(api_speed_tas) < 5 and abs(telem_interface.indicators.get('speed', 9999)) < 5 and \
                                api_throttle1 < 5 and api_altitude_h < 100)
            
            condition_in_match_robust = telem_interface.map_info.map_valid and (currentMap != 'Hangar')

            # Data for template formatting
            template_data = {
                'vehicle_display_name': truncatedVehicleNameForDisplay,
                'map_display_name': currentMap,
                'br_value': br_value,
                'country_display_name': country_display_name_raw,
                'vehicle_type_action': "", # Will be set below
                'match_type': "", # Will be set below
            }

            if currentMap == "Test Drive":
                if vehicleType == "tank":
                    template_data['vehicle_type_action'] = "Driving"
                elif vehicleType == "air":
                    template_data['vehicle_type_action'] = "Piloting"
                else:
                    template_data['vehicle_type_action'] = "In" # Generic for unknown type in test drive

                current_rpc_state = current_templates['test_drive_state'].format(**template_data)
                current_rpc_details = current_templates['test_drive_details'].format(**template_data)
                current_rpc_large_image = "western_europe" 
                current_rpc_large_text = "Western Europe"
                current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"

            elif condition_in_match_robust:
                is_air_vehicle = (vehicleType == "air" or 
                                  (vehicleType == "Unknown" and telem_interface.indicators.get('icon', '').lower() in ['bomber', 'fighter', 'assault', 'heavy_fighter', 'attacker']) or
                                  (vehicleType == "Unknown" and telem_interface.indicators.get('type', '').lower().startswith('plane'))) 
                
                is_tank_vehicle = (vehicleType == "tank")
                
                is_naval_vehicle = (vehicleType == "ship" or
                                    (vehicleType == "Unknown" and telem_interface.indicators.get('icon', '').lower() in ['ship', 'torpedoboat']) or
                                    (vehicleType == "Unknown" and telem_interface.indicators.get('type', '').lower().startswith('ship'))) 

                if is_air_vehicle:
                    template_data['vehicle_type_action'] = "Piloting"
                elif is_tank_vehicle:
                    template_data['vehicle_type_action'] = "Driving"
                elif is_naval_vehicle:
                    template_data['vehicle_type_action'] = "Commanding"
                else:
                    template_data['vehicle_type_action'] = "In" # Generic for unknown type in match

                current_rpc_state = current_templates['match_state'].format(**template_data)

                if inMatch:
                    if is_air_vehicle:
                        if mainObjective.startswith("Capture and maintain superiority over the airfields") or \
                           mainObjective.startswith("Capture and hold airfields.") or \
                           mainObjective.startswith("Capture and maintain superiority over the air zone") or \
                           mainObjective.startswith("Capture and hold the airfield"):
                            template_data['match_type'] = "Air Domination Match"
                        elif mainObjective.startswith("Destroy the enemy ground vehicles"):
                            template_data['match_type'] = "Air Ground Strike Match"
                        elif mainObjective.startswith("Destroy the highlighted targets"):
                            template_data['match_type'] = "Air Frontline Match"
                        elif mainObjective.startswith("Capture and maintain superiority over the points") or \
                             mainObjective.startswith("Capture the enemy point") or \
                             mainObjective.startswith("Prevent capture of allied point") or \
                             mainObjective.startswith("Capture and keep hold of the point"):
                            template_data['match_type'] = "Air/Ground Mixed Battle"
                        elif mainObjective and mainObjective != "false":
                            template_data['match_type'] = "Air Operations Match"
                        else:
                            template_data['match_type'] = "Air Match"
                    elif is_tank_vehicle:
                        if mainObjective.startswith("Capture and maintain superiority over the points"):
                            template_data['match_type'] = "Ground Domination Match"
                        elif mainObjective.startswith("Capture the enemy point") or \
                             mainObjective.startswith("Prevent the capture of the allied point"):
                            template_data['match_type'] = "Ground Battle Match"
                        elif mainObjective.startswith("Capture and keep hold of the point"):
                            template_data['match_type'] = "Ground Conquest Match"
                        elif mainObjective and mainObjective != "false":
                            template_data['match_type'] = "Ground Operations Match"
                        else:
                            template_data['match_type'] = "Ground Match"
                    elif is_naval_vehicle:
                        if mainObjective.startswith("Capture and maintain superiority over the points"):
                            template_data['match_type'] = "Naval Domination Match"
                        elif mainObjective.startswith("Capture the enemy point") or \
                           mainObjective.startswith("Prevent capture of allied point") or \
                           mainObjective.startswith("Capture and keep hold of the point"):
                            template_data['match_type'] = "Naval Domination Match"
                        elif mainObjective and mainObjective != "false":
                            template_data['match_type'] = "Naval Operations Match"
                        else:
                            template_data['match_type'] = "Naval Match"
                    else:
                        template_data['match_type'] = "Match"
                    current_rpc_details = current_templates['match_details'].format(**template_data)
                else:
                    if "DUMMY" in vehicleName.upper():
                        current_rpc_state = current_templates['loading_match_state'].format(**template_data)
                        current_rpc_details = current_templates['loading_match_details'].format(**template_data)
                    elif is_air_vehicle:
                        template_data['match_type'] = "Air Match"
                        current_rpc_details = current_templates['match_details'].format(**template_data)
                    elif is_tank_vehicle:
                        template_data['match_type'] = "Ground Match"
                        current_rpc_details = current_templates['match_details'].format(**template_data)
                    elif is_naval_vehicle:
                        template_data['match_type'] = "Naval Match"
                        current_rpc_details = current_templates['match_details'].format(**template_data)
                    else:
                        template_data['match_type'] = "Match"
                        current_rpc_details = current_templates['match_details'].format(**template_data)

                current_rpc_large_image = map_asset_key
                current_rpc_large_text = currentMap
                current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"

            elif condition_hangar:
                current_rpc_state = current_templates['hangar_state'].format(**template_data)
                current_rpc_large_image = "hangar"
                current_rpc_large_text = "In the Hangar"
                
                if isinVehicle and strippedVehicleName and strippedVehicleName != 'Unknown' and "DUMMY" not in strippedVehicleName.upper():
                    current_rpc_details = current_templates['hangar_details'].format(**template_data)
                    current_rpc_small_image = f"https://encyclopedia.warthunder.com/i/images/{encodedVehicleName}.png"
                    current_rpc_small_text = f"{truncatedVehicleNameForDisplay}{country_code_display}{vehicle_br_text}"
                else:
                    current_rpc_details = current_templates['hangar_details_browsing'].format(**template_data)
                    current_rpc_small_image = None
                    current_rpc_small_text = None

            else:
                current_rpc_state = "In-game (Unknown State)"
                current_rpc_details = "Waiting for War Thunder data..."
                current_rpc_large_image = "logo"
                current_rpc_large_text = "War Thunder"
                current_rpc_small_image = None
                current_rpc_small_text = None
            #endregion

            #region Update Discord Rich Presence
            log_to_console = False
            
            current_activity_signature = (
                current_rpc_state,
                current_rpc_details,
                current_rpc_large_image,
                current_rpc_small_image,
                current_rpc_large_text,
                current_rpc_small_text
            )

            last_activity_signature = (
                _last_rpc_state,
                _last_rpc_details,
                _last_rpc_large_image,
                _last_rpc_small_image,
                _last_rpc_large_text,
                _last_rpc_small_text
            )

            if current_activity_signature != last_activity_signature:
                _current_activity_start_time = int(time.time())
                log_to_console = True
                logger.info("Activity changed, resetting timer.")
            elif _current_activity_start_time is None:
                _current_activity_start_time = int(time.time())
                log_to_console = True
                logger.info("Initial activity detected, starting timer.")
            elif time.time() - _last_rpc_update_timestamp > 30:
                log_to_console = True


            if is_connected:
                if telem_interface.status in [telemetry.IN_MENU, telemetry.NO_MISSION]:
                    time.sleep(1) 

                payload_to_log = {
                    "state": current_rpc_state,
                    "details": current_rpc_details,
                    "start": _current_activity_start_time,
                    "large_image": current_rpc_large_image,
                    "large_text": current_rpc_large_text,
                    "small_image": current_rpc_small_image,
                    "small_text": current_rpc_small_text
                }
                
                if log_to_console:
                    logger.debug(f"Attempting RPC update with payload: {payload_to_log}") 
                
                try:
                    RPC.update(**payload_to_log)
                    if log_to_console:
                        logger.debug("RPC update successful.") 
                except exceptions.PipeClosed:
                    logger.error("Discord pipe closed. Discord might have been closed or restarted. Attempting to reconnect on next loop.")
                    RPC = None
                except Exception as rpc_e:
                    logger.error(f"Failed to send RPC update: {rpc_e}")
                    logger.debug(traceback.format_exc())
                
                if log_to_console:
                    logger.info(f"Updated Presence: State='{current_rpc_state}', Details='{current_rpc_details}'")
                    logger.debug(f"Vehicle='{truncatedVehicleNameForDisplay}{country_code_display}', BR='{vehicle_br_text.strip()}'")
                    logger.debug(f"RPC Update Sent: Large Image='{current_rpc_large_image}', Small Image='{current_rpc_small_image}'") 

                _last_rpc_update_timestamp = int(time.time())

            _last_rpc_state = current_rpc_state
            _last_rpc_details = current_rpc_details
            _last_rpc_large_image = current_rpc_large_image
            _last_rpc_small_image = current_rpc_small_image
            _last_rpc_large_text = current_rpc_large_text
            _last_rpc_small_text = current_rpc_small_text
            _last_vehicle_name = strippedVehicleName
            #endregion

        #region Error Handling for Main Loop
        except Exception as e:
            logger.error(f"An unexpected error occurred in the main loop: {e}")
            logger.debug(traceback.format_exc())
            
            current_rpc_state = "Error occurred"
            current_rpc_details = "Waiting for game to restart"
            current_rpc_large_image = "logo"
            current_rpc_large_text = "War Thunder"
            current_rpc_small_image = None
            current_rpc_small_text = None
            _current_activity_start_time = None
            
            _last_map_name = None 
            _last_vehicle_name = None

            if (_last_rpc_state != current_rpc_state or _last_rpc_details != current_rpc_details or
                _last_rpc_large_image != current_rpc_large_image or _last_rpc_large_text != current_rpc_large_text or
                time.time() - _last_rpc_update_timestamp > 30):
                
                logger.info(f"RPC Update (Error State): Large Image='{current_rpc_large_image}', Small Image='{current_rpc_small_image}'")
                payload = {
                    "state": current_rpc_state,
                    "details": current_rpc_details,
                    "start": int(time.time()),
                    "large_image": current_rpc_large_image,
                    "large_text": current_rpc_large_text,
                    "small_image": current_rpc_small_image,
                    "small_text": current_rpc_small_text
                }
                logger.debug(f"RPC Payload (Error State): {payload}")
                try:
                    RPC.update(**payload)
                    logger.debug("RPC update successful for 'Error' state.")
                except exceptions.PipeClosed:
                    logger.error("Discord pipe closed during error state. Attempting to reconnect on next loop.")
                    RPC = None
                except Exception as rpc_e:
                    logger.error(f"Failed to send RPC update for 'Error' state: {rpc_e}")
                    logger.debug(traceback.format_exc())

                _last_rpc_update_timestamp = int(time.time())
            
            _last_rpc_state = current_rpc_state
            _last_rpc_details = current_rpc_details
            _last_rpc_large_image = current_rpc_large_image
            _last_rpc_small_image = current_rpc_small_image
            _last_rpc_large_text = current_rpc_large_text
            _last_rpc_small_text = current_rpc_small_text
            
        time.sleep(1)
    logger.info("RPC loop terminated.")
    try:
        if RPC:
            RPC.close()
            logger.info("Disconnected from Discord RPC.")
    except Exception as e:
        logger.error(f"Error disconnecting from Discord RPC: {e}")
        logger.debug(traceback.format_exc())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="War Thunder RPC Script")
    parser.add_argument("--client-id", type=str, help="Discord Application Client ID")
    args = parser.parse_args()

    # When main.py is run directly (not via gui_launcher), it will load its own config
    # The custom_message_templates will be None in this case, triggering the _load_config_for_main
    run_rpc(client_id=args.client_id)
