import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
from urllib.parse import urlparse # Import urlparse for clean fallback name

# Set a user-agent to make the request look like a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_vehicle_name(wiki_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Scrapes the War Thunder Wiki page for the vehicle's official display name and RB BR.
    
    Args:
        wiki_url: The URL to the specific vehicle's wiki page (e.g., https://wiki.warthunder.com/unit/f3d_1).
        
    Returns:
        A tuple (display_name, rb_br) where display_name is the official name (string) 
        and rb_br is a string like '12.3' or None if not found.
    """
    print(f"--- Starting scrape for URL: {wiki_url} ---")
    
    try:
        response = requests.get(wiki_url, headers=HEADERS, timeout=5)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Scrape failed: Request error for {wiki_url}: {e}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # --- 1. Extract Vehicle Name (PRIORITY: .game-unit_name div) ---
    display_name = None
    
    # Look for the dedicated unit name div, which is usually the cleanest name
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
        # Extract the last segment of the URL path (e.g., 'f_16a_block_10')
        url_path = urlparse(wiki_url).path
        raw_id = url_path.split('/')[-1]
        # Clean it up: replace underscores with spaces and title case it
        display_name = raw_id.replace('_', ' ').title().strip()


    # --- 2. Extract Realistic Battle (RB) BR ---
    rb_br = None
    # Find all divs that hold BR items
    br_items = soup.find_all('div', class_='game-unit_br-item')
    
    for item in br_items:
        mode_div = item.find('div', class_='mode')
        value_div = item.find('div', class_='value')
        
        # Check if the mode is 'RB' (Realistic Battle) and the value exists
        if mode_div and mode_div.get_text(strip=True) == 'RB' and value_div:
            rb_br = value_div.get_text(strip=True)
            # BR found, exit the loop
            break 
    
    if display_name:
        print(f"Scrape successful. Vehicle name found: {display_name}")
    if rb_br:
        print(f"Scrape successful. RB BR found: {rb_br}")
        
    return display_name, rb_br
