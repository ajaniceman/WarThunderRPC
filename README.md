# War Thunder Discord Rich Presence

## Credits and Shoutout

A huge shoutout to [ValerieOSD](https://github.com/ValerieOSD/WarThunderRPC) for their foundational work on War Thunder RPC scripts, which served as the inspiration and starting point for this project. Their efforts made this possible\!

**This project was developed with the assistance of Gemini, an AI assistant.**

This Python script integrates with War Thunder's in-game telemetry API to update your Discord Rich Presence, displaying your current activity in the game, including the vehicle you're using, the map, and its Battle Rating (BR).

## **Features**

* **Dynamic Status:** Automatically updates your Discord status when you're in the hangar, in a match, or in a test drive.  
* **Vehicle Information:** Displays the vehicle you are currently viewing or playing, with its correct in-game name (scraped from War Thunder Wiki).  
* **Map Recognition:** Identifies the current map you are playing on and displays it.  
* **Battle Rating (BR):** Fetches and displays the Battle Rating of your current vehicle.  
* **Game State Detection:** Distinguishes between hangar, in-match, and test drive states.  
* **Robustness:** Includes error handling for API connectivity issues and unrecognized map data.

## **Visuals**

Here are some screenshots of the Discord Rich Presence in action:

| Screenshot 1 | Screenshot 2 | Screenshot 3 |
| :---- | :---- | :---- |
|  ![Discord Rich Presence in Hangar](images/InMatch.png) | ![Discord Rich Presence In-Game](images/T90M.png) | ![Discord Rich Presence Example](images/T90MDetails.png) |
| *Caption for Screenshot 1: Discord Rich Presence displaying in-game status, showing the map (Sinai) and the vehicle (T-90M).* | *Caption for Screenshot 2: Discord Rich Presence displaying hangar status, showing the vehicle (T-90M\) being viewed.* | *Caption for Screenshot 3: A detailed view of the Discord Rich Presence, showing the vehicle's full name, country, and Battle Rating (BR).* |

**Note on Map Display:** For map images to appear in your Discord Rich Presence, you need to upload them as "Art Assets" to your Discord Application in the [Discord Developer Portal](https://discord.com/developers/applications) (under Rich Presence \> Art Assets). The script expects these assets to be named according to the map's lowercased, underscore-separated name (e.g., sinai, golan\_heights). Please be aware that it can take some time for newly uploaded assets to propagate and become visible in your Rich Presence.

### **1\. Prerequisites**

* **Python 3.x:** Make sure you have Python 3 installed on your system. You can download it from [python.org](https://www.python.org/downloads/). (Only if running from source, not the .exe)  
* **Discord Desktop Client:** The Discord application must be running for the Rich Presence to display.  
* **War Thunder:** The game needs to be installed and running.

### **2\. Download the Application (Recommended for Users)**

The easiest way to use the War Thunder RPC Launcher is to download the pre-built executable:

1. Go to the [GitHub Releases page](https://github.com/ajaniceman/WarThunderRPC/releases/tag/V1.0.0) of this repository.
2. Under the latest release, download the WarThunderRPC.exe file (for Windows).  
3. Run the downloaded .exe file.

### **3\. Discord Developer Application Setup (Mandatory)**

For your Discord Rich Presence to work, you need to create and configure a Discord Application. This is where you get your unique CLIENT\_ID and upload images that Discord will display.

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).  
2. Click "New Application".  
3. Give your application a name (e.g., "War Thunder").  
4. Copy the **Application ID**. This is your CLIENT\_ID.  
5. **Open the War Thunder RPC Launcher application.**  
6. Paste your copied **Application ID** into the "Discord Client ID" field on the main window.  
7. Click the "Save ID" button. This will save your Client ID so you don't have to enter it every time.  
8. Go to "Rich Presence" \-\> "Art Assets" in your Discord application settings.  
9. Upload images for your Rich Presence. At a minimum, you'll need:  
   * logo (for general War Thunder presence \- a square image, e.g., War Thunder logo)  
   * hangar (for when you're in the hangar \- a square image)  
   * You can also upload images for specific maps (e.g., tunisia, kursk) if you want custom icons for maps. The map\_info.py module expects map image files to be named after the map's internal name (e.g., sinai.jpg). These should be placed in a mapPictures folder next to your executable if you're distributing it.

### **4\. Using the War Thunder RPC Launcher**

The GUI application provides a user-friendly way to manage your Rich Presence:

1. **Start RPC:** Click the "Start RPC" button to begin updating your Discord status. The console will show logs, and the status label will indicate "RPC script running."  
2. **Stop RPC:** Click the "Stop RPC" button to halt the Rich Presence updates.  
3. **Hide Window:** Click the "Hide Window" button to minimize the application to your taskbar. The RPC script will continue running in the background. You can click the icon in your taskbar to bring the window back.  
4. **Settings:** Click the "Settings" button to open a new window with additional options:  
   * **Enable Detailed Logging:** Check this box for more verbose output in the console, useful for debugging. Remember to click "Save Configuration" if you change this.  
   * **Auto-start RPC on App Launch (Work in Progress):** This feature is planned for future updates to automatically start the RPC when the launcher opens.  
   * **Update Map Data:** Open a utility to add new map hashes to the maps.py file if the application doesn't recognize a map. You'll need the 16-character hash from the console log.  
   * **Clear Console:** Clears all messages from the console output.  
   * **Custom Messages Tab:** Here you can customize the text messages displayed for different in-game states (hangar, match, loading, test drive, vehicle BR, and country). Remember to click "Save Message Templates" after making changes or "Reset to Default" to revert.

### **5\. Running from Source (for Developers)**

If you intend to modify the script or run it directly from source:

1. **Clone the Repository:**  
   git clone https://github.ajaniceman/WarThunderRPC.git  
   cd WarThunder-RPC

2. **Install Dependencies:**  
   pip install \-r requirements.txt

3. **Run the GUI Launcher:**  
   python WarThunderRPC.py

   *(Use pythonw WarThunderRPC.py on Windows if you want to run it without a console window.)*

### **6\. Creating the Executable (for Distribution)**

To create a standalone executable (.exe on Windows) that doesn't require Python installed on the user's machine:

1. **Open your terminal or command prompt** and navigate to the root directory of this project (where WarThunderRPC.py is located).  
2. **Run the PyInstaller command:**  
   **For Windows:**  
   pyinstaller --noconsole --onefile --add-data "main.py;." --add-data "telemetry.py;." --add-data "mapinfo.py;." --add-data "maps.py;." --add-data "mapPictures;mapPictures" --add-data "logger_config.py;." --hidden-import requests --hidden-import pypresence --hidden-import html --hidden-import PIL --hidden-import PIL.Image --hidden-import imagehash --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont WarThunderRPC.py

   **For macOS/Linux:**  
   pyinstaller \--noconsole \--onefile \--add-data "main.py:." \--add-data "telemetry.py:." \--add-data "mapinfo.py:." \--add-data "maps.py:." \--add-data "mapPictures:mapPictures" \--add-data "logger\_config.py:." \--hidden-import requests \--hidden-import pypresence \--hidden-import html WarThunderRPC.py

3. **Find the executable:** After the process completes, your executable will be located in the newly created dist folder (e.g., YourProject/dist/WarThunderRPC.exe). You can distribute this single file.

## **Troubleshooting**

* **"War Thunder is not running"**: Ensure War Thunder is actively running.  
* **"Could not connect to map JSON API" / "Map JSON data malformed or empty"**: This can happen if War Thunder is in the hangar or a loading screen. If it persists during a match, ensure your firewall isn't blocking Python's access to localhost:8111.  
* **"Map image not recognized"**: The script uses perceptual hashing to identify maps. If a new map is added to War Thunder or an existing map's image changes significantly, its hash might not be in maps.py. Use the "Update Map Data" button in the GUI settings and provide the hash from the console log.  
* **Incorrect Vehicle Names / BRs**: The script attempts to scrape vehicle names and BRs from the War Thunder Wiki. If the wiki's HTML structure changes, or if a vehicle page has an unusual format, the scraping might fail or produce incorrect results.  
* **ValueError: invalid literal for int() with base 16: ''**: This error indicates an empty string in the hashes list within your maps.py file. Ensure all hash entries are valid hexadecimal strings or the list is empty (\[\]).