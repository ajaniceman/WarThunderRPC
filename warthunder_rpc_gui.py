import requests
import json
import time
import os
import sys
import hashlib
import threading
from datetime import datetime
from pypresence import Presence
from typing import Dict, Any, Optional, Tuple, Callable
from urllib.parse import urlparse
import tkinter as tk
from tkinter import messagebox, scrolledtext

# ==============================================================================
# --- LOCAL MODULE LOGIC (Merged from scrape_vehicle_name.py) ---
# ==============================================================================

# Set a user-agent for scraping
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Ensure BeautifulSoup is available for scraping (Tkinter is built-in)
try:
    from bs4 import BeautifulSoup
except ImportError:
    # This will still raise an error if called, but better than silent failure.
    print("FATAL ERROR: The 'beautifulsoup4' library is required for scraping.")
    
# --- Vehicle Scraping Functions ---

def get_vehicle_name(wiki_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Scrapes the War Thunder Wiki page for the vehicle's official display name and RB BR.
    """
    
    try:
        response = requests.get(wiki_url, headers=HEADERS, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\u26A0 Vehicle scraping failed for URL: {wiki_url}. Error: {e}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # --- 1. Extract Vehicle Name (PRIORITY: .game-unit_name div) ---
    display_name = None
    
    # Look for the dedicated unit name div
    unit_name_div = soup.find('div', class_='game-unit_name')
    if unit_name_div:
        display_name = unit_name_div.get_text(strip=True)
    
    # Fallback 1: Use the main H1 header (page title)
    if not display_name:
        header = soup.find('h1', id='firstHeading')
        if header:
            display_name = header.get_text(strip=True)

    # Fallback 2: Extract name from URL if header scrape failed
    if not display_name:
        url_path = urlparse(wiki_url).path
        raw_id = url_path.split('/')[-1]
        display_name = raw_id.replace('_', ' ').title().strip()

    # --- 2. Extract Realistic Battle (RB) BR ---
    rb_br = None
    br_items = soup.find_all('div', class_='game-unit_br-item')
    
    for item in br_items:
        mode_div = item.find('div', class_='mode')
        value_div = item.find('div', class_='value')
        
        if mode_div and mode_div.get_text(strip=True) == 'RB' and value_div:
            rb_br = value_div.get_text(strip=True)
            break 
    
    return display_name, rb_br

# ==============================================================================
# --- FILE PATH UTILITY & CONFIG CONSTANTS ---
# ==============================================================================

# The name for the user-editable file that lives next to the EXE
PERSISTENT_CONFIG_FILE = "config.json"
# The name of the file embedded inside the EXE via PyInstaller
EMBEDDED_CONFIG_FILE = "default_config.json" 

# --- NEW: External Manifest URL (You MUST host this file on a public service like GitHub raw)
# REPLACE THIS WITH YOUR ACTUAL GITHUB RAW URL
EXTERNAL_MANIFEST_URL = "https://raw.githubusercontent.com/ajaniceman/WarThunderRPC/main/map_manifest.json"


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to bundled resource (read-only), works for dev and for PyInstaller.
    Used for files like the icon and the embedded config.
    """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Fallback for development environment
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_config_path() -> str:
    """
    Returns the persistent path for the user-editable config.json.
    This is typically the directory containing the executable.
    """
    if getattr(sys, 'frozen', False):
        # Running from an executable: Use the directory of the executable itself
        base_dir = os.path.dirname(sys.executable)
    else:
        # Development environment: Use the current working directory
        base_dir = os.path.abspath(".")
    
    return os.path.join(base_dir, PERSISTENT_CONFIG_FILE)


# ==============================================================================
# --- GLOBALS & CONFIGURATION (wtrpc.py globals adapted) ---
# ==============================================================================

# Cache and state variables
VEHICLE_NAME_CACHE: Dict[str, Tuple[str, str]] = {}
LAST_VEHICLE_ID: Optional[str] = None
VEHICLE_DISPLAY_MAP: Dict[str, str] = {}
GLOBAL_MAP_HASHES: Dict[str, str] = {}
GLOBAL_APP_ID: Optional[str] = None
RPC = None # Placeholder for the pypresence.Presence instance

# War Thunder Monitor Config
WAR_THUNDER_API_URL = "http://127.0.0.1:8111"
POLL_INTERVAL_SECONDS = 5.0
VEHICLE_IMAGE_BASE_URL = "https://static.encyclopedia.warthunder.com/images/"

ENDPOINTS = {
    "state": f"{WAR_THUNDER_API_URL}/state",
    "indicators": f"{WAR_THUNDER_API_URL}/indicators",
    "mission": f"{WAR_THUNDER_API_URL}/mission.json"
}

GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/ajaniceman/WarThunderRPC/main/mapPictures/"
MAP_IMAGE_EXTENSION = ".jpg"
MAP_IMAGE_URL = f"{WAR_THUNDER_API_URL}/map.img"

# --- Configuration Loading/Saving Functions (Adapted to use get_config_path) ---

def fetch_external_manifest() -> Optional[Dict[str, Any]]:
    """Fetches the latest map hash manifest from the external URL."""
    try:
        # Setting a short timeout to prevent long hangs if the URL is down
        response = requests.get(EXTERNAL_MANIFEST_URL, timeout=3)
        response.raise_for_status() 
        manifest_data = response.json()
        print("\u2705 Map hash manifest downloaded and applied.")
        return manifest_data
    except requests.exceptions.RequestException as e:
        print(f"\u26A0 Could not fetch latest map data. Using local list only. Error: {e}")
        return None
    except json.JSONDecodeError:
        print("\u26A0 Error decoding external map data. File might be corrupt.")
        return None

def save_config(config_data: Dict[str, Any]):
    """Saves the current configuration data back to persistent config.json."""
    config_path = get_config_path() # Use persistent path
    try:
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"\u2705 Configuration saved successfully to {PERSISTENT_CONFIG_FILE}.")
    except IOError as e:
        print(f"\u274C Error saving configuration to {PERSISTENT_CONFIG_FILE}. Error: {e}")

