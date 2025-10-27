# **War Thunder Rich Presence Monitor**

## **🚀 What is this application?**

The War Thunder Rich Presence Monitor automatically connects to your running War Thunder client and updates your Discord status (Rich Presence) in real-time.

It provides detailed information to your friends on Discord about:

* The **Vehicle** you are currently piloting or driving (scraped from the War Thunder Wiki).  
* The **Battle Rating (BR)** of the vehicle.  
* The **Map** you are playing on (including custom map image assets).  
* Your current **Status** (In Ground Battle, Idle in Hangar, etc.).

## **🛠️ Setup Instructions (Quick Start)**

You only need to complete the following steps once.

### **1\. Discord Application Setup**

1. **Create an Application:** Go to the [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications).  
2. Click **"New Application"** and name it War Thunder.  
3. Go to the **"General Information"** tab and find the **Application ID**.  
4. **Copy this ID.** This is the ID you will enter into the app later.  

### **2\. Application Configuration**

1. **Download and Run:** Download the WarthunderRPC.exe file and run it.  
2. **Enter ID:** Paste the Discord **Application ID** you copied in Step 1 into the "Discord App ID" field.  
3. **Save:** Click the **"Save ID"** button. The application will remember this ID.  
4. **Start:** Click the **"Start RPC"** button.

The app will now begin monitoring War Thunder. If successful, the log output will show **"Connected to Discord RPC"**.

## **🔄 Automatic Map Updates**

This application is designed for zero-friction maintenance. The list of map hashes (which frequently change after Gaijin updates) is kept on a central server.

* Every time you start the app, it automatically downloads the latest list of map hashes and updates your local configuration.  
* **You never need to download a new .exe just because a map hash changed.**

## **❓ Troubleshooting**

| Issue | Potential Solution |
| :---- | :---- |
| **"Failed to connect to Discord RPC"** | Ensure the official **Discord desktop application** is running. |
| **"Error reading mission data" / "Offline"** | 1\. Ensure War Thunder is running. 2\. Check your Windows Firewall to ensure it is not blocking the internal War Thunder API endpoint (127.0.0.1:8111). |
| **App won't start monitoring** | Check the log output for errors. Ensure you have entered and **Saved** the correct 18-digit Discord Application ID. |

