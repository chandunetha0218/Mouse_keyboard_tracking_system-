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

### 2. Activity Logic
- **Tracker Class**: run in a separate thread.
- **Mouse Listener**: `on_move`, `on_click`, `on_scroll` -> updates `last_active_time`.
- **Keyboard Listener**: `on_press` -> updates `last_active_time`.
- **Timer Loop**: Checks every 1 second:
    - If `now - last_active > 5 minutes`: State = IDLE
    - Else: State = WORKING
    - Log transition events (e.g., Working -> Idle).

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