def load_config() -> Optional[str]:
    """Loads APP_ID and map hashes, preferring persistent file, then embedded default, then merges external manifest."""
    global GLOBAL_MAP_HASHES, GLOBAL_APP_ID
    
    app_id = None
    config_local: Dict[str, Any] = {}
    config_embedded: Dict[str, Any] = {}
    
    # 1. Attempt to load existing persistent configuration file (User's changes)
    persistent_path = get_config_path()
    
    if os.path.exists(persistent_path):
        try:
            with open(persistent_path, 'r') as f:
                config_local = json.load(f)
                print(f"\u2705 Loaded user configuration from {PERSISTENT_CONFIG_FILE}.")
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"\u274C Error reading local config file. Attempting to use default. Error: {e}")
            config_local = {}
    
    # 2. If local load failed (or file didn't exist), try loading the embedded default
    if not config_local:
        embedded_path = resource_path(EMBEDDED_CONFIG_FILE)
        if os.path.exists(embedded_path):
             try:
                with open(embedded_path, 'r') as f:
                    config_embedded = json.load(f)
                    config_local.update(config_embedded)
                    print(f"\u26A0 Local config not found. Initializing from embedded default.")
                    
             except (json.JSONDecodeError, IOError) as e:
                 print(f"\u274C FATAL: Could not load embedded default config file. Starting with blank config. Error: {e}")
        else:
             print(f"\u274C Embedded default config fallback NOT FOUND. Starting with blank config.")

    # 3. Fetch and merge the External Manifest (Priority 1 for Map Hashes)
    config_external = fetch_external_manifest()
    
    if config_external and "MAP_HASHES" in config_external:
        GLOBAL_MAP_HASHES = config_external["MAP_HASHES"]
    else:
        GLOBAL_MAP_HASHES = config_local.get("MAP_HASHES", {})
        
    # Merge local/discovered hashes ON TOP of the external ones
    if config_local.get("MAP_HASHES"):
        GLOBAL_MAP_HASHES.update(config_local["MAP_HASHES"]) 
    
    # 4. Finalize and Save
    GLOBAL_APP_ID = config_local.get("APP_ID")
    app_id = GLOBAL_APP_ID

    config_to_save = {
        "APP_ID": GLOBAL_APP_ID, 
        "MAP_HASHES": GLOBAL_MAP_HASHES 
    }
    
    save_config(config_to_save) 
    
    return app_id

