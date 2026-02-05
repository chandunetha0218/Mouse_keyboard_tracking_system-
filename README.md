# Activity Tracker Application

## Overview
This is a desktop application that tracks user activity (Working vs Idle) based on Mouse and Keyboard usage and reports it to a central website.

## Setup
1. Install Python (if not installed).
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Running the App
```powershell
python main.py
```

## Configuration
- **API Connection**:
  - Open `api_client.py` and implement your actual API calls in `login` and `send_activity_log`.
  - Currently, it assumes a mock successful login.

## Building for Distribution
To share this with your team as a standalone `.exe`:
1. Install PyInstaller:
   ```powershell
   pip install pyinstaller
   ```
2. Build the executable:
   ```powershell
   pyinstaller --noconsole --onefile main.py
   ```
3. Share the `dist/main.exe` file.
