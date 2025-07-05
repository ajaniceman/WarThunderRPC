'''
Module to query and access telemetry data during War Thunder matches
'''

#region Imports
import socket
import requests
import json 
import time 
import os 
import hashlib 
from PIL import Image 
import imagehash 
import traceback 

import mapinfo # Custom module for map-related data
#endregion

#region API Endpoints
# IP address of the local machine, used for War Thunder API access
IP_ADDRESS = socket.gethostbyname(socket.gethostname())

# API endpoint for detailed indicators (vehicle type, etc.)
URL_INDICATORS = 'http://{}:8111/indicators'.format(IP_ADDRESS)
# API endpoint for general game state
URL_STATE = 'http://{}:8111/state'.format(IP_ADDRESS)
# API endpoint for mission objectives
URL_OBJECTIVES = 'http://{}:8111/objectives'.format(IP_ADDRESS) 
# API endpoint for game chat comments, requires lastId for incremental updates
URL_COMMENTS = 'http://{}:8111/gamechat?lastId={}'
# API endpoint for game events (damage, kills), requires lastEvt and lastDmg for incremental updates
URL_EVENTS = 'http://{}:8111/hudmsg?lastEvt=-1&lastDmg={}'
#endregion

#region Constants
# Conversion factor from feet to meters
FT_TO_M = 0.3048

# Status codes to represent different states of War Thunder
IN_FLIGHT = 0 # Player is in an active match/flight
IN_MENU = 1 # Player is in the hangar or menu
NO_MISSION = -2 # Game is running, but no active mission/match (e.g., hangar, test flight)
WT_NOT_RUNNING = -3 # War Thunder application is not running or API is unreachable
OTHER_ERROR = -4 # An unexpected error occurred during telemetry fetch

# List of country prefixes for planes that report altitude in Imperial units (feet)
# This is used to convert altitude to meters for consistency
METRICS_PLANES = ['p-', 'f-', 'f2', 'f3', 'f4', 'f6', 'f7', 'f8', 'f9', 'os',
                  'sb', 'tb', 'a-', 'pb', 'am', 'ad', 'fj', 'b-', 'b_', 'xp',
                  'bt', 'xa', 'xf', 'sp', 'hu', 'ty', 'fi', 'gl', 'ni', 'fu',
                  'fu', 'se', 'bl', 'be', 'su', 'te', 'st', 'mo', 'we', 'ha']
#endregion

#region Helper Functions
def combine_dicts(to_dict: dict, from_dict: dict) -> dict:
    '''
    Merges all contents of "from_dict" into "to_dict".
    
    Args:
        to_dict:
            The dictionary to which contents will be merged.
        from_dict:
            The dictionary from which contents will be taken.
    
    Returns:
            A dictionary with the merged contents of the original to_dict and
            from_dict. Returns an empty dictionary if inputs are not dicts.
    '''
    
    if (type(to_dict) == dict) and (type(from_dict) == dict):
        for key in from_dict.keys():
            to_dict[key] = from_dict[key]
        return to_dict
    else:
        return {}
#endregion

