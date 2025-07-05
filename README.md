# **War Thunder Discord Rich Presence**

## **Credits and Shoutout**

A huge shoutout to [ValerieOSD](https://github.com/ValerieOSD/WarThunderRPC) for their foundational work on War Thunder RPC scripts, which served as the inspiration and starting point for this project. Their efforts made this possible\!

**This project was developed with the assistance of Gemini, an AI assistant.**

This Python script integrates with War Thunder's in-game telemetry API to update your Discord Rich Presence, displaying your current activity in the game, including the vehicle you're using, the map, and its Battle Rating (BR).

## **Features**

* **Automatic Status Updates:** Dynamically updates your Discord status based on your in-game activity.  
* **Vehicle Display:** Shows the name of the vehicle you are currently driving or piloting.  
* **Battle Rating (BR) Integration:** Fetches and displays the Realistic Battle (RB) Battle Rating for your selected vehicle directly from the War Thunder Wiki.  
* **Map Display:** Shows the name of the map you are playing on.  
* **Hangar/Match Detection:** Differentiates between being in the hangar/menu and being in an active match.  
* **Formatted Vehicle Names:** Displays vehicle names cleanly, e.g., "T 90M 2020 (USSR)" instead of internal game names.
**Note on Map Display:** The feature for displaying the correct map name and image in the Discord Rich Presence is still under development and may not always show accurate information.

## **Visuals**

Here are some screenshots of the Discord Rich Presence in action:

| Screenshot 1 | Screenshot 2 | Screenshot 3 |
| :---- | :---- | :---- |
|  ![Discord Rich Presence in Hangar](images/InMatch.png) | ![Discord Rich Presence In-Game](images/T90M.png) | ![Discord Rich Presence Example](images/T90MDetails.png) |
| *Caption for Screenshot 1: Discord Rich Presence displaying in-game status, showing the map (Sinai) and the vehicle (T 90M 2020).* | *Caption for Screenshot 2: Discord Rich Presence displaying hangar status, showing the vehicle (T 90M 2020\) being viewed.* | *Caption for Screenshot 3: A detailed view of the Discord Rich Presence, showing the vehicle's full name, country, and Battle Rating (BR).* |


## **Setup Instructions**

### **1\. Prerequisites**

* **Python 3.x:** Make sure you have Python 3 installed on your system. You can download it from [python.org](https://www.python.org/downloads/).  
* **Discord Desktop Client:** The Discord application must be running for the Rich Presence to display.  
* **War Thunder:** The game needs to be installed and running.

### **2\. Clone the Repository**

First, clone this repository to your local machine:

git clone https://github.ajaniceman/WarThunderRPC.git  
cd WarThunderRPC


### **3\. Install Dependencies**

Navigate to the cloned directory and install the required Python libraries using pip:

pip install \-r requirements.txt

### **4\. Discord Developer Application Setup**

For your Discord Rich Presence to work, you need to create a Discord Application:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).  
2. Click "New Application".  
3. Give your application a name (e.g., "War Thunder RPC").  
4. Copy the **Application ID**. This is your CLIENT\_ID.  
5. Open main.py and replace the placeholder CLIENT\_ID value with your copied Application ID:  
   CLIENT\_ID \= "YOUR\_APPLICATION\_ID\_HERE"

6. Go to "Rich Presence" \-\> "Art Assets" in your application settings.  
7. Upload images for your Rich Presence. At a minimum, you'll need:  
   * logo (for general War Thunder presence)  
   * hangar (for when you're in the hangar)  
   * You might also want to upload images for specific maps (e.g., tunisia, kursk) and vehicles if you want custom icons instead of the encyclopedia links. The script currently uses encyclopedia links for vehicles, but map images are looked for locally.
   **Note:** I will provide a mapPictures folder containing various map images (for both air and ground versions) that you can upload as assets to your Discord application for richer map display.

### **5\. Running the Script**

#### **A. Manually (for testing)**

You can run the script manually from your terminal:

python main.py

*(Use pythonw main.py on Windows if you want to run it without a console window.)*

#### **B. Automatically on Game Launch (Windows \- Recommended)**

To have the script run automatically when you launch War Thunder, you can use Windows Task Scheduler:

1. **Open Task Scheduler:** Search for "Task Scheduler" in the Windows Start menu.  
2. **Create Basic Task:** In the right-hand pane, click "Create Basic Task...".  
3. **Name the Task:** Give it a descriptive name, e.g., "War Thunder RPC Launcher". Click "Next".  
4. **Trigger:** Select "When a specific event is logged". Click "Next".  
5. **Event:**  
   * **Log:** Select "Application".  
   * **Source:** Find "Application".  
   * **Event ID:** You need the Event ID for War Thunder's launch.  
     * Launch War Thunder.  
     * Open **Event Viewer** (search for it in Start menu).  
     * Navigate to Windows Logs \-\> Application.  
     * Look for a recent "Information" event from "Application" related to aces.exe (War Thunder's executable). Note down the "Event ID" (commonly 1000 or 1001).  
     * Enter this Event ID in Task Scheduler.  
6. **Action:** Select "Start a program". Click "Next".  
7. **Program/script:**  
   * **Program/script:** Enter the full path to your pythonw.exe (e.g., C:\\Users\\YourUser\\AppData\\Local\\Programs\\Python\\Python39\\pythonw.exe).  
   * **Add arguments (optional):** Enter the full path to your main.py script (e.g., "C:\\Path\\To\\Your\\WarThunder-RPC\\main.py"). **Ensure the path is enclosed in double quotes if it contains spaces.**  
   * **Start in (optional):** Enter the directory where main.py is located (e.g., C:\\Path\\To\\Your\\WarThunder-RPC).  
8. **Finish:** Click "Next" and then "Finish".

#### **C. Automatically on Login (Windows \- Simpler)**

This method will launch the script every time you log into your Windows account.

1. **Open Startup Folder:** Press Win \+ R, type shell:startup, and press Enter.  
2. **Create Shortcut:** Right-click inside the Startup folder, select New \-\> Shortcut.  
3. **Type the location of the item:**  
   * Enter the path to your Python interpreter followed by the path to your script:  
     "C:\\Path\\To\\Your\\pythonw.exe" "C:\\Path\\To\\Your\\WarThunder-RPC\\main.py"  
     (Replace with your actual paths. Use pythonw.exe to run without a console window.)  
4. **Name the Shortcut:** Give it a name like "War Thunder RPC". Click "Finish".