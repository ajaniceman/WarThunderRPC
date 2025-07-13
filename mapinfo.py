'''
Module to query and access map and non-player object/vehicle data during War Thunder matches
'''

#region Imports
import os
import socket
import imagehash
from time import sleep
from requests import get
from PIL import Image, ImageDraw
from json.decoder import JSONDecodeError
from simplejson.errors import JSONDecodeError as simpleJSONDecodeError
from urllib.error import URLError
from urllib.request import urlretrieve
from requests.exceptions import ReadTimeout, ConnectTimeout
from math import radians, degrees, sqrt, sin, asin, cos, atan2
from maps import maps # Ensure this import is correct and maps.py is in the same directory
import traceback # Added for detailed error logging
#endregion

#region Global Configuration & Constants
# Local path for script execution
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
# Path where the map image will be saved
MAP_PATH = os.path.join(LOCAL_PATH, 'map.jpg')
# IP address of the local machine, used for War Thunder API access
IP_ADDRESS = socket.gethostbyname(socket.gethostname())

# API endpoints for map and object data
URL_MAP_IMG = 'http://{}:8111/map.img'.format(IP_ADDRESS)
URL_MAP_OBJ = 'http://{}:8111/map_obj.json'.format(IP_ADDRESS)
URL_MAP_INFO = 'http://{}:8111/map_info.json'.format(IP_ADDRESS)

# Hexadecimal color codes used by War Thunder to denote enemy units on the map
ENEMY_HEX_COLORS = ['#f40C00', '#ff0D00', '#ff0000']
# Maximum allowed Hamming distance for image hash comparison to consider maps a match
MAX_HAMMING_DIST = 3 # This value can be adjusted if hashes are consistently off by a small margin
# Earth's radius in kilometers, used for geographical calculations
EARTH_RADIUS_KM = 6378.137
# Timeout for API requests in seconds
REQUEST_TIMEOUT = 0.1

# Specific hash for the "Test Drive" map
TEST_DRIVE_HASH = imagehash.hex_to_hash("e08080050fcfefe7")
#endregion

#region Helper Functions - Geographical Calculations
def hypotenuse(a: float, b: float) -> float:
    '''
    Find the length of the hypotenuse side of a right triangle.
    
    Args:
        a:
            One side of the right triangle.
        b:
            The other side of the right triangle.
    
    Returns:
            Length of the hypotenuse.
    '''
    
    return sqrt((a ** 2) + (b ** 2))

def coord_bearing(lat_1: float, lon_1: float, lat_2: float, lon_2: float) -> float:
    '''
    Find the bearing (in degrees) between two latitude/longitude coordinates (decimal degrees).
    
    Args:
        lat_1:
            First point's latitude (decimal degrees).
        lon_1:
            First point's longitude (decimal degrees).
        lat_2:
            Second point's latitude (decimal degrees).
        lon_2:
            Second point's longitude (decimal degrees).
    
    Returns:
            Bearing in degrees between point 1 and 2 (0-360).
    '''
    
    deltaLon_r = radians(lon_2 - lon_1)
    lat_1_r = radians(lat_1)
    lat_2_r = radians(lat_2)

    x = cos(lat_2_r) * sin(deltaLon_r)
    y = cos(lat_1_r) * sin(lat_2_r) - sin(lat_1_r) * cos(lat_2_r) * cos(deltaLon_r)

    return (degrees(atan2(x, y)) + 360) % 360

def coord_dist(lat_1: float, lon_1: float, lat_2: float, lon_2: float) -> float:
    '''
    Find the total distance (in km) between two latitude/longitude coordinates (decimal degrees).
    Uses the Haversine formula for accurate distance over a sphere.
    
    Args:
        lat_1:
            First point's latitude (decimal degrees).
        lon_1:
            First point's longitude (decimal degrees).
        lat_2:
            Second point's latitude (decimal degrees).
        lon_2:
            Second point's longitude (decimal degrees).
    
    Returns:
            Distance in km between point 1 and 2.
    '''
    
    lat_1_rad = radians(lat_1)
    lon_1_rad = radians(lon_1)
    lat_2_rad = radians(lat_2)
    lon_2_rad = radians(lon_2)
    
    d_lat = lat_2_rad - lat_1_rad
    d_lon = lon_2_rad - lon_1_rad
    
    a = (sin(d_lat / 2) ** 2) + cos(lat_1_rad) * cos(lat_2_rad) * (sin(d_lon / 2) ** 2)
    
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))

