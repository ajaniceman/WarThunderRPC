import requests
import json
import time
import os 
import hashlib 
from datetime import datetime
from pypresence import Presence
from typing import Dict, Any, Optional, Tuple, Callable
from urllib.parse import urlparse 

# ==============================================================================
# --- FILE PATH UTILITY ---
def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    try:
        # PyInstaller extracts resources to a temp folder and sets this path
        base_path = os.sys._MEIPASS
    except AttributeError:
        # Fallback for when running the script directly (development environment)
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)
# ==============================================================================

# ==============================================================================
# --- LOCAL MODULE IMPORTS ---
from scrape_vehicle_name import get_vehicle_name 
# Note: map_metadata.py is no longer needed as map data is loaded from config.json
# ==============================================================================

# Cache to store official scraped data (name, br) to avoid repeated scraping
VEHICLE_NAME_CACHE: Dict[str, Tuple[str, str]] = {}
LAST_VEHICLE_ID: Optional[str] = None

# Manual mapping for complex vehicle IDs that require specific in-game naming
VEHICLE_DISPLAY_MAP: Dict[str, str] = {
  # 'f_16a_block_10': 'F-16A', 
}

# Global dictionary to hold the map hashes loaded from config.json
GLOBAL_MAP_HASHES: Dict[str, str] = {}

# ==============================================================================
# --- Configuration File Path ---
CONFIG_FILE = "config.json"
# ==============================================================================

# --- WAR THUNDER MONITOR CONFIGURATION ---
WAR_THUNDER_API_URL = "http://127.0.0.1:8111"
POLL_INTERVAL_SECONDS = 5.0 
VEHICLE_IMAGE_BASE_URL = "https://static.encyclopedia.warthunder.com/images/"

# API Endpoints
ENDPOINTS = {
  "state": f"{WAR_THUNDER_API_URL}/state",
  "indicators": f"{WAR_THUNDER_API_URL}/indicators",
  "mission": f"{WAR_THUNDER_API_URL}/mission.json"
}

# --- GITHUB URL CONFIGURATION (FOR AUTO-GENERATING RAW MAP LINKS) ---
# IMPORTANT: This must be the raw base URL for your map images folder.
# Example: "https://raw.githubusercontent.com/ajaniceman/WarThunderRPC/main/mapPictures/"
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/ajaniceman/WarThunderRPC/main/mapPictures/"
# Default map image extension
MAP_IMAGE_EXTENSION = ".jpg"


# ==============================================================================
# --- MAP DETECTION CONFIGURATION (SHA256 LOOKUP) ---
MAP_IMAGE_URL = f"{WAR_THUNDER_API_URL}/map.img"

def get_map_image_hash() -> Optional[str]:
  """
  Fetches the map image data from /map.img and returns its SHA256 hash.
  """
  try:
    response = requests.get(MAP_IMAGE_URL, timeout=1.5)
    response.raise_for_status()
    
    if response.content:
      # We use SHA256 hash on the raw image bytes
      return hashlib.sha256(response.content).hexdigest()
    
    return None
  except requests.exceptions.RequestException:
    return None

def lookup_map_name(sha256_hash: Optional[str]) -> str:
  """
  Looks up the map hash in the configuration. 
  Returns the associated value (URL or Discord Asset Key) or a diagnostic string.
  """
  if sha256_hash:
    map_value = GLOBAL_MAP_HASHES.get(sha256_hash)
    
    if map_value is not None:
      # Returns the URL, a clean asset key, or an empty string for manual cleanup
      return map_value if map_value != "" else "Unknown Map (Needs Update)"
      
    # Hash is not in config, which is handled by the auto-add logic in the main loop
    return f"Unknown Map (Hash: {sha256_hash[:8]}...)"
    
  return "Not in Mission"
# ==============================================================================

def is_url(s: str) -> bool:
  """Checks if a string appears to be a full URL."""
  return s.startswith("http://") or s.startswith("https://")


# --- Configuration Loading/Saving Functions ---