# --- Helper Functions ---

def get_map_image_hash() -> Optional[str]:
    """Fetches the map image data from /map.img and returns its SHA256 hash."""
    try:
        response = requests.get(MAP_IMAGE_URL, timeout=1.5)
        response.raise_for_status()
        if response.content:
            return hashlib.sha256(response.content).hexdigest()
        return None
    except requests.exceptions.RequestException:
        return None

def lookup_map_name(sha256_hash: Optional[str]) -> str:
    """Looks up the map hash in the configuration."""
    if sha256_hash:
        map_value = GLOBAL_MAP_HASHES.get(sha256_hash)
        if map_value is not None:
            return map_value if map_value != "" else "Unknown Map (Needs Update)"
        return f"Unknown Map (Hash: {sha256_hash[:8]}...)"
    return "Not in Mission"

def is_url(s: str) -> bool:
    """Checks if a string appears to be a full URL."""
    return s.startswith("http://") or s.startswith("https://")

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
    """Determines the current game status based on API data."""
    if not state_data:
        return "Offline", "Waiting for game..."

    vehicle_display = detected_vehicle if detected_vehicle != "Unknown Vehicle" else "Vehicle"

    if map_name == "Hangar":
        if detected_vehicle != "Unknown Vehicle":
            return "Idle in Hangar", f"Inspecting {vehicle_display}" 
        return "In Main Menu/Hangar", "Waiting for vehicle selection"
    
    is_status_running = mission_data and mission_data.get('status') == 'running'
    
    is_mission_enabled_or_valid = mission_data and (
        mission_data.get('is_enabled', False) or 
        (mission_data.get('valid', False) and mission_data.get('type', 'mission') != 'mission')
    )
    
    is_in_mission = is_status_running or is_mission_enabled_or_valid
    
    if is_in_mission:
        mission_type_raw = mission_data.get('type')
        map_name_display = map_name 
        
        if not mission_type_raw or mission_type_raw == 'mission':
            if unfiltered_raw_id and 'tankmodels/' in unfiltered_raw_id:
                mission_type_raw = 'ground_battle'
            elif unfiltered_raw_id and ('shipmodels/' in unfiltered_raw_id or 'boat/' in unfiltered_raw_id):
                mission_type_raw = 'naval_battle'
            elif unfiltered_raw_id != "unknown_vehicle":
                mission_type_raw = 'air_battle'
            else:
                mission_type_raw = 'Custom Battle'

        action_text = ""
        if 'tankmodels/' in unfiltered_raw_id:
            action_text = f"Driving a {detected_vehicle}"
        elif 'shipmodels/' in unfiltered_raw_id or 'boat/' in unfiltered_raw_id:
            action_text = f"Commanding the {detected_vehicle}"
        else:
            action_text = f"Piloting the {detected_vehicle}"

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
            mission_type_display = mission_type_raw.replace('_', ' ').title()
            details = f"In Battle: {mission_type_display}"
            action_text = f"Map: {map_name_display}" 

        state = action_text 
        return details, state
    
    if detected_vehicle != "Unknown Vehicle":
        return "Idle in Hangar", f"Inspecting {vehicle_display}" 
        
    return "In Main Menu/Hangar", "Waiting for vehicle selection"

