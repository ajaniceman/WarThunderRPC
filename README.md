# **✈️ War Thunder Rich Presence Monitor**

## **🚀 What is this application?**

The **War Thunder Rich Presence Monitor** is a lightweight application that automatically connects to your running War Thunder client and updates your Discord status (Rich Presence) in real-time.

It provides detailed, up-to-the-second information about your game state to your friends on Discord, including:

* The **Vehicle** you are currently piloting or driving (scraped directly from the War Thunder Wiki).  
* The **Battle Rating (BR)** of the vehicle.  
* The **Map** you are playing on (with custom image assets for the large icon).  
* Your current **Status** (In Ground Battle, Idle in Hangar, etc.).

## **🛠️ Setup Instructions (Quick Start)**

You only need to complete the following steps once.

### **1\. Download the Application**

The easiest way to get the app is through the **Releases** page:

* [**Click Here to Download the Latest Release**](https://github.com/ajaniceman/WarThunderRPC/releases/tag/v1.0.0)  
* Download the WarthunderRPC.exe file from the **Assets** section of the latest release.

### **2\. Discord Application Setup (Mandatory)**

1. **Create an Application:** Go to the [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications).  
2. Click **"New Application"** and it **MUST** be named **"War Thunder"** for the rich presence to display correctly.  
3. Go to the **"General Information"** tab and find the **Application ID**.  
4. **Copy this ID.** You will enter this into the app later.

### **3\. Application Configuration & Launch**

1. **Run:** Launch the downloaded WarthunderRPC.exe file.  
2. **Enter ID:** Paste the Discord **Application ID** you copied in Step 2 into the "Discord App ID" field.  
3. **Save:** Click the **"Save ID"** button.  
4. **Start:** Click the **"Start RPC"** button.

The app will now begin monitoring War Thunder. If successful, the log output will show **"Connected to Discord RPC"**.

**⚠️ IMPORTANT: Do NOT Edit config.json**

The application automatically creates a file named config.json in its directory to store your Application ID and the map hash database. This file is mandatory for the application to function. **Do not modify or delete this file manually.** If you need to change your Application ID, use the client's built-in settings.

*Note: War Thunder must be running for the application to detect game state.*

## **🔄 Automatic Map Updates**

This application is designed for zero-friction maintenance. The list of map hashes (which frequently change after Gaijin updates) is kept on a central server.

* Every time you start the app, it automatically downloads the latest list of map hashes and updates your local configuration.  
* **You never need to download a new executable just because a map hash changed.**

## **❓ Troubleshooting**

| Issue | Potential Solution |
| :---- | :---- |
| **"Failed to connect to Discord RPC"** | Ensure the official **Discord desktop application** is running. |
| **"Error reading mission data" / "Offline"** | 1\. Ensure War Thunder is running. 2\. Check your Windows Firewall to ensure it is not blocking the internal War Thunder API endpoint (127.0.0.1:8111). |
| **App won't start monitoring** | Check the log output for errors. Ensure you have entered and **Saved** the correct 18-digit Discord Application ID. |

