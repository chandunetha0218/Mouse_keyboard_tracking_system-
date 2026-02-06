# implementation_plan.md

## Goal
Create a Python Desktop Application that tracks User Activity (Active vs Idle) based on mouse/keyboard inputs and reports this data to a web backend.

## Architecture

### 1. Desktop Client (Python)
- **UI Framework**: `customtkinter` (Modern UI wrapper for tkinter)
- **Activity Monitoring**: `pynput` library.
    - We will NOT record specific keys (privacy).
    - We will only record the *timestamp* of the last action.
    - Logic: If `current_time - last_action_time > IDLE_THRESHOLD` (e.g., 5 mins), status = Idle.
- **Backend Communication**: `requests` library.
    - Endpoint: `POST /api/activity-log`
    - payload: `{user_id, status, timestamp, duration}`
- **Authentication**: simple Login screen in the app to get a token/user_ID from the website.

### 2. Activity Logic (Strict Event-Driven)
- **Rules**:
    - **Start**: ONLY when HRMS "Punch In" is detected (Transition or Fresh). Time must be 10:00 - 18:00.
    - **Stop**: ONLY when:
        1. HRMS "Punch Out" detected.
        2. HRMS "Logout" detected (or Session Invalid).
        3. App Closing.
    - **Resume**: NO auto-resume on app restart/login if "Punch In" is stale. Require fresh "Punch In" event or explicit user confirmation. (User Requirement: "Resume only after Punch In again").
- **Reporting**:
    - Generate Report on **STOP** (Logout/Punch Out).
    - Append to Daily Report.
    - Reset Stats at 00:00 midnight.
    - Track "Sessions" list: `[{start, end, work, idle}, ...]`.

### 3. Desktop Client (Python)
- **Main Controller**:
    - `handle_sync(punch_in, punch_out, is_logged_in)`
    - `check_logout_condition()`
- **Persistence**: Save `daily_sessions.json`.

## Proposed Layout
- **Login Screen**: URL config, Username, Password.
- **Dashboard**:
    - Status Indicator (Green: Working, Yellow: Idle, Grey: Offline).
    - "Today's Time": `HH:MM`.
    - Minimalist design.

## File Structure
- `main.py`: Entry point and UI Controller.
- `tracker.py`: Background logic for pynput.
- `api_client.py`: Handling HTTP requests.
- `config.py`: Settings (Idle threshold, API URLs).
- `requirements.txt`: Dependencies.

## Next Steps
1. Create `requirements.txt`
2. Implement `tracker.py` (Core Logic)
3. Implement `main.py` (UI)