def get_raw_vehicle_id(state_data: Optional[Dict], indicators_data: Optional[Dict]) -> Tuple[str, str]:
    """Extracts the vehicle ID. Returns: (canonical_id, unfiltered_raw_id)"""
    raw_id = None
    if state_data and 'name' in state_data:
        raw_id = state_data['name']
    elif indicators_data and 'type' in indicators_data:
        raw_id = indicators_data['type']
    
    if not raw_id or raw_id in ('unknown_vehicle', 'Unknown Vehicle'):
        return "unknown_vehicle", "unknown_vehicle"
        
    unfiltered_raw_id = raw_id.lower().strip()
    
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
    
# ==============================================================================
# --- MAIN RPC MONITOR LOGIC (Adapted for GUI) ---
# ==============================================================================

class RPCMonitor:
    def __init__(self, app_id: str, stop_event: threading.Event):
        global RPC
        self.app_id = app_id
        self.stop_event = stop_event
        self.start_time = time.time()
        self.last_details = ""
        self.last_state = ""
        self.last_vehicle_display = ""
        self.last_image_url = "" 
        self.last_br = ""
        self.last_map_name = "" 
        self.is_connected = False
        
        # Connect RPC
        try:
            RPC = Presence(self.app_id)
            RPC.connect()
            self.is_connected = True
            print(f"\u2705 Discord RPC Connected.")
        except Exception as e:
            print(f"\u274C Failed to connect to Discord RPC. Is Discord running? Error: {e}")
            self.stop_event.set() # Set stop event if connection fails

    def run(self):
        """The main polling loop, runs in a separate thread."""
        global LAST_VEHICLE_ID, GLOBAL_MAP_HASHES

        if not self.is_connected:
            return

        try:
            while not self.stop_event.is_set():
                current_time_str = datetime.now().strftime("%H:%M:%S")

                # 1. Fetch data
                state_data = get_data("state")
                indicators_data = get_data("indicators")
                mission_data = get_data("mission")

                # 2. Get Vehicle ID and Name/BR
                raw_vehicle_id, unfiltered_raw_id = get_raw_vehicle_id(state_data, indicators_data)
                detected_vehicle = get_default_display_name(raw_vehicle_id)
                detected_br = "N/A"

                if raw_vehicle_id != "unknown_vehicle":
                    if raw_vehicle_id in VEHICLE_NAME_CACHE:
                        detected_vehicle, detected_br = VEHICLE_NAME_CACHE[raw_vehicle_id]
                    
                    elif raw_vehicle_id != LAST_VEHICLE_ID or raw_vehicle_id not in VEHICLE_NAME_CACHE:
                        wiki_url = get_wiki_url_from_id(raw_vehicle_id)
                        
                        scraped_data = get_vehicle_name(wiki_url)
                        
                        if scraped_data and scraped_data[0]:
                            scraped_name, scraped_br = scraped_data
                            
                            detected_vehicle = scraped_name if scraped_name else detected_vehicle
                            detected_br = scraped_br if scraped_br else "N/A"
                            
                            VEHICLE_NAME_CACHE[raw_vehicle_id] = (detected_vehicle, detected_br)
                        else:
                            detected_br = "N/A"
                            print(f"\u26A0 Could not scrape name for {raw_vehicle_id}. Using default name.")

                # Apply manual override
                if raw_vehicle_id in VEHICLE_DISPLAY_MAP:
                    detected_vehicle = VEHICLE_DISPLAY_MAP[raw_vehicle_id]

                LAST_VEHICLE_ID = raw_vehicle_id
                
                # 3. MAP DETECTION LOGIC
                current_map_value = "Not in Mission"
                sha256_hash = get_map_image_hash() 
                
                if sha256_hash:
                    current_map_value = lookup_map_name(sha256_hash)
                    
                    # --- AUTO-ADD NEW HASHES TO PERSISTENT CONFIG ---
                    if sha256_hash and sha256_hash not in GLOBAL_MAP_HASHES:
                        placeholder_name = "unknown_map" 
                        clean_placeholder_name = placeholder_name.lower().replace(' ', '_')
                        auto_generated_url = f"{GITHUB_RAW_BASE_URL}{clean_placeholder_name}{MAP_IMAGE_EXTENSION}"
                        
                        GLOBAL_MAP_HASHES[sha256_hash] = auto_generated_url
                        
                        config_to_save = {"APP_ID": GLOBAL_APP_ID, "MAP_HASHES": GLOBAL_MAP_HASHES}
                        save_config(config_to_save)
                        
                        print(f"\n\u26A0 NEW MAP DETECTED! Hash added to local config.")
                        print(f"\u26A0 Hash: {sha256_hash[:8]}... (Please update the online manifest)")
                        
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
                map_name_display = current_map_value 
                
                # Logic for display name and asset key conversion... 
                if is_url(current_map_value):
                    parsed_url = urlparse(current_map_value)
                    filename_with_ext = os.path.basename(parsed_url.path) 
                    filename = os.path.splitext(filename_with_ext)[0]
                    map_name_display = filename.replace('_', ' ').title()
                    if map_name_display == "Unknown Map":
                        map_name_display = "Unknown Map (Upload Pending)"
                elif map_name_display in ["Unknown Map (Needs Update)", "Unknown Map (Just Added)", "Not in Mission"]:
                    if map_name_display == "Not in Mission" and sha256_hash and 'cfb99c04947c94c19d4c523c1e0fb3a2d71d403263fefcad5f4c4fc8485d07d0' in sha256_hash:
                        map_name_display = "Hangar"
                    pass
                else:
                    map_name_display = map_name_display.replace('_', ' ').title()
                    map_asset_key_or_url = map_asset_key_or_url.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')


                # 6. Process status message
                details, state = get_status_message(state_data, mission_data, detected_vehicle, map_name_display, unfiltered_raw_id) 

                # 7. Construct Tooltip Text
                br_tooltip = f" BR: {detected_br}" if detected_br != "N/A" else ""
                tooltip_text = f"{detected_vehicle}{br_tooltip}"

                # 8. Image Logic
                large_image_key = "war_thunder_logo" # Default (Must be an uploaded asset on Discord)
                large_image_text = "War Thunder"
                small_image_key = None
                small_image_text = None
                
                if is_in_mission:
                    is_clean_asset_key = not is_url(map_asset_key_or_url) and map_asset_key_or_url not in ["unknown_map_(needs_update)", "unknown_map_(just_added)", "unknown_map", "not_in_mission", "hangar"]
                    if is_url(map_asset_key_or_url):
                        large_image_key = map_asset_key_or_url
                        large_image_text = map_name_display if map_name_display not in ["Unknown Map (Upload Pending)"] else "Uploading Map Image"
                    elif is_clean_asset_key:
                        large_image_key = map_asset_key_or_url
                        large_image_text = map_name_display
                    else:
                        large_image_key = "war_thunder_logo"

                    if current_image_url:
                        small_image_key = current_image_url
                        small_image_text = tooltip_text
                        
                elif current_image_url:
                    small_image_key = current_image_url
                    
                if small_image_key and not small_image_text:
                    small_image_text = tooltip_text
            
                if map_name_display == "Hangar":
                    self.start_time = time.time()
                    

                # 9. Prepare RPC Payload
                rpc_payload = {
                    "details": details,
                    "state": state,
                    "start": int(self.start_time),
                    "large_image": large_image_key, 
                    "large_text": large_image_text,
                }
                if small_image_key:
                    rpc_payload["small_image"] = small_image_key
                    rpc_payload["small_text"] = small_image_text
                
                # 10. Check if update is needed
                current_rpc_data_tuple = (details, state, detected_vehicle, large_image_key, small_image_key, detected_br, map_name_display)
                last_rpc_data_tuple = (self.last_details, self.last_state, self.last_vehicle_display, self.last_image_url, small_image_key, self.last_br, self.last_map_name) 

                if current_rpc_data_tuple != last_rpc_data_tuple:
                    
                    # Simplified RPC Update message
                    print(f"[{current_time_str}] RPC Updated: Details: '{details}' | State: '{state}'")
                    
                    RPC.update(**rpc_payload)
                    
                    self.last_details = details
                    self.last_state = state
                    self.last_vehicle_display = detected_vehicle
                    self.last_image_url = large_image_key
                    self.last_br = detected_br
                    self.last_map_name = map_name_display 
                else:
                    # Print current status on every poll for visibility
                    state_status = "Found" if state_data else "None (Check Game/Firewall)"
                    print(f"[{current_time_str}] WT Status: {state_status} | Current Vehicle: {detected_vehicle} | Map: {map_name_display}")


                # 11. Wait for next poll
                time.sleep(POLL_INTERVAL_SECONDS)

        except Exception as e:
            print(f"\nCRITICAL ERROR in monitoring loop: {e}")
        finally:
            self.stop_rpc_connection()

    def stop_rpc_connection(self):
        """Cleans up the RPC connection."""
        global RPC
        print("\n\u274C Stopping monitor and closing Discord RPC connection.")
        try:
            if RPC:
                RPC.close()
                RPC = None
        except Exception as e:
            print(f"Error during RPC shutdown: {e}")