def coord_coord(lat: float, lon: float, dist: float, bearing: float) -> list:
    '''
    Finds the latitude/longitude coordinates 'dist' km away from the given 'lat' and 'lon'
    coordinate along the given compass 'bearing'.
    
    Args:
        lat:
            First point's latitude (decimal degrees).
        lon:
            First point's longitude (decimal degrees).
        dist:
            Distance in km the second point should be from the first point.
        bearing:
            Bearing in degrees from the first point to the second.
    
    Returns:
            Latitude and longitude in decimal degrees of the second point.
    '''
    
    brng = radians(bearing)
    lat_1 = radians(lat)
    lon_1 = radians(lon)
    
    lat_2 = asin(sin(lat_1) * cos(dist / EARTH_RADIUS_KM) + cos(lat_1) * sin(dist / EARTH_RADIUS_KM) * cos(brng))
    lon_2 = lon_1 + atan2(sin(brng) * sin(dist / EARTH_RADIUS_KM) * cos(lat_1), cos(dist / EARTH_RADIUS_KM) - sin(lat_1) * sin(lat_2))
    
    return [degrees(lat_2), degrees(lon_2)]
#endregion

#region Helper Functions - Map Grid & Object Coordinates
def get_grid_info(map_img: Image) -> dict:
    '''
    Compares the current map image from the browser interface to pre-calculated map hashes
    to identify the map and provide its geographical information. Supports multiple hashes per map.

    Args:
        map_img:
            PIL.Image object of the current map's JPEG.

    Returns:
        Dictionary with map metadata. Example -
            {'name': 'Kursk',
             'ULHC_lat': 51.16278580067218,
             'ULHC_lon': 36.906235369488115,
             'size_km' : 65,
             'detected_hash': 'abcdef1234567890'},
        Returns a default "UNKNOWN" dictionary with the detected hash if no match is found.
    '''

    current_image_hash = None # Initialize to None
    try:
        # Generate the perceptual hash as an ImageHash object for the current map
        current_image_hash = imagehash.average_hash(map_img)
    except Exception as e:
        print(f"ERROR: Failed to generate image hash for map. This might happen with corrupted map images or if War Thunder API returns an invalid image. Error: {e}")
        traceback.print_exc()
        # If hashing fails, return UNKNOWN immediately with a placeholder hash
        return {"name": "UNKNOWN", "ULHC_lat": 0.0, "ULHC_lon": 0.0, "size_km" : 65, "detected_hash": "ERROR_HASH"}
    
    # --- Special handling for Test Drive map ---
    if current_image_hash - TEST_DRIVE_HASH <= 0: # Check for exact or very close match
        print("DEBUG: parse_map_metadata: Test Drive map recognized.")
        return {"name": "Test Drive", "ULHC_lat": 0.0, "ULHC_lon": 0.0, "size_km": 65, "detected_hash": str(current_image_hash)}


    # Initialize with a distance greater than MAX_HAMMING_DIST to ensure any valid match is better
    best_match = (MAX_HAMMING_DIST + 1, "UNKNOWN") 

    found_exact_match = False
    # Iterate through each known map by its name defined in the 'maps' module
    for map_name, map_data in maps.items():
        if "hashes" in map_data and isinstance(map_data["hashes"], list):
            for stored_hash_str in map_data["hashes"]:
                # Skip empty hash strings to prevent ValueError
                if not stored_hash_str:
                    continue
                try:
                    # Convert the stored hexadecimal hash string back to an ImageHash object
                    stored_image_hash = imagehash.hex_to_hash(stored_hash_str)
                except ValueError:
                    print(f"WARNING: Invalid hash string '{stored_hash_str}' found for map '{map_name}' in maps.py. Skipping.")
                    continue
                
                # Calculate Hamming distance between the current map's hash and the stored hash
                distance = current_image_hash - stored_image_hash

                # If this is the best match found so far and within the acceptable limit
                if distance <= MAX_HAMMING_DIST and distance < best_match[0]:
                    best_match = (distance, map_name)
                    if distance == 0: # Exact match found, no need to check further hashes for this map
                        found_exact_match = True
                        break 
            if found_exact_match: # If exact match found for any hash of this map, break outer loop
                break 

    # If a match was found within MAX_HAMMING_DIST
    if best_match[0] <= MAX_HAMMING_DIST:
        matched_map_name = best_match[1]
        matched_map_data = maps[matched_map_name].copy() # Create a copy to avoid modifying the original maps dictionary
        matched_map_data['name'] = matched_map_name # Explicitly add the 'name' key for clarity
        matched_map_data['detected_hash'] = str(current_image_hash) # Add the detected hash
        return matched_map_data
    else:
        # No match found within the specified Hamming distance
        # Return UNKNOWN dictionary including the detected hash
        return {"name": "UNKNOWN",
                "ULHC_lat": 0.0,
                "ULHC_lon": 0.0,
                "size_km" : 65,
                "detected_hash": str(current_image_hash)}