def save_config(config_data: Dict[str, Any]):
    """Saves the current configuration data back to config.json."""
    # Use resource_path() for the path
    config_path = resource_path(CONFIG_FILE) 
    try:
        with open(config_path, 'w') as f: # <- Uses config_path now
            json.dump(config_data, f, indent=4)
        print(f"\u2705 Configuration saved successfully to {CONFIG_FILE}.")
    except IOError as e:
        print(f"\u274C Error saving configuration to {CONFIG_FILE}. Error: {e}")

def load_config() -> Optional[str]:
  """Loads APP_ID and map hashes from config.json."""
  global GLOBAL_MAP_HASHES
  
  app_id = None
  config = {}

  config_path = resource_path(CONFIG_FILE)
  
  # 1. Try to load existing configuration file
  if os.path.exists(config_path):
    try:
      with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        app_id = config.get("APP_ID")
        GLOBAL_MAP_HASHES = config.get("MAP_HASHES", {}) 
        
        if app_id:
          print(f"\u2705 Loaded Discord Application ID from {CONFIG_FILE}.")
        if GLOBAL_MAP_HASHES:
          print(f"\u2705 Loaded {len(GLOBAL_MAP_HASHES)} map hashes from {CONFIG_FILE}.")
          
    except (json.JSONDecodeError, IOError):
      print(f"\u274C Error reading or decoding {CONFIG_FILE}. Starting fresh configuration.")
      config = {}
  
  # 2. If ID is not loaded, prompt the user (omitted for Canvas environment)
  if not app_id and "__app_id" in globals():
    app_id = globals()["__app_id"]
    
    # Save config if MAP_HASHES key is missing
    if "MAP_HASHES" not in config:
      config["APP_ID"] = app_id
      config["MAP_HASHES"] = GLOBAL_MAP_HASHES
      save_config(config)

  # Note: In the final deployment, this function would handle user input if run locally.
  # We rely on the Canvas providing the ID or the user editing config.json.
  
  return app_id

# --- Helper Functions ---

def get_data(endpoint_name):
  """Fetches JSON data from a specified War Thunder API endpoint with error handling."""
  url = ENDPOINTS.get(endpoint_name)
  if not url:
    return None
  try:
    response = requests.get(url, timeout=1.5) 
    response.raise_for_status() 
    return response.json()
  except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, 
      requests.exceptions.HTTPError, json.JSONDecodeError, Exception):
    return None