# ==============================================================================
# --- GUI FRAMEWORK (TKINTER) ---
# ==============================================================================

class TerminalRedirect:
    """
    Redirects stdout to a tkinter Text widget. 
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget
        # Capture the original stream object. It can be None in --windowed mode.
        self.stdout = sys.stdout 

    def write(self, text):
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END) # Auto-scroll to the bottom
        # Only write to the original console if it exists (fixes the AttributeError)
        if self.stdout is not None:
            self.stdout.write(text)

    def flush(self):
        # Only flush the original console if it exists
        if self.stdout is not None:
            self.stdout.flush()

class WarThunderRPCApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Tkinter window setup (AESTHETIC CHANGES START HERE)
        self.title("War Thunder RPC Monitor")
        self.geometry("800x600")
        self.minsize(600, 450)
        # Deep dark background color
        self.configure(bg="#1E2833") 
        try:
             # Attempt to set the icon
            self.iconbitmap(resource_path('warthunder.ico'))
        except:
            pass
        
        # State variables
        self.rpc_thread = None
        self.stop_event = threading.Event()
        
        # Load config on startup
        loaded_id = load_config()
        
        self.create_widgets(loaded_id)
        
        # Set up terminal output redirection
        sys.stdout = TerminalRedirect(self.terminal_output)
        print("--- Monitor Initialized ---") 
        
        # Handle window close event gracefully (CRITICAL SHUTDOWN LOGIC)
        # This ensures on_closing is called when the user clicks the 'X' button.
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self, loaded_id):
        # Define common styling
        DARK_BG = "#1E2833"
        LIGHT_BG = "#2C3E50"
        TEXT_COLOR = "#ECF0F1"
        FONT_STYLE = ("Inter", 10)
        MONO_FONT = ("Consolas", 9)
        BUTTON_PADY = 6
        BUTTON_PADX = 15

        # 1. Control Frame (Input and Buttons)
        control_frame = tk.Frame(self, padx=15, pady=15, bg=LIGHT_BG, bd=0, relief=tk.FLAT)
        control_frame.pack(fill='x', padx=10, pady=(10, 5))

        # App ID Label and Entry
        tk.Label(control_frame, text="Discord App ID:", fg=TEXT_COLOR, bg=LIGHT_BG, font=FONT_STYLE).pack(side=tk.LEFT, padx=(0, 10))
        
        self.app_id_entry = tk.Entry(
            control_frame, 
            width=30, 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#7f8c8d", # Light gray border
            highlightcolor="#3498DB",      # Blue highlight on focus
            fg=DARK_BG, 
            bg=TEXT_COLOR,
            insertbackground=DARK_BG,
            font=FONT_STYLE
        )
        self.app_id_entry.insert(0, loaded_id if loaded_id else "")
        self.app_id_entry.pack(side=tk.LEFT, padx=(0, 20), ipady=3) # Added internal Y padding

        # Button Styling
        common_button_args = {
            "relief": tk.FLAT, 
            "bd": 0, 
            "padx": BUTTON_PADX, 
            "pady": BUTTON_PADY,
            "fg": "white", 
            "font": FONT_STYLE
        }

        # Save Button
        tk.Button(
            control_frame, 
            text="Save ID", 
            command=self.save_app_id, 
            bg="#2ECC71", # Green
            activebackground="#27AE60", # Darker Green
            **common_button_args
        ).pack(side=tk.LEFT, padx=5)

        # Start Button
        self.start_button = tk.Button(
            control_frame, 
            text="Start RPC", 
            command=self.start_rpc, 
            bg="#3498DB", # Blue
            activebackground="#2980B9", # Darker Blue
            **common_button_args
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Stop Button
        self.stop_button = tk.Button(
            control_frame, 
            text="Stop RPC", 
            command=self.stop_rpc, 
            bg="#E74C3C", # Red
            activebackground="#C0392B", # Darker Red
            state=tk.DISABLED,
            **common_button_args
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 2. Terminal Output (Scrolled Text Area)
        tk.Label(self, text="Application Log (Status & Updates):", fg=TEXT_COLOR, bg=DARK_BG, font=FONT_STYLE).pack(fill='x', padx=15, pady=(5, 0))
        
        self.terminal_output = scrolledtext.ScrolledText(
            self, 
            wrap=tk.WORD, 
            bg="#1C2833", # Log area background
            fg="#ECF0F1", # Light text
            bd=0, 
            relief=tk.FLAT, 
            padx=10, 
            pady=10, 
            font=MONO_FONT
        )
        self.terminal_output.pack(fill='both', expand=True, padx=15, pady=(5, 10))


    def save_app_id(self):
        """Saves the user-provided APP ID to the config file."""
        new_id = self.app_id_entry.get().strip()
        if not new_id:
            messagebox.showerror("Configuration Error", "Discord Application ID cannot be empty.")
            return

        global GLOBAL_APP_ID, GLOBAL_MAP_HASHES
        GLOBAL_APP_ID = new_id
        current_config = {"APP_ID": GLOBAL_APP_ID, "MAP_HASHES": GLOBAL_MAP_HASHES}
        save_config(current_config)
        print(f"\u2705 App ID set to: {GLOBAL_APP_ID}")


    def start_rpc(self):
        """Initializes and starts the RPC monitor thread."""
        app_id = self.app_id_entry.get().strip()
        
        if not app_id:
            messagebox.showerror("Configuration Error", "Please enter and save a Discord Application ID before starting.")
            return

        if self.rpc_thread and self.rpc_thread.is_alive():
            print("\u26A0 RPC is already running.")
            return

        self.save_app_id() # Save the ID before starting just in case
        
        self.stop_event.clear()
        # Initialize and start the monitor logic in a separate thread
        self.rpc_thread = threading.Thread(target=RPCMonitor(app_id, self.stop_event).run, daemon=True)
        self.rpc_thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        print("\n\u27A1 RPC Monitoring Started...")


    def stop_rpc(self):
        """Stops the RPC monitor thread."""
        if self.rpc_thread and self.rpc_thread.is_alive():
            self.stop_event.set() # Signal the thread to stop
            print("\u27A1 Sending stop signal to monitor thread...")
            # Note: We rely on the thread's 'finally' block to call stop_rpc_connection()
            # We don't use thread.join() to keep the GUI responsive.

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def on_closing(self):
        """
        [CRITICAL] Stops the RPC monitor thread gracefully before closing the window. 
        This is called when the user clicks the 'X' button or closes the app via the OS.
        """
        self.stop_rpc()
        # Give the thread a moment to process the stop_event and close RPC connection
        # before the main thread destroys the Tk window.
        time.sleep(0.5) 
        # Restore stdout before exit
        sys.stdout = sys.__stdout__
        self.destroy()

if __name__ == "__main__":
    
    app = WarThunderRPCApp()
    app.mainloop()