def find_obj_coords(x: float, y: float, map_size: float, ULHC_lat: float, ULHC_lon: float) -> list:
    '''
    Converts an object's normalized x/y coordinates (0-1) on the map image to
    estimated real-world latitude and longitude.
    
    Args:
        x:
            The normalized horizontal distance of the object from the upper-left corner (0=left, 1=right).
        y:
            The normalized vertical distance of the object from the upper-left corner (0=top, 1=bottom).
        map_size:
            The length/width of the map in km (all maps are assumed to be square).
        ULHC_lat:
            The true world estimated latitude of the map's upper-left hand corner point.
        ULHC_lon:
            The true world estimated longitude of the map's upper-left hand corner point.
    
    Returns:
            Estimated latitude and longitude (decimal degrees) of the object's position.
    '''
    
    dist_x = x * map_size
    dist_y = y * map_size
    dist = hypotenuse(dist_x, dist_y) # Distance from ULHC to object in km
    
    # Calculate initial bearing from ULHC to object
    bearing = degrees(atan2(y, x)) + 90
    
    if bearing < 0:
        bearing += 360 # Normalize bearing to 0-360 degrees
    
    return coord_coord(ULHC_lat, ULHC_lon, dist, bearing)
#endregion

#region Map Object Class
class map_obj(object):
    """
    Represents a single object (vehicle, airfield, capture zone, etc.) detected on the War Thunder map.
    Parses raw API data and calculates real-world coordinates.
    """
    def __init__(self, map_obj_entry: dict = {}, map_size: float = 65, ULHC_lat: float = 0, ULHC_lon: float = 0):
        '''
        Initializes a map_obj instance.
        
        Args:
            map_obj_entry:
                A single object/vehicle entry from the JSON scraped from http://localhost:8111/map_obj.json.
            map_size:
                The length/width of the map in km (all maps are square).
            ULHC_lat:
                The true world estimated latitude of the map's upper-left hand corner point.
            ULHC_lon:
                The true world estimated longitude of the map's upper-left hand corner point.
        '''
        
        self.type = '' # Type of object (e.g., 'airfield', 'tank')
        self.icon = '' # Icon type (e.g., 'heavytank', 'fighter', 'capture_zone')
        self.hex_color = '' # Hexadecimal color of the object as reported by API
        self.friendly = True # True if friendly, False if enemy (based on color/blink)
        
        self.position = [0, 0] # Normalized x-y coordinates on the map image (0-1 range)
        self.position_delta = [0, 0] # Change in x-y position, used for heading
        self.south_end = [0, 0] # For airfields: normalized x-y of south end of runway
        self.east_end = [0, 0] # For airfields: normalized x-y of east end of runway
        
        self.position_ll = [0, 0] # Estimated latitude and longitude (decimal degrees)
        self.south_end_ll = [0, 0] # For airfields: estimated lat/lon of south end
        self.east_end_ll = [0, 0] # For airfields: estimated lat/lon of east end
        self.runway_dir = 0 # For airfields: calculated bearing of the runway
        
        # Boolean flags to easily identify object types
        self.airfield = False
        self.heavy_tank = False
        self.medium_tank = False
        self.light_tank = False
        self.spg = False # Self-Propelled Gun / Tank Destroyer
        self.spaa = False # Self-Propelled Anti-Aircraft
        self.wheeled = False # AI only
        self.tracked = False # AI only
        self.aaa = False # Anti-Aircraft Artillery
        self.bomber = False # Also includes helicopters
        self.heavy_fighter = False
        self.fighter = False
        self.ship = False
        self.torpedo_boat = False
        self.tank_respawn = False
        self.bomber_respawn = False
        self.fighter_respawn = False
        self.capture_zone = False
        self.defend_point = False
        self.bombing_point = False
        
        self.hdg = 0 # Heading of the object in degrees (0-360)
        
        if map_obj_entry:
            self.update(map_obj_entry, map_size, ULHC_lat, ULHC_lon)
    
    def update(self, map_obj_entry: dict, map_size: float, ULHC_lat: float, ULHC_lon: float):
        '''
        Updates object attributes based on the provided map context and raw API entry.
        
        Args:
            map_obj_entry:
                A single object/vehicle entry from the JSON scraped from http://localhost:8111/map_obj.json.
            map_size:
                The length/width of the map in km (all maps are square).
            ULHC_lat:
                The true world estimated latitude of the map's upper-left hand corner point.
            ULHC_lon:
                The true world estimated longitude of the map's upper-left hand corner point.
        '''
        
        self.type = map_obj_entry.get('type', '')
        self.icon = map_obj_entry.get('icon', '')
        self.hex_color = map_obj_entry.get('color', '')
        
        # Determine friendliness based on color or blinking status
        if (self.hex_color in ENEMY_HEX_COLORS) or map_obj_entry.get('blink', False):
            self.friendly = False
        else:
            self.friendly = True
                
        # Set boolean flags for object types
        self.airfield = (self.type.lower() == 'airfield')
        self.bombing_point = (self.icon.lower() == 'bombing_point')
        if self.bombing_point: self.friendly = False # Bombing points are always enemy
        
        self.heavy_tank = (self.icon.lower() == 'heavytank')
        self.medium_tank = (self.icon.lower() == 'mediumtank')
        self.light_tank = (self.icon.lower() == 'lighttank')
        self.spg = (self.icon.lower() == 'tankdestroyer')
        self.spaa = (self.icon.lower() == 'spaa')
        self.wheeled = (self.icon.lower() == 'wheeled')
        self.tracked = (self.icon.lower() == 'tracked')
        self.aaa = (self.icon.lower() == 'airdefence')
        self.bomber = (self.icon.lower() == 'bomber') # Includes helicopters
        self.heavy_fighter = (self.icon.lower() == 'assault')
        self.fighter = (self.icon.lower() == 'fighter')
        self.ship = (self.icon.lower() == 'ship')
        self.torpedo_boat = (self.icon.lower() == 'torpedoboat')
        self.tank_respawn = (self.icon.lower() == 'respawn_base_tank')
        self.bomber_respawn = (self.icon.lower() == 'respawn_base_bomber')
        self.fighter_respawn = (self.icon.lower() == 'respawn_base_fighter')
        self.capture_zone = (self.icon.lower() == 'capture_zone')
        self.defend_point = (self.icon.lower() == 'defending_point')
        if self.defend_point: self.friendly = True # Defend points are always friendly

        # Update position and heading
        self.position = [map_obj_entry.get('x', 0), map_obj_entry.get('y', 0)]
        
        self.position_delta = [map_obj_entry.get('dx', 0), map_obj_entry.get('dy', 0)]
        if self.position_delta != [0, 0]:
            self.hdg = degrees(atan2(*self.position_delta)) + 90
            if self.hdg < 0:
                self.hdg += 360
        else:
            self.hdg = 0
        
        # Update airfield specific coordinates and runway direction
        self.south_end = [map_obj_entry.get('sx', 0), map_obj_entry.get('sy', 0)]
        self.east_end = [map_obj_entry.get('ex', 0), map_obj_entry.get('ey', 0)]
        
        if self.airfield: # Only calculate for airfields
            self.south_end_ll = find_obj_coords(*self.south_end, map_size, ULHC_lat, ULHC_lon)
            self.east_end_ll = find_obj_coords(*self.east_end, map_size, ULHC_lat, ULHC_lon)
            self.runway_dir = coord_bearing(*self.south_end_ll, *self.east_end_ll)
        else:
            self.south_end_ll = [0, 0]
            self.east_end_ll = [0, 0]
            self.runway_dir = 0
        
        # Calculate real-world coordinates for the object's main position
        self.position_ll = find_obj_coords(*self.position, map_size, ULHC_lat, ULHC_lon)