def get_status_message(state_data: Optional[Dict], mission_data: Optional[Dict], detected_vehicle: str, map_name: str, unfiltered_raw_id: str) -> Tuple[str, str]:
  """
  Determines the current game status based on API data.
  """
  if not state_data:
    return "Offline", "Waiting for game..."

  # --- PRIORITY CHECK: HANGAR MAP DETECTED ---
  vehicle_display = detected_vehicle if detected_vehicle != "Unknown Vehicle" else "Vehicle"

  if map_name == "Hangar":
    if detected_vehicle != "Unknown Vehicle":
      return "Idle in Hangar", f"Inspecting {vehicle_display}" 
    return "In Main Menu/Hangar", "Waiting for vehicle selection"
  
  # --- RESILIENT MISSION DETECTION LOGIC (SECONDARY CHECK) ---
  is_status_running = mission_data and mission_data.get('status') == 'running'
  
  is_mission_enabled_or_valid = mission_data and (
    mission_data.get('is_enabled', False) or 
    (mission_data.get('valid', False) and mission_data.get('type', 'mission') != 'mission')
  )
  
  is_in_mission = is_status_running or is_mission_enabled_or_valid
  
  if is_in_mission:
    mission_type_raw = mission_data.get('type')
    map_name_display = map_name 
    
    # --- MISSION TYPE INFERENCE LOGIC (PRIMARY CHECK FOR BATTLE TYPE) ---
    # 1. Get official mission type
    if not mission_type_raw or mission_type_raw == 'mission':
      # 2. If official type is generic/missing, infer from vehicle ID prefix (less reliable)
      if unfiltered_raw_id and 'tankmodels/' in unfiltered_raw_id:
        mission_type_raw = 'ground_battle' # Infer ground if tank
      elif unfiltered_raw_id and ('shipmodels/' in unfiltered_raw_id or 'boat/' in unfiltered_raw_id):
        mission_type_raw = 'naval_battle' # Infer naval if boat/ship
      elif unfiltered_raw_id != "unknown_vehicle":
        # If vehicle is known but no mission type, default to air (most common default for mission API)
        mission_type_raw = 'air_battle'
      else:
        mission_type_raw = 'Custom Battle'
    # --- End Inference Logic ---


    # Determine the action based on the CURRENT VEHICLE TYPE
    action_text = ""
    # Check if the current vehicle is a tank/ground vehicle
    if 'tankmodels/' in unfiltered_raw_id:
      action_text = f"Driving a {detected_vehicle}"
    # Check if the current vehicle is a ship/boat/naval vehicle
    elif 'shipmodels/' in unfiltered_raw_id or 'boat/' in unfiltered_raw_id:
      action_text = f"Commanding the {detected_vehicle}"
    # Otherwise, assume it's an air vehicle (plane/heli) or unknown
    else:
      action_text = f"Piloting the {detected_vehicle}"

    
    # Determine the DETAILS message based on the MISSION TYPE (PRIORITY)
    details = ""
    
    if 'ground_battle' in mission_type_raw or 'ground_match' in mission_type_raw:
      details = f"In Ground Battle on {map_name_display}"
    elif 'air_battle' in mission_type_raw or 'air_match' in mission_type_raw:
      details = f"In Air Battle on {map_name_display}" 
    elif 'naval_battle' in mission_type_raw:
      details = f"In Naval Battle on {map_name_display}"
    elif 'Custom Battle' in mission_type_raw:
      details = f"In Custom Battle on {map_name_display}"
    else:
      # Fallback for unknown/new mission types
      mission_type_display = mission_type_raw.replace('_', ' ').title()
      details = f"In Battle: {mission_type_display}"
      action_text = f"Map: {map_name_display}" # Fallback for state

    
    # Ensure the state is always the vehicle action text
    state = action_text 
    
    return details, state
  
  if detected_vehicle != "Unknown Vehicle":
    return "Idle in Hangar", f"Inspecting {vehicle_display}" 
    
  return "In Main Menu/Hangar", "Waiting for vehicle selection"

def get_raw_vehicle_id(state_data: Optional[Dict], indicators_data: Optional[Dict]) -> Tuple[str, str]:
  """
  Extracts the vehicle ID.
  Returns: (canonical_id, unfiltered_raw_id)
  """
  raw_id = None
  
  if state_data and 'name' in state_data:
    raw_id = state_data['name']
  elif indicators_data and 'type' in indicators_data:
    raw_id = indicators_data['type']
  
  if not raw_id or raw_id in ('unknown_vehicle', 'Unknown Vehicle'):
    return "unknown_vehicle", "unknown_vehicle"
    
  unfiltered_raw_id = raw_id.lower().strip()
  
  # Remove path prefixes (e.g., 'tankmodels/') to get the canonical ID for the Wiki
  canonical_id = unfiltered_raw_id
  if '/' in canonical_id:
    canonical_id = canonical_id.split('/')[-1]
    
  return canonical_id, unfiltered_raw_id

def get_wiki_url_from_id(vehicle_id: str) -> str:
  """Constructs the War Thunder Wiki URL from the raw vehicle ID."""
  BASE_WIKI_URL = "https://wiki.warthunder.com/unit/"
  return f"{BASE_WIKI_URL}{vehicle_id}"

def get_default_display_name(raw_id: str) -> str:
  """Creates a clean, capitalized name from the raw ID as a fallback."""
  if raw_id == "unknown_vehicle":
    return "Unknown Vehicle"
  return raw_id.replace('_', ' ').title().strip()
  
# --- Main Logic ---