#region TelemInterface Class
class TelemInterface(object):
    """
    Manages interaction with the War Thunder telemetry API.
    """
    def __init__(self):
        self.connected = False # True if successfully connected to the game API
        self.full_telemetry = {} # Combines all fetched telemetry data
        self.basic_telemetry = {} # Holds a minimal set of telemetry for core functionality
        self.indicators = {} # Data from /indicators endpoint
        self.state = {} # Data from /state endpoint
        self.map_info = mapinfo.MapInfo() # Instance of MapInfo for map-related data
        self.last_event_ID = -1 # Tracks the last event ID to fetch new events incrementally
        self.last_comment_ID = -1 # Tracks the last comment ID to fetch new comments incrementally
        self.comments = [] # List of game chat comments
        self.events = {} # Dictionary of game events (e.g., damage log)
        self.status = WT_NOT_RUNNING # Current status of War Thunder (running, in menu, in flight, etc.)
    
    def get_comments(self) -> list:
        '''
        Queries the War Thunder API for game chat comments.
        
        Returns:
                A list of comments.
        '''
        try:
            comments_response = requests.get(URL_COMMENTS.format(IP_ADDRESS, self.last_comment_ID), timeout=1)
            comments_response.raise_for_status() # Raise HTTPError for bad responses
            new_comments = comments_response.json()
            self.comments.extend(new_comments)
            if self.comments:
                self.last_comment_ID = max([comment['id'] for comment in self.comments])
            return self.comments
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.JSONDecodeError) as e:
            print(f"Error fetching comments: {e}")
            return [] # Return empty list on error
    
    def get_events(self) -> dict:
        '''
        Queries the War Thunder API for game events (e.g., damage, kills).
        
        Returns:
                An events log dictionary.
        '''
        try:
            events_response = requests.get(URL_EVENTS.format(IP_ADDRESS, self.last_event_ID), timeout=1)
            events_response.raise_for_status() # Raise HTTPError for bad responses
            self.events = combine_dicts(self.events, events_response.json())
            
            try:
                # Update last_event_ID based on the 'damage' events
                if 'damage' in self.events and self.events['damage']:
                    self.last_event_ID = max([event['id'] for event in self.events['damage']])
            except ValueError: # Handle case where 'damage' list might be empty
                self.last_event_ID = -1
            
            return self.events
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.JSONDecodeError) as e:
            print(f"Error fetching events: {e}")
            return {} # Return empty dict on error
    
    def find_altitude(self) -> float:
        '''
        Finds and standardizes reported altitude to meters for all planes.
        Accounts for Imperial units used by some nations (US and UK planes).
        
        Returns:
                Altitude in meters. Returns 0 if altitude data is unavailable.
        '''
        
        name = self.indicators.get('type', '') # Use .get() for safe access
        
        # Check if the plane uses Imperial units based on its prefix
        if name[:2].lower() in METRICS_PLANES:
            if 'altitude_10k' in self.indicators:
                return self.indicators['altitude_10k'] * FT_TO_M
            elif 'altitude_hour' in self.indicators:
                return self.indicators['altitude_hour'] * FT_TO_M
            elif 'altitude_min' in self.indicators:
                return self.indicators['altitude_min'] * FT_TO_M
            else:
                return 0
        else: # Assume metric units for other nations
            if 'altitude_10k' in self.indicators:
                return self.indicators['altitude_10k']
            elif 'altitude_hour' in self.indicators:
                return self.indicators['altitude_hour']
            elif 'altitude_min' in self.indicators:
                return self.indicators['altitude_min']
            else:
                return 0

    def get_telemetry(self, comments: bool = False, events: bool = False) -> bool:
        '''
        Pings War Thunder API endpoints (/indicators, /state, /mapinfo, /map.img)
        to sample telemetry data. This populates self.indicators, self.state,
        self.full_telemetry, and self.basic_telemetry.
        
        Args:
            comments:
                Whether or not to query for match comment data.
            events:
                Whether or not to query for match event data.
        
        Returns:
                True if War Thunder is detected and responding, False otherwise.
                Also updates self.status to reflect the game's state.
        '''
        
        self.connected = False
        self.full_telemetry = {}
        self.basic_telemetry = {}

        try:
            # 1. Fetch core game state and indicators first
            state_response = requests.get(URL_STATE, timeout=1)
            state_response.raise_for_status()
            self.state = state_response.json()
            
            indicators_response = requests.get(URL_INDICATORS, timeout=1)
            indicators_response.raise_for_status()
            self.indicators = indicators_response.json()

            # Handle objectives gracefully, as it might not always be available (e.g., in hangar)
            try:
                objectives_response = requests.get(URL_OBJECTIVES, timeout=1)
                objectives_response.raise_for_status()
                self.full_telemetry['objectives'] = objectives_response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # 404 is expected if not in a mission, treat as no objectives
                    self.full_telemetry['objectives'] = []
                else:
                    # Re-raise other HTTP errors
                    raise e # Re-raise unexpected HTTP errors
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.JSONDecodeError) as e:
                # Catch other errors specific to objectives fetch (e.g., connection issues, malformed JSON)
                print(f"Warning: Error fetching objectives (might be normal in hangar): {e}")
                self.full_telemetry['objectives'] = [] # Treat as no objectives
            
            self.status = IN_MENU # Default to menu if in a valid game state

            # 2. Conditionally fetch map data if game is running and in a valid state
            if self.indicators.get('valid') and self.state.get('valid'):
                map_image_downloaded = self.map_info.download_map_image()
                map_json_data_fetched = self.map_info.fetch_map_json_data()

                if map_image_downloaded and map_json_data_fetched:
                    self.map_info.parse_map_metadata() # This will set self.map_info.map_valid and grid_info

                    if self.map_info.map_valid and self.map_info.grid_info.get('name') != 'Hangar':
                        self.status = IN_FLIGHT
                    else:
                        self.status = IN_MENU # Could be hangar map or unrecognized valid map
                else:
                    self.status = NO_MISSION # Game running, but map data couldn't be fully retrieved
            else:
                self.status = NO_MISSION # Indicators/state not valid, but game is running (e.g. loading screen)

            # 3. Continue with telemetry processing only if core indicators/state are valid
            if self.indicators.get('valid') and self.state.get('valid'):
                # Fix War Thunder's odd sign conventions for pitch and roll
                self.indicators['aviahorizon_pitch'] = -self.indicators.get('aviahorizon_pitch', 0)
                self.indicators['aviahorizon_roll'] = -self.indicators.get('aviahorizon_roll', 0)
                
                self.indicators['alt_m'] = self.find_altitude() # Standardize altitude
                
                # Combine all telemetry data into full_telemetry
                self.full_telemetry = combine_dicts(self.full_telemetry, self.indicators)
                self.full_telemetry = combine_dicts(self.full_telemetry, self.state)
                # Objectives are already added above
                
                # Populate basic_telemetry with key metrics
                self.basic_telemetry['airframe'] = self.indicators.get('type')
                self.basic_telemetry['roll'] = self.indicators.get('aviahorizon_roll')
                self.basic_telemetry['pitch'] = self.indicators.get('aviahorizon_pitch')
                self.basic_telemetry['heading'] = self.indicators.get('compass')
                self.basic_telemetry['altitude'] = self.indicators.get('alt_m')
                
                self.basic_telemetry['lat'] = self.map_info.player_lat
                self.full_telemetry['lat'] = self.map_info.player_lat
                self.basic_telemetry['lon'] = self.map_info.player_lon
                self.full_telemetry['lon'] = self.map_info.player_lon
                
                self.basic_telemetry['IAS'] = self.state.get('TAS, km/h')
                self.basic_telemetry['flapState'] = self.state.get('flaps, %')
                self.basic_telemetry['gearState'] = self.state.get('gear, %')
                
                self.connected = True
            else:
                self.connected = False # Not fully connected if indicators/state are invalid

            # Optionally fetch comments and events
            if comments:
                self.get_comments()
            else:
                self.comments = [] # Clear comments if not requested
            
            if events:
                self.get_events()
            else:
                self.events = {} # Clear events if not requested

            return self.connected

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # War Thunder API is not responding or not running
            self.status = WT_NOT_RUNNING
            # Clear all telemetry data if not connected
            self.state = {}
            self.indicators = {}
            self.full_telemetry = {}
            self.map_info.map_valid = False
            self.map_info.grid_info = {"name": "UNKNOWN", "ULHC_lat": 0.0, "ULHC_lon": 0.0, "size_km": 65} # Reset grid_info
            return False
        except (json.JSONDecodeError, requests.exceptions.RequestException) as e: 
            # Catch JSONDecodeError and general RequestException for core API calls
            self.status = OTHER_ERROR
            print(f"JSON or Request error during core telemetry fetch: {e}")
            traceback.print_exc()
            return False
        except Exception as e:
            # Catch any other unexpected errors during telemetry fetch
            self.status = OTHER_ERROR
            print(f"An unexpected error occurred during telemetry fetch: {e}")
            traceback.print_exc()
            return False
#endregion