#endregion

#region MapInfo Class
class MapInfo(object):
    """
    Manages fetching, parsing, and providing access to War Thunder map data
    and information about objects present on the map.
    """
    def __init__(self):
        self.map_valid = False # True if map data was successfully retrieved and parsed
        self.map_objs = [] # List of map_obj instances representing objects on the map
        self.grid_info = {"name": "UNKNOWN", "ULHC_lat": 0.0, "ULHC_lon": 0.0, "size_km": 65} # Geographical info about the map
        self.player_found = False # True if the player's object is found on the map
        self.player_lat = 0.0 # Player's estimated latitude
        self.player_lon = 0.0 # Player's estimated longitude
        self.map_img = None # PIL Image object of the map
        self.map_draw = None # PIL ImageDraw object for drawing on the map image
        self.info = {} # Raw map_info.json data
        self.obj = [] # Raw map_obj.json data

    def download_map_image(self) -> bool:
        '''
        Downloads the current map image (map.img) from the API.
        Returns True on successful download, False otherwise.
        '''
        try:
            urlretrieve(URL_MAP_IMG, MAP_PATH)
            self.map_img = Image.open(MAP_PATH)
            return True
        except (URLError, ReadTimeout, ConnectTimeout, OSError) as e:
            # OSError for Image.open if file doesn't exist or is corrupted
            print(f'WARNING: Could not download or open map.jpg (might be normal in hangar): {e}')
            self.map_img = None # Ensure map_img is None on failure
            return False
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during map image download: {e}")
            traceback.print_exc()
            self.map_img = None
            return False

    def fetch_map_json_data(self) -> bool:
        '''
        Fetches map_info.json and map_obj.json from the API.
        Populates self.info and self.obj.
        Returns True on successful fetch, False otherwise.
        '''
        try:
            self.info = get(URL_MAP_INFO, timeout=REQUEST_TIMEOUT).json()
            self.obj = get(URL_MAP_OBJ, timeout=REQUEST_TIMEOUT).json()
            return True
        except (ReadTimeout, ConnectTimeout) as e:
            # These are common when not in a match, treat as warning
            print(f'WARNING: Could not connect to map JSON API (might be normal in hangar): {e}')
            self.info = {}
            self.obj = []
            return False
        except (JSONDecodeError, simpleJSONDecodeError) as e:
            # JSONDecodeError is also common when not in a match, treat as warning
            print(f'WARNING: Map JSON data malformed or empty (might be normal in hangar): {e}')
            self.info = {}
            self.obj = []
            return False
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during map JSON data fetch: {e}")
            traceback.print_exc()
            self.info = {}
            self.obj = []
            return False

    def parse_map_metadata(self):
        '''
        Parses the downloaded map image and JSON data to set grid_info and map_objs.
        This method should only be called after successful download of image and JSONs.
        '''
        self.map_valid = False # Assume invalid until proven otherwise
        if self.map_img and self.info: # Ensure image and info are present
            # Call get_grid_info only once
            map_grid_info_result = get_grid_info(self.map_img)
            self.grid_info = map_grid_info_result # Assign the result to self.grid_info

            if self.grid_info.get('name') != "UNKNOWN":
                self.map_valid = True
                self.map_objs = [] # Clear previous objects
                self.player_found = False # Reset player found status

                for obj_entry in self.obj:
                    current_obj = map_obj(obj_entry,
                                          self.grid_info['size_km'],
                                          self.grid_info['ULHC_lat'],
                                          self.grid_info['ULHC_lon'])
                    self.map_objs.append(current_obj)
                    
                    if obj_entry.get('icon') == 'Player':
                        self.player_found = True
                        self.player_lat = current_obj.position_ll[0]
                        self.player_lon = current_obj.position_ll[1]
                
                self.map_draw = ImageDraw.Draw(self.map_img) # Initialize draw object if map is valid
            else:
                # Updated log message for unknown maps
                print(f"WARNING: Map image not recognized. Hash: {self.grid_info.get('detected_hash', 'N/A')}. Please use the 'Update Map Data' button in the GUI and provide this hash from the console log.")
        else:
            print("DEBUG: parse_map_metadata: Missing map image or info data to parse.")

    #region Object Type Filters
    def airfields(self) -> list:
        '''
        Returns a list of `map_obj` instances that are airfields currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.airfield]
    
    def bombing_points(self) -> list:
        '''
        Returns a list of `map_obj` instances that are bomb points currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.bombing_point]
    
    def heavy_tanks(self) -> list:
        '''
        Returns a list of `map_obj` instances that are heavy tanks currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.heavy_tank]
    
    def medium_tanks(self) -> list:
        '''
        Returns a list of `map_obj` instances that are medium tanks currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.medium_tank]
    
    def light_tanks(self) -> list:
        '''
        Returns a list of `map_obj` instances that are light tanks currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.light_tank]
    
    def SPGs(self) -> list:
        '''
        Returns a list of `map_obj` instances that are Self-Propelled Guns (SPGs) currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.spg]
    
    def SPAAs(self) -> list:
        '''
        Returns a list of `map_obj` instances that are Self-Propelled Anti-Aircraft (SPAAs) currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.spaa]
    
    def tanks(self) -> list:
        '''
        Returns a combined list of all tank-type `map_obj` instances currently in the match.
        Includes heavy, medium, light tanks, SPGs, and SPAAs.
        '''
        output = []
        output.extend(self.heavy_tanks())
        output.extend(self.medium_tanks())
        output.extend(self.light_tanks())
        output.extend(self.SPGs())
        output.extend(self.SPAAs())
        return output
    
    def wheeled_AIs(self) -> list:
        '''
        Returns a list of `map_obj` instances that are wheeled AI units currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.wheeled]
    
    def tracked_AIs(self) -> list:
        '''
        Returns a list of `map_obj` instances that are tracked AI units currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.tracked]
    
    def AAAs(self) -> list:
        '''
        Returns a list of `map_obj` instances that are Anti-Aircraft Artillery (AAAs) currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.aaa]
    
    def bombers(self) -> list:
        '''
        Returns a list of `map_obj` instances that are bombers (including helicopters) currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.bomber]
    
    def heavy_fighters(self) -> list:
        '''
        Returns a list of `map_obj` instances that are heavy fighters currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.heavy_fighter]
    
    def fighters(self) -> list:
        '''
        Returns a list of `map_obj` instances that are fighters currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.fighter]
    
    def ships(self) -> list:
        '''
        Returns a list of `map_obj` instances that are ships (including torpedo boats) currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.ship or obj.torpedo_boat]
    
    def planes(self) -> list:
        '''
        Returns a combined list of all plane-type `map_obj` instances currently in the match.
        Includes bombers, heavy fighters, and fighters.
        '''
        output = []
        output.extend(self.bombers())
        output.extend(self.heavy_fighters())
        output.extend(self.fighters())
        return output
    
    def tank_respawns(self) -> list:
        '''
        Returns a list of `map_obj` instances that are tank respawn points currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.tank_respawn]
    
    def bomber_respawns(self) -> list:
        '''
        Returns a list of `map_obj` instances that are bomber respawn points currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.bomber_respawn]
    
    def fighter_respawns(self) -> list:
        '''
        Returns a list of `map_obj` instances that are fighter respawn points currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.fighter_respawn]
    
    def plane_respawns(self) -> list:
        '''
        Returns a combined list of all plane respawn `map_obj` instances currently in the match.
        Includes bomber and fighter respawn points.
        '''
        output = []
        output.extend(self.bomber_respawns())
        output.extend(self.fighter_respawns())
        return output
    
    def capture_zones(self) -> list:
        '''
        Returns a list of `map_obj` instances that are capture zones currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.capture_zone]
    
    def defend_points(self) -> list:
        '''
        Returns a list of `map_obj` instances that are defend points currently in the match.
        '''
        return [obj for obj in self.map_objs if obj.defend_point]
    #endregion
#endregion