def monitor_war_thunder():
  """Main loop to monitor the War Thunder API and prepare RPC data."""
  global LAST_VEHICLE_ID
  global GLOBAL_MAP_HASHES

  print("--- War Thunder RPC Monitor Initializing ---")
  
  # 1. Load or prompt for APP_ID and load GLOBAL_MAP_HASHES
  app_id = load_config()
  if not app_id:
    print("\u274C Cannot proceed without a valid Discord Application ID.")
    # This will exit gracefully in a local environment
    return 

  # 2. RPC Connection Setup
  try:
    RPC = Presence(app_id)
    RPC.connect()
    print(f"\u2705 Attempting connection to Discord RPC with ID: {app_id}...")
  except Exception as e:
    print(f"\u274C Failed to connect to Discord RPC. Is Discord running, or is the 'pypresence' library installed? Error: {e}")
    return 

  # Variables to track previous state for update checking
  last_details = ""
  last_state = ""
  last_vehicle_display = ""
  last_image_url = "" 
  last_br = ""
  last_map_name = "" 
  
  start_time = time.time()
  
  print(f"\n\u2705 Monitoring War Thunder Local API at {WAR_THUNDER_API_URL}...")
  
  try:
    while True:
      current_time = datetime.now().strftime("%H:%M:%S")

      # 1. Fetch data
      state_data = get_data("state")
      indicators_data = get_data("indicators")
      mission_data = get_data("mission")

      # 2. Get Raw Vehicle ID and determine default name/BR
      raw_vehicle_id, unfiltered_raw_id = get_raw_vehicle_id(state_data, indicators_data)
      detected_vehicle = get_default_display_name(raw_vehicle_id)
      detected_br = "N/A" # Default BR

      if raw_vehicle_id != "unknown_vehicle":
        
        if raw_vehicle_id in VEHICLE_NAME_CACHE:
          detected_vehicle, detected_br = VEHICLE_NAME_CACHE[raw_vehicle_id]
        
        elif raw_vehicle_id != LAST_VEHICLE_ID or raw_vehicle_id not in VEHICLE_NAME_CACHE:
          wiki_url = get_wiki_url_from_id(raw_vehicle_id)
          print(f"\n\u2139 Vehicle ID changed or uncached. Attempting to scrape data from: {wiki_url}")
          
          scraped_data = get_vehicle_name(wiki_url)
          
          if scraped_data and scraped_data[0]:
            scraped_name, scraped_br = scraped_data
            
            detected_vehicle = scraped_name if scraped_name else detected_vehicle
            detected_br = scraped_br if scraped_br else "N/A"
            
            VEHICLE_NAME_CACHE[raw_vehicle_id] = (detected_vehicle, detected_br)
            print(f"\u2705 Scraped data successfully: {detected_vehicle} (RB BR: {detected_br})")
          else:
            detected_br = "N/A"
            print(f"\u274C Scraping failed for {raw_vehicle_id}. Using default name: {detected_vehicle}")

      # Apply manual display name override if available
      if raw_vehicle_id in VEHICLE_DISPLAY_MAP:
        detected_vehicle = VEHICLE_DISPLAY_MAP[raw_vehicle_id]
        print(f"\u2139 Applied manual name override: {detected_vehicle}")

      # Update the last known ID
      LAST_VEHICLE_ID = raw_vehicle_id
      
      # 3. MAP DETECTION LOGIC
      current_map_value = "Not in Mission"
      sha256_hash = get_map_image_hash() 
      
      if sha256_hash:
        current_map_value = lookup_map_name(sha256_hash)
        
        # --- AUTO-ADD NEW HASHES TO CONFIG.JSON WITH RAW GITHUB URL ---
        if sha256_hash and sha256_hash not in GLOBAL_MAP_HASHES:
          
          # Placeholder name for cleaning 
          placeholder_name = "unknown_map" 
          
          # 1. Clean the default display name
          
          # 2. Construct the auto-generated raw URL
          clean_placeholder_name = placeholder_name.lower().replace(' ', '_')
          auto_generated_url = f"{GITHUB_RAW_BASE_URL}{clean_placeholder_name}{MAP_IMAGE_EXTENSION}"
          
          # 3. Update global map hashes and save config
          GLOBAL_MAP_HASHES[sha256_hash] = auto_generated_url
          current_config = {"APP_ID": app_id, "MAP_HASHES": GLOBAL_MAP_HASHES}
          save_config(current_config)
          
          print(f"\n\u26A0 NEW MAP DETECTED! Hash added to {CONFIG_FILE}.")
          print(f"\u26A0 The hash has been mapped to a placeholder URL:")
          print(f"  {auto_generated_url}")
          print(f"\u26A0 ACTION REQUIRED: Please rename this map URL in {CONFIG_FILE} and upload the image to GitHub!")
          
          # Update current map value to the newly added URL
          current_map_value = auto_generated_url 
      
      
      is_status_running = mission_data and mission_data.get('status') == 'running'
      is_mission_enabled_or_valid = mission_data and (
        mission_data.get('is_enabled', False) or 
        (mission_data.get('valid', False) and mission_data.get('type', 'mission') != 'mission')
      )
      is_in_mission = is_status_running or is_mission_enabled_or_valid

      
      # 4. Construct Public Vehicle Image URL
      current_image_url = f"{VEHICLE_IMAGE_BASE_URL}{raw_vehicle_id}.png" if raw_vehicle_id != "unknown_vehicle" else ""

      # 5. Determine Map Display Name and RPC Asset Key/URL
      map_asset_key_or_url = current_map_value
      map_name_display = current_map_value # Default display name is the value from config
      
      if is_url(current_map_value):
        # If a URL is used, we extract the map name from the filename for display
        parsed_url = urlparse(current_map_value)
        filename_with_ext = os.path.basename(parsed_url.path) 
        filename = os.path.splitext(filename_with_ext)[0]
        map_name_display = filename.replace('_', ' ').title()
        
        # Check if the map name is the generic placeholder name
        if map_name_display == "Unknown Map":
          map_name_display = "Unknown Map (Upload Pending)"
        
      elif map_name_display in ["Unknown Map (Needs Update)", "Unknown Map (Just Added)", "Not in Mission"]:
        # If a diagnostic/placeholder name, try to use Hangar map name if available
                if map_name_display == "Not in Mission" and sha256_hash and 'cfb99c04947c94c19d4c523c1e0fb3a2d71d403263fefcad5f4c4fc8485d07d0' in sha256_hash:
                    map_name_display = "Hangar"
                
                pass # Use the diagnostic name
        
      else:
        # Value is a clean name/Discord Asset Key (e.g., "Port Novorossiysk").
        map_name_display = map_name_display.replace('_', ' ').title() # Capitalize for display
        map_asset_key_or_url = map_asset_key_or_url.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
        

      # 6. Process status message
      details, state = get_status_message(state_data, mission_data, detected_vehicle, map_name_display, unfiltered_raw_id) 

      # 7. Construct Tooltip Text
      br_tooltip = f" BR: {detected_br}" if detected_br != "N/A" else ""
      tooltip_text = f"{detected_vehicle}{br_tooltip}"

      # --- 8. IMAGE LOGIC MODIFICATION (Map Asset/URL as Large Image in Battle) ---
      large_image_key = "war_thunder_logo" # Default
      large_image_text = "War Thunder"
      small_image_key = None
      small_image_text = None
      
      
      if is_in_mission:
        
        # Check if the map value is a URL or a clean key
        is_clean_asset_key = not is_url(map_asset_key_or_url) and map_asset_key_or_url not in ["unknown_map_(needs_update)", "unknown_map_(just_added)", "unknown_map", "not_in_mission", "hangar"]
        
        if is_url(map_asset_key_or_url):
          # Option 1: External URL used directly
          large_image_key = map_asset_key_or_url
          large_image_text = map_name_display if map_name_display not in ["Unknown Map (Upload Pending)"] else "Uploading Map Image"
          
        elif is_clean_asset_key:
          # Option 2: Discord Asset Key (requires manual upload)
          large_image_key = map_asset_key_or_url
          large_image_text = map_name_display
          
        else:
          # Fallback if map name is not specific 
          large_image_key = "war_thunder_logo" # Fallback to logo
          large_image_text = "In Battle"

        # Use the vehicle icon (public URL) for the Small Image
        if current_image_url:
          small_image_key = current_image_url
          small_image_text = tooltip_text
          
      elif current_image_url:
        # Idle/Hangar: Keep Logo Large, use Vehicle Icon for Small Image
        small_image_key = current_image_url
                
            # Ensure the small image text (vehicle name/BR) is set when a vehicle is present,
            # even if not in a mission (i.e., in the Hangar)
      if small_image_key and not small_image_text:
        small_image_text = tooltip_text
    
      # If map is Hangar, we reset start_time
      if map_name_display == "Hangar":
        start_time = time.time()
        

      # 9. Prepare RPC Payload
      rpc_payload = {
        "details": details,
        "state": state,
        "start": int(start_time),
        "large_image": large_image_key, 
        "large_text": large_image_text,
      }
      if small_image_key:
        rpc_payload["small_image"] = small_image_key
        rpc_payload["small_text"] = small_image_text
      
      # 10. Print Debug Data & Status Check
      print("\n--- WAR THUNDER MONITOR LOG ---")
      state_status = "Found" if state_data else "None (Check Game/Firewall)"
      print(f"Data Status (State): {state_status}")
      print(f"Raw Vehicle ID: {raw_vehicle_id}")
      print(f"Detected Map Value (Config): {current_map_value}")
      print(f"RPC Map Key/URL Used: {map_asset_key_or_url}")
      print("\n--- DISCORD RPC PAYLOAD ---")
      print(f"DETAILS: {rpc_payload['details']}")
      print(f"STATE: {rpc_payload['state']}")
      print(f"LARGE IMAGE: {large_image_key}") # Log which image is used as large
      print(f"SMALL IMAGE: {small_image_key}") # Log which image is used as small
      print(f"TIME ELAPSED: {int(time.time() - start_time)} seconds")
      print(f"Last API Poll: {current_time}")
      print("-----------------------------")


      # 11. Update RPC
      current_rpc_data_tuple = (details, state, detected_vehicle, large_image_key, small_image_key, detected_br, map_name_display)
      last_rpc_data_tuple = (last_details, last_state, last_vehicle_display, last_image_url, small_image_key, last_br, last_map_name) 

      if current_rpc_data_tuple != last_rpc_data_tuple:
        
        changed_items = []
        if details != last_details: changed_items.append("Details")
        if state != last_state: changed_items.append("State")
        if detected_vehicle != last_vehicle_display: changed_items.append("Vehicle")
        if large_image_key != last_image_url: changed_items.append("Large Image Key/URL") 
        if small_image_key != (current_image_url if not is_in_mission else current_image_url): changed_items.append("Small Image Key") 
        if detected_br != last_br: changed_items.append("BR")
        if map_name_display != last_map_name: changed_items.append(f"Map Name ('{last_map_name}'->'{map_name_display}')")

        update_message = f"\u27A1 RPC Update: {', '.join(changed_items)} changed."
        print(update_message)
        
        RPC.update(**rpc_payload)
        
        last_details = details
        last_state = state
        last_vehicle_display = detected_vehicle
        last_image_url = large_image_key
        last_br = detected_br
        last_map_name = map_name_display 

      # 12. Wait for next poll
      time.sleep(POLL_INTERVAL_SECONDS)

  except KeyboardInterrupt:
    print("\nMonitoring stopped by user.")
    try:
      RPC.close()
    except:
      pass
  except Exception as e:
    print(f"\nCRITICAL ERROR in main loop: {e}")
    try:
      RPC.close()
    except:
      pass

if __name__ == "__main__":
  monitor_war_thunder()