# HRMS Time Tracker - Setup Guide

This guide explains how to set up the **Time Tracker Application** on your computer.

## Prerequisites
- A Windows Computer (Laptop/Desktop)
- Google Chrome (or any browser supporting Tampermonkey)

## Step 1: Install the Desktop App
1.  Download the `HRMS_Time_Tracker.exe` file.
2.  Move it to a permanent folder (e.g., `Documents\TimeTracker`).
3.  Right-click -> **Create Shortcut** (Optional, for easy access).
4.  Double-click to run. You might see a "Windows Defender" warning. Click **More Info** -> **Run Anyway**.
5.  Login with your regular credentials.

## Step 2: Install Browser Extension
1.  Open Chrome and search for **Tampermonkey Extension**.
2.  Install it.
3.  Click the Extension Icon -> **Create a new script**.
4.  Delete *everything* in the editor.
5.  Copy-Paste the code from `tampermonkey_script_v5.0_final.js` (provided with this app).
6.  Click **File** -> **Save**.

## How it Works (Zero Touch)
1.  **Punch In** on the HRMS Portal.
2.  The Tracker will **Automatically Start** (It might take 10-15 seconds to sync).
3.  **Punch Out** or **Logout** stops the tracker.

## Troubleshooting
- **Not Syncing?** Make sure you are on the "Attendance" page in HRMS.
- **App Closed?** Just open `.exe` again. If you are already punched in for the day, it will auto-resume.
