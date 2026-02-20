# How to Distribute the Activity Tracker Application

## Overview
To share this application, you will create a standalone **folder** that contains the application and all its dependencies. This method (Directory Mode) ensures the application **starts instantly** compared to a single file.

## Prerequisites
1.  Ensure you have **Python** installed.
2.  Ensure you have installed the requirements:
    ```powershell
    pip install -r requirements.txt
    pip install pyinstaller
    ```

## Step 1: Build the Application
Open your terminal in the project folder and run:

```powershell
pyinstaller HRMS_Time_Tracker.spec
```

This will create a `dist` folder.
Inside `dist`, you will find a folder named `HRMS_Time_Tracker`. This folder contains the executable and necessary files.

## Step 2: Prepare the Distribution Package
Create a ZIP file of the `HRMS_Time_Tracker` folder found in `dist`.
Send this **ZIP file** to your users along with the Tampermonkey script.

## Step 3: Deployment Instructions for Users

Send the ZIP file to your users with these instructions:

### 1. Install the Browser Script
1.  Install the **Tampermonkey** extension for Chrome/Edge.
2.  Create a new script, paste the contents of `tampermonkey_script_v5.0_final.js`, and save.

### 2. Run the Desktop App
1.  Unzip the folder to a permanent location (e.g., `Documents`).
2.  Open the folder and double-click `HRMS_Time_Tracker.exe`.
3.  **Login** with your email and password.
4.  The app will minimize to the System Tray and start automatically on future restarts.

### 3. Usage
- Go to the HRMS Portal and punch in.
- The tracker will detect your punch-in and start tracking automatically.
- Just allow the app to run in the background.

## Support
If the app fails to start, check the `debug.log` file created in the folder.
It contains details on startup errors or path issues.

The app is configured for "Instant Startup" mode, so it should appear login screen within 1-2 seconds.
