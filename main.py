import customtkinter as ctk
import threading
import time
import tkinter
import os
import json
import datetime
import json
import datetime

# Lazy imports for performance
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from matplotlib.figure import Figure
# import matplotlib.pyplot as plt

from tracker import ActivityTracker
from api_client import ApiClient
import pystray
from PIL import Image, ImageDraw
import sys
import winreg

import logging

# ... (imports)

class TimeTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Setup Logging
        try:
            self.log_file = self.get_app_path("debug.log")
            logging.basicConfig(filename=self.log_file, level=logging.INFO, 
                                format='%(asctime)s - %(levelname)s - %(message)s')
            logging.info("Application Started")
        except Exception as e:
            print(f"Logging setup failed: {e}")

        try:
            # Window Setup
            logging.info("Setting up Window...")
            self.title("Activity Tracker v2.2")
            self.geometry("600x800")
            self.resizable(False, False)
            
            # State
            logging.info("Initializing State...")
            self.is_compact = False
            self.tracking_active = False
            self.start_time = None
            self.total_work_seconds = 0
            self.total_idle_seconds = 0
            self.current_date = datetime.date.today().strftime("%Y-%m-%d")
            
            # Sync State
            self.last_processed_punch_in = None
            
            # Analytics
            self.hourly_stats = {} 
            self.load_local_stats()
            
            # Logic Components
            logging.info("Initializing Logic Components...")
            self.target_seconds = 8 * 3600 # 8 Hours
            self.current_state = "WAITING"
            self.tracker = ActivityTracker(idle_threshold_seconds=10) 
            self.api = ApiClient("https://hrms-420.netlify.app/.netlify/functions/api")
            self.app_running = True
            self.last_sync_time = time.time()
            
            # Office Hours Configuration
            self.OFFICE_START_HOUR = 10 
            self.OFFICE_END_HOUR = 18   
            self.threads_started = False 
            
            # GUI
            logging.info("Creating GUI Container...")
            self.container = ctk.CTkFrame(self)
            self.container.pack(fill="both", expand=True)
            
            # UI Setup
            logging.info("Calling setup_ui()...")
            self.setup_ui()
            logging.info("setup_ui() completed.")
            
            # Protocols
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.update_ui_loop()
            
            # Tray
            logging.info("Creating Tray Icon...")
            self.tray_icon = None
            self.create_tray_icon()
            
            # Login
            logging.info("Checking Launch Arguments...")
            is_startup_launch = "--startup" in sys.argv
            if is_startup_launch:
                print("[SYSTEM] Detected Automatic Startup. Launching in Tray.")
                logging.info("Startup Mode: TRUE")
            
            logging.info("Calling check_auto_login()...")
            self.check_auto_login(startup=is_startup_launch)

            logging.info("Initialization Complete - Loop Running.")

        except Exception as e:
            logging.critical(f"CRASH DURING STARTUP: {e}", exc_info=True)
            print(f"CRASH: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def setup_ui(self):
        """Initializes the UI components."""
        # 1. Login View
        self.login_view = self.create_login_view()
        
        # 2. Dashboard View
        # 2. Dashboard View (Lazy Loading for Startup Speed)
        self.dashboard_view = None
        
        # 3. Compact View
        self.compact_view = self.create_compact_view()

        # Show Login initially
        self.show_login()

    def is_within_working_hours(self):
        """Checks if tracking is allowed (10 AM - 6 PM)."""
        now_hour = datetime.datetime.now().hour
        return self.OFFICE_START_HOUR <= now_hour < self.OFFICE_END_HOUR

    def get_current_user_identifier(self):
        """Get a safe filename-friendly identifier for the current user."""
        if hasattr(self.api, 'employee_id') and self.api.employee_id:
            return str(self.api.employee_id).replace(" ", "_")
        return "default"

    def get_app_path(self, filename):
        """Returns the absolute path for a file relative to the executable."""
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Running as .py script
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, filename)

    # --- CREDENTIAL MANAGEMENT ---
    def save_creds(self, email, password):
        """Saves credentials securely (base64 encoded simple obsfucation) for auto-login."""
        try:
            import base64
            import json
            enc_user = base64.b64encode(email.encode()).decode()
            enc_pass = base64.b64encode(password.encode()).decode()
            data = {"u": enc_user, "p": enc_pass}
            file_path = self.get_app_path("user_creds.json")
            with open(file_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving creds: {e}")

    def load_creds(self):
        """Loads saved credentials."""
        try:
            import base64
            import json
            file_path = self.get_app_path("user_creds.json")
            if not os.path.exists(file_path):
                return None, None
            
            with open(file_path, "r") as f:
                data = json.load(f)
            
            email = base64.b64decode(data["u"]).decode()
            password = base64.b64decode(data["p"]).decode()
            return email, password
        except:
            return None, None

    def check_auto_login(self, startup=True):
        """Attempts to auto-login if credentials exist. Startup=True means Minimize to Tray."""
        self.startup_mode = startup
        logging.info(f"Checking Auto Login. Startup Mode: {startup}")
        email, password = self.load_creds()
        if email and password:
            logging.info("Credentials found. Attempting Auto-Login.")
            # Ensure UI exists before accessing
            if hasattr(self, 'entry_user'):
                self.entry_user.delete(0, 'end')
                self.entry_user.insert(0, email)
                self.entry_pass.delete(0, 'end')
                self.entry_pass.insert(0, password)
                # Show status
                self.lbl_error.configure(text="Auto-logging in... (Server Waking Up)", text_color="orange")
                self.handle_login(silent=startup)
        else:
            logging.info("No Credentials found. Showing Login Screen.")

    def handle_login(self, silent=False):
        """Triggers the login process in a background thread."""
        user = self.entry_user.get()
        password = self.entry_pass.get()
        
        self.is_silent_login = silent # Store state for result handler
        logging.info(f"Starting Login Process for user: {user} (Silent={silent})")
        
        if not user or not password:
            self.lbl_error.configure(text="Please enter both email and password")
            return

        # UI Feedback: Show loading state
        self.lbl_error.configure(text="Connecting... (Server Waking Up, < 60s)", text_color="orange")
        for child in self.login_view.winfo_children():
            if isinstance(child, ctk.CTkButton) and child.cget("text") == "Login":
                child.configure(state="disabled", text="Logging in...")
                self.login_btn_ref = child

        # Start Login Thread
        threading.Thread(target=self._do_login_thread, args=(user, password), daemon=True).start()

    def _do_login_thread(self, user, password):
        """Background thread logic for authentication."""
        url = "https://hrms-420.netlify.app/.netlify/functions/api"
        logging.info("Contacting Login API...")
        self.api = ApiClient(url)
        success, msg = self.api.login(user, password)
        logging.info(f"Login API Result: Success={success}, Msg={msg}")

        # Update UI back on the Main Thread
        self.after(0, lambda: self._handle_login_result(success, msg, user, password))

    def logout(self):
        """Clear session and go back to login."""
        creds_path = self.get_app_path("user_creds.json")
        if os.path.exists(creds_path): # Clear auto-login
            os.remove(creds_path)
        
        # Save current stats one last time before clearing
        self.save_local_stats()
        
        self.stop_tracking() # Ensure tracking stops if active
        
        # Reset Timers for next login
        self.total_work_seconds = 0
        self.total_idle_seconds = 0
        self.hourly_stats = {} # Reset stats on explicit logout
        
        self.show_login()

    def create_tray_icon(self):
        """Creates the system tray icon."""
        try:
            print("[DEBUG] Creating Tray Icon...")
            # Create a simple icon image (Red Box for visibility)
            self.icon_image = Image.new('RGB', (64, 64), color=(255, 0, 0))
            draw = ImageDraw.Draw(self.icon_image)
            draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
            
            menu = (
                pystray.MenuItem("Show", self.show_window, default=True),
                pystray.MenuItem("Quit", self.quit_app)
            )
            
            self.tray_icon = pystray.Icon("name", self.icon_image, "Activity Tracker", menu)
            
            # Start tray in a separate thread because it can be blocking
            print("[DEBUG] Starting Tray Icon Thread...")
            threading.Thread(target=self._run_tray, daemon=True).start()
            
        except Exception as e:
            print(f"Tray Icon Error: {e}")

    def _run_tray(self):
        try:
            print("[DEBUG] Tray Icon Loop Started")
            self.tray_icon.run()
            print("[DEBUG] Tray Icon Loop Ended")
        except Exception as e:
            print(f"[DEBUG] Tray Run Failed: {e}")

    def show_window(self, icon=None, item=None):
        """Restores the window from the tray."""
        self.after(0, self.deiconify)

    def quit_app(self, icon=None, item=None):
        """Fully exits the application."""
        self.app_running = False
        self.tracking_active = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        os._exit(0) # Force kill all threads

    def on_closing(self):
        """Overrides the 'X' button to minimize to tray instead of closing."""
        print("[DEBUG] on_closing called")
        # Only minimize if tray is actually available (created)
        if self.tray_icon:
            print("[DEBUG] Tray Icon exists. Withdrawing window.")
            self.withdraw() # Hide window
            if hasattr(self.tray_icon, 'notify'):
                try:
                    self.tray_icon.notify("Tracker minimized to tray. Right-click icon to Quit.", "Activity Tracker")
                except:
                    pass
            # Also ensure the icon is visible/running? 
            # In pystray, if it's running in a thread, it should be fine.
        else:
            # Fallback: Just quit if tray failed to prevent app from becoming stuck
            print("Tray Icon not available. Exiting app.")
            self.quit_app()

    def create_login_view(self):
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        
        label = ctk.CTkLabel(frame, text="Employee Login", font=("Roboto", 24, "bold"))
        label.pack(pady=(40, 30))

        self.entry_user = ctk.CTkEntry(frame, placeholder_text="Username")
        self.entry_user.pack(pady=10, fill="x")

        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="Password", show="*")
        self.entry_pass.pack(pady=10, fill="x")

        btn_login = ctk.CTkButton(frame, text="Login", command=self.handle_login)
        btn_login.pack(pady=30, fill="x")
        
        self.lbl_error = ctk.CTkLabel(frame, text="", text_color="red")
        self.lbl_error.pack()

        return frame

    def create_dashboard_view(self):
        # Lazy Import heavy dependencies
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        
        # Logout Button (Top Right)
        btn_logout = ctk.CTkButton(frame, text="Logout", width=60, height=20, fg_color="red", command=self.logout)
        btn_logout.pack(anchor="ne", pady=(0, 10))

        # Compact Mode Button (Top Left)
        btn_compact = ctk.CTkButton(frame, text="↗ Mini Mode", width=80, height=20, fg_color="#555", command=self.toggle_compact_mode)
        btn_compact.place(x=0, y=0)
        
        # 1. Status Header
        self.lbl_status = ctk.CTkLabel(frame, text="WAITING FOR PUNCH IN", font=("Roboto", 24, "bold"), text_color="grey")
        self.lbl_status.pack(pady=(10, 5))

        # USER INFO LABEL (ID & ROLE)
        self.lbl_user_info = ctk.CTkLabel(frame, text="", font=("Roboto", 14), text_color="silver")
        self.lbl_user_info.pack(pady=(0, 5))

        # CONNECTIVITY STATUS
        self.lbl_bridge = ctk.CTkLabel(frame, text="Browser Sync: 🔴 Waiting...", font=("Roboto", 12), text_color="#A0A0A0")
        self.lbl_bridge.pack(pady=(0, 5))
        
        self.lbl_punch_time = ctk.CTkLabel(frame, text="", font=("Roboto", 12), text_color="#2CC985")
        self.lbl_punch_time.pack(pady=(0, 10))

        # 2. Statistics Grid
        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        
        # --- BUTTON: Work Time --- (Read Only)
        self.btn_start = ctk.CTkButton(
            stats_frame,
            text="WORK TIME\n\n00:00:00",
            font=("Roboto", 20, "bold"),
            fg_color="#1E1E1E", 
            border_width=2,
            border_color="#2CC985",
            hover_color="#1E1E1E", # No hover effect
            height=100,
            command=None # DISABLED
        )
        self.btn_start.pack(side="left", expand=True, fill="both", padx=5, pady=5)
        
        # --- BUTTON: Idle Time --- (Read Only)
        self.btn_stop = ctk.CTkButton(
            stats_frame,
            text="IDLE TIME\n\n00:00:00",
            font=("Roboto", 20, "bold"),
            fg_color="#1E1E1E",
            border_width=2,
            border_color="#FFB347",
            hover_color="#1E1E1E", # No hover effect
            height=100,
            command=None # DISABLED
        )
        self.btn_stop.pack(side="right", expand=True, fill="both", padx=5, pady=5)
        
        # Remove old labels (since button has text)
        self.lbl_work_time = None 
        self.lbl_idle_time = None

        # 3. Progress Bar (Target 7h)
        self.lbl_target = ctk.CTkLabel(frame, text="Target: 8 Hours")
        self.lbl_target.pack(pady=(10, 0))
        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(5, 20))

        # --- MOVED BUTTON HERE FOR VISIBILITY ---
        self.btn_report = ctk.CTkButton(frame, text="Download Daily Report (PDF)", command=self.generate_report, fg_color="#3B8ED0")
        self.btn_report.pack(pady=(0, 20), fill="x", padx=10)

        # 4. Matplotlib Chart
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#242424') # Matches Dark Mode
        self.ax.set_facecolor('#242424')
        
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        # 5. Console/Log
        self.console = ctk.CTkTextbox(frame, height=80)
        self.console.pack(pady=10, fill="x")
        self.console.configure(state="disabled")

        return frame

    def create_compact_view(self):
        """Creates the Mini/Compact interface."""
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        
        # Expand Button
        btn_expand = ctk.CTkButton(frame, text="↙ Expand", width=60, height=20, fg_color="#555", command=self.toggle_compact_mode)
        btn_expand.pack(pady=(5, 5), anchor="ne")
        
        self.lbl_compact_status = ctk.CTkLabel(frame, text="ACTIVE", font=("Roboto", 14, "bold"), text_color="green")
        self.lbl_compact_status.pack(pady=0)

        self.lbl_compact_work = ctk.CTkLabel(frame, text="00:00:00", font=("Roboto", 32, "bold"), text_color="#2CC985")
        self.lbl_compact_work.pack(pady=5)
        
        self.lbl_compact_idle = ctk.CTkLabel(frame, text="Idle: 00:00:00", font=("Roboto", 12), text_color="#FFB347")
        self.lbl_compact_idle.pack(pady=0)
        
        return frame

    def toggle_compact_mode(self):
        """Switches between Full and Mini modes."""
        if not self.is_compact:
            # Switch to Compact
            self.dashboard_view.pack_forget()
            self.compact_view.pack(fill="both", expand=True)
            self.geometry("300x160")
            self.attributes('-topmost', True) # Always on top
            self.is_compact = True
        else:
            # Switch to Full
            self.compact_view.pack_forget()
            self.dashboard_view.pack(fill="both", expand=True)
            self.geometry("600x800")
            self.attributes('-topmost', False)
            self.is_compact = False

    def show_login(self):
        if self.dashboard_view:
            self.dashboard_view.pack_forget()
        self.login_view.pack(fill="both", expand=True)

    def show_dashboard(self):
        # Lazy Load View
        if self.dashboard_view is None:
            self.dashboard_view = self.create_dashboard_view()

        self.login_view.pack_forget()
        self.dashboard_view.pack(fill="both", expand=True)
        
        # Display User Details
        if hasattr(self.api, 'employee_id') and hasattr(self.api, 'course_role'):
            self.lbl_user_info.configure(text=f"ID: {self.api.employee_id}  |  Role: {self.api.course_role}")
        
        self.lbl_status.configure(text="SYNCHRONIZING WITH HRMS...", text_color="orange")

        # Start the portal sync loop in background
        self.app_running = True
        
        # Start core threads (Guard against duplication on re-login)
        if not self.threads_started:
            threading.Thread(target=self.sync_with_portal, daemon=True).start()
            threading.Thread(target=self.server_polling_loop, daemon=True).start()
            threading.Thread(target=self.start_command_server, daemon=True).start()
            self.threads_started = True
            self.log_msg("System: Browser Bridge Active on Port 12345")

    def start_command_server(self):
        """
        Listens on localhost:12345 for /sync commands from Browser.
        """
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import urllib.parse
        
        app_ref = self 

        class CommandHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                # LOG ALL REQUESTS FOR DEBUGGING
                print(f"[BRIDGE] GET {self.path}")
                
                parsed_path = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed_path.query)
                
                if parsed_path.path == '/sync':
                    # Extract punch data from query params
                    punch_in = query.get('punch_in', [None])[0]
                    punch_out = query.get('punch_out', [None])[0]
                    attendance_date = query.get('date', [None])[0]
                    worked_str = query.get('worked', [None])[0]
                    
                    print(f"[SYNC] Received data for {attendance_date}: In={punch_in}, Out={punch_out}, Worked={worked_str}")
                    
                    # Update local bridge status
                    app_ref.after(0, lambda: app_ref.lbl_bridge.configure(text="Browser Sync: 🟢 Connected", text_color="green"))
                    
                    # Process sync on main thread
                    app_ref.after(0, lambda: app_ref.process_sync_data(punch_in, punch_out, attendance_date, worked_str=worked_str))
                    
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Sync Received")
                
                elif parsed_path.path == '/heartbeat':
                    # Update local bridge status
                    app_ref.after(0, lambda: app_ref.lbl_bridge.configure(text="Browser Sync: 🟢 Connected", text_color="green"))
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Alive")

                # Maintain legacy support for /start and /stop
                elif parsed_path.path == '/start':
                    app_ref.after(0, app_ref.start_tracking)
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                elif parsed_path.path == '/stop':
                    app_ref.after(0, app_ref.stop_tracking)
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                elif parsed_path.path == '/show':
                    app_ref.after(0, app_ref.show_window)
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Window Restored")
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args): pass

        while True:
            try:
                # Use 127.0.0.1 instead of localhost for better Windows compatibility
                server = HTTPServer(('127.0.0.1', 12345), CommandHandler)
                print("[BRIDGE] Command Server Successfully Started on Port 12345")
                server.serve_forever()
            except OSError as e:
                print(f"[BRIDGE] Port 12345 busy or unavailable: {e}. Retrying in 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"[BRIDGE] Critical Server Error: {e}")
                time.sleep(5)

    def process_sync_data(self, punch_in, punch_out, attendance_date, server_work_seconds=None, status=None, worked_str=None):
        """Processes punch data received via bridge or polling."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # Validation: Only process if it's for today
        if attendance_date and str(attendance_date) != today_str:
            print(f"[SYNC] WARNING: Data Date '{attendance_date}' != System Date '{today_str}'. Ignoring.")
            return

        print(f"[SYNC] Received - In: '{punch_in}', Out: '{punch_out}', Status: '{status}', Worked: '{worked_str}'")

        # 1. HANDLE LOGOUT (Strict Stop)
        if status == "logged_out":
            if self.tracking_active:
                print("[SYNC] User Logged Out. Stopping Tracker.")
                self.after(0, lambda: self.stop_tracking("Logged Out"))
            return

        # 2. HANDLE PUNCH DATA
        invalid_vals = [None, "null", "none", "", "-", "--", "--:--", "undefined", "false", "Active", "Working...", "LATE"]
        is_punched_in = punch_in not in invalid_vals
        is_punched_out = punch_out not in invalid_vals

        if is_punched_in:
            # 3. CHECK FOR NEW SESSION (Log context only, don't reset timers)
            if self.last_processed_punch_in and punch_in != self.last_processed_punch_in:
                print(f"[SYNC] New Punch In Detected ({self.last_processed_punch_in} -> {punch_in}). Resuming from daily cumulative time.")
                self.log_msg(f"System: New punch session detected ({punch_in}). Resuming tracked time.")

            # Update reference immediately (thread-safe for simple assignment)
            self.last_processed_punch_in = punch_in

            # 4. STRICT STATE ENFORCEMENT
            if is_punched_out:
                # Case: Punched Out (Completed Session)
                # Check status thread-safely? self.tracking_active is a bool, ok to read.
                if self.tracking_active:
                     print(f"[SYNC] Punch Out Detected ({punch_out}). Stopping.")
                     # Make sure we generate the report for the session that just ended
                     self.after(0, lambda: self.stop_tracking("Punched Out"))
            
            else:
                # Case: Punched In + Active (Working)
                if not self.tracking_active:
                    print(f"[SYNC] Active Punch detected ({punch_in}). Force Starting.")
                    self.after(0, lambda: self.start_tracking(punch_in_time_str=punch_in))
                
                # 5. SYNC TIMERS
                if worked_str and worked_str not in invalid_vals:
                    # Sync with WORKED column from HRMS (Absolute Truth)
                    self.after(0, lambda: self.sync_timers_with_worked_str(worked_str))
                else:
                    # Fallback to calculated sync (Drift prone)
                    self.after(0, lambda: self.sync_timers_with_punch_in(punch_in))
        
        else:
            # Case: No Punch In Data (or Invalid)
            if self.tracking_active:
                 print(f"[SYNC] No active punch detected. Stopping.")
                 self.after(0, lambda: self.stop_tracking("No Data")) 

    def sync_timers_with_worked_str(self, worked_str):
        """Parses '0h 1m 9s' and updates total_work_seconds."""
        try:
            # Expected format: "0h 1m 9s" or "2h 30m"
            parts = worked_str.split(' ')
            h, m, s = 0, 0, 0
            for p in parts:
                p = p.lower()
                if 'h' in p: h = int(p.replace('h',''))
                if 'm' in p: m = int(p.replace('m',''))
                if 's' in p: s = int(p.replace('s',''))
            
            server_seconds = h*3600 + m*60 + s
            
            # MUTUAL EXCLUSIVITY FIX:
            # HRMS 'Worked' usually means total elapsed time. To get actual 'Work' time,
            # we subtract our locally tracked idle seconds.
            actual_work_seconds = max(0, server_seconds - self.total_idle_seconds)
            
            # Sync if drift > 5 seconds
            if abs(actual_work_seconds - self.total_work_seconds) > 5:
                 print(f"[SYNC] Updating Work Time (Excluding Idle): {self.total_work_seconds}s -> {actual_work_seconds}s")
                 self.total_work_seconds = actual_work_seconds
        except Exception as e:
            print(f"[SYNC] Error parsing worked time '{worked_str}': {e}")

    def sync_timers_with_punch_in(self, punch_in_str):
        """Calculates work time based on: Current Time - Punch In - Total Idle."""
        try:
            # Parse HRMS Punch In Time
            import dateutil.parser as dparser
            # If it's just a time like "14:10", parse result will have today's date if we provide a default
            now = datetime.datetime.now()
            
            # Robust parsing with default for today
            try:
                punch_dt = dparser.parse(punch_in_str, default=now)
            except Exception as pe:
                print(f"[SYNC] Parsing error: {pe}. Attempting manual split.")
                # Manual fallback for HH:MM:SS or HH:MM
                pts = punch_in_str.split(':')
                if len(pts) >= 2:
                    h = int(pts[0])
                    m = int(pts[1])
                    s = int(pts[2]) if len(pts) > 2 else 0
                    punch_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                else:
                    raise pe

            # Ensure precision
            elapsed_total = (now - punch_dt).total_seconds()
            
            # Work Time = Elapsed - Total Idle (Accrued locally)
            calculated_work = max(0, elapsed_total - self.total_idle_seconds)
            
            # Log the calculation for debugging
            # print(f"[DEBUG] Sync Calc: Now={now.strftime('%H:%M:%S')}, Punch={punch_dt.strftime('%H:%M:%S')}, Elapsed={int(elapsed_total)}s, Local_Idle={int(self.total_idle_seconds)}s -> Work={int(calculated_work)}s")

            # Only update if there's a significant difference (Sync) or if we are at 0
            # Only update if there's a significant difference (Sync) or if we are at 0
            if self.total_work_seconds == 0 or abs(calculated_work - self.total_work_seconds) > 300:
                 print(f"[SYNC] Adjusting Timer: Local={self.total_work_seconds}s -> ServerCalc={calculated_work}s")
                 self.total_work_seconds = calculated_work
                
        except Exception as e:
            print(f"[SYNC] Time Sync Error: {e} for string '{punch_in_str}'")

    def _do_login_thread(self, user, password):
        """Background thread logic for authentication."""
        url = "https://hrms-420.netlify.app/.netlify/functions/api"
        self.api = ApiClient(url)
        success, msg = self.api.login(user, password)

        # Update UI back on the Main Thread
        self.after(0, lambda: self._handle_login_result(success, msg, user, password))

    def _handle_login_result(self, success, msg, user, password):
        """Processes login result and restores UI."""
        # Enable Button
        if hasattr(self, 'login_btn_ref'):
            self.login_btn_ref.configure(state="normal", text="Login")

        if success:
            self.save_creds(user, password)
            self.add_to_startup() # PERSISTENCE
            
            # Switch view first so it is ready
            self.show_dashboard()
            self.load_local_stats()
            self.lbl_error.configure(text="") # Clear errors
            
            # If auto-login, start minimized
            if hasattr(self, 'is_silent_login') and self.is_silent_login:
                print("Silent Login: Minimizing to Tray.")
                self.withdraw() # Minimizes/Hides the window
                if self.tray_icon and hasattr(self.tray_icon, 'notify'):
                    try:
                        self.tray_icon.notify("Ready (Running in Background)", "Activity Tracker")
                    except: pass
            
        else:
            self.lbl_error.configure(text=msg, text_color="red")

    def add_to_startup(self):
        """Adds the application to Windows Startup via Registry."""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "HRMSActivityTracker"
            
            # Determine path
            if getattr(sys, 'frozen', False):
                # Requesting executable path (PyInstaller)
                exe_path = f'"{sys.executable}"'
            else:
                # Running as script (python main.py)
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

            logging.info(f"Adding to Startup: {exe_path}")
            print(f"[SYSTEM] Adding to Startup: {exe_path}")

            # Append --startup flag for silent boot
            startup_path = f'{exe_path} --startup'
            
            logging.info(f"Registry Key Value: {startup_path}")

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, startup_path)
            winreg.CloseKey(key)
            logging.info("Successfully added to Registry Run Key.")
            print("[SYSTEM] Successfully added to Windows Startup.")
        except Exception as e:
            print(f"[SYSTEM] Failed to add to startup: {e}")

    def log_msg(self, msg):
        # Ensure UI updates happen on the Main Thread to prevent freezing
        self.after(0, lambda: self._log_msg_internal(msg))

    def _log_msg_internal(self, msg):
        self.console.configure(state="normal")
        self.console.insert("end", f"{msg}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_ui_loop(self):
        """Called every second by Tkinter main loop to refresh stats/charts."""
        work_str = self.format_time(self.total_work_seconds)
        idle_str = self.format_time(self.total_idle_seconds)

        # 1. Update Compact View (Always Available)
        if hasattr(self, 'compact_view') and self.compact_view:
             if self.tracking_active:
                  color = "green" if self.current_state == "WORKING" else "orange"
                  self.lbl_compact_status.configure(text=self.current_state, text_color=color)
             else:
                  self.lbl_compact_status.configure(text="OFFLINE", text_color="grey")
             
             self.lbl_compact_work.configure(text=work_str)
             self.lbl_compact_idle.configure(text=f"Idle: {idle_str}")

        # 2. Update Dashboard View (Only if Active)
        if hasattr(self, 'dashboard_view') and self.dashboard_view:
             if self.tracking_active:
                  color = "green" if self.current_state == "WORKING" else "orange"
                  self.lbl_status.configure(text=self.current_state, text_color=color)
             else:
                  self.lbl_status.configure(text="OFF THE CLOCK", text_color="grey")
             
             self.btn_start.configure(text=f"WORK TIME\n\n{work_str}")
             self.btn_stop.configure(text=f"IDLE TIME\n\n{idle_str}")
             
             # Update progress
             if self.target_seconds > 0:
                 progress = self.total_work_seconds / self.target_seconds
                 self.progress_bar.set(min(progress, 1.0))
             
             # Update Chart (Throttle to every 30s)
             if int(time.time()) % 30 == 0 and self.tracking_active:
                 self.update_chart()

        self.after(1000, self.update_ui_loop) # Reschedule

    def update_chart(self):
        self.ax.clear()
        
        labels = ['Working', 'Idle']
        sizes = [max(1, self.total_work_seconds), max(0, self.total_idle_seconds)]
        colors = ['#2CC985', '#FFB347'] # Green, Orange
        
        # Don't show chart if 0 data
        if self.total_work_seconds == 0 and self.total_idle_seconds == 0:
            return

        self.ax.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            startangle=90, colors=colors,
            textprops={'color':"white"}
        )
        self.ax.axis('equal')  
        self.fig.tight_layout()
        self.chart_canvas.draw()

    def server_polling_loop(self):
        """Dedicated thread to poll server status every 15 seconds."""
        while self.app_running:
            try:
                # We always poll if we are logged in, to detect punch transitions
                is_active, server_work_seconds, punch_data = self.api.check_punch_status()
                
                if punch_data:
                    self.after(0, lambda: self.process_sync_data(
                        punch_data.get('punch_in'), 
                        punch_data.get('punch_out'), 
                        punch_data.get('date'),
                        server_work_seconds=server_work_seconds
                    ))
            except Exception as e:
                print(f"[POLL] Error: {e}")
            time.sleep(15) 

    def sync_with_portal(self):
        """Background Thread: Accumulates time based on activity."""
        self.last_sync_time = time.time()
        
        while self.app_running:
            # --- rollover check ---
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            if today_str != self.current_date:
                self.log_msg(f"System: New day detected ({today_str}). Resetting daily stats.")
                print(f"[SYSTEM] Day Rollover: {self.current_date} -> {today_str}. Resetting counters.")
                
                # Full Reset for New Day
                self.total_work_seconds = 0
                self.total_idle_seconds = 0
                self.hourly_stats = {}
                self.current_date = today_str
                self.last_processed_punch_in = None # Reset reference for new day
                
                self.save_local_stats()
                # Update UI elements on main thread
                self.after(0, self.update_chart)
                self.after(0, lambda: self.lbl_punch_time.configure(text=""))

            now = time.time()
            delta = now - self.last_sync_time
            self.last_sync_time = now

            try:
                # RE-ENFORCE WORKING HOURS CHECK
                working_hours = self.is_within_working_hours()
                
                if self.tracking_active:
                    state, _ = self.tracker.get_status()
                    
                    # Update status text if out of hours
                    if not working_hours:
                        self.current_state = "AFTER HOURS (Paused)"
                    else:
                        self.current_state = state
                    
                    # ONLY ACCUMULATE TIME IF WITHIN 10 AM - 6 PM
                    if working_hours:
                        hour_key = datetime.datetime.now().strftime("%H") # e.g. "09", "10"
                        if hour_key not in self.hourly_stats:
                            self.hourly_stats[hour_key] = {"work": 0, "idle": 0}

                        if state == "WORKING":
                            self.total_work_seconds += delta
                            self.hourly_stats[hour_key]["work"] += delta
                        else:
                            self.total_idle_seconds += delta
                            self.hourly_stats[hour_key]["idle"] += delta
                    
                    # Upload Heartbeat (Every ~30 seconds)
                    # We still upload heartbeat to keep session alive, but maybe with "IDLE" or special status?
                    if int(now) % 30 == 0: 
                         status_to_send = state if working_hours else "OUT_OF_HOURS"
                         threading.Thread(target=self.api.upload_activity_log, args=(status_to_send, 30), daemon=True).start()
                
                # Background Persistence (Every ~10 seconds)
                if int(now) % 10 == 0:
                    self.save_local_stats()

                time.sleep(0.5) 
                
            except Exception as e:
                print(f"THREAD CRASH: {e}")
                time.sleep(1)

    def start_tracking(self, punch_in_time_str=None):
        """Starts the LOCAL activity tracking."""
        # AUTO-VISIBILITY: If already active, still ensure visibility (e.g. from Smart Resume)
        if self.tracking_active:
             if not self.is_compact:
                 self.toggle_compact_mode()
             self.deiconify()
             self.attributes('-topmost', True)
             return

        self.lbl_status.configure(text="PUNCHED IN (Active)", text_color="green")
        self.log_msg(f"System: HRMS Punch-In detected. Starting tracking.")
        
        if punch_in_time_str:
            self.log_msg(f"System: HRMS Punch-In Time: {punch_in_time_str}")
            self.sync_timers_with_punch_in(punch_in_time_str)
            self.lbl_punch_time.configure(text=f"Clocked In at: {punch_in_time_str}")

        self.tracking_active = True
        self.tracker.start()
        self.show_notification("HRMS EVENT: PUNCH IN DETECTED")
        self.btn_start.configure(fg_color="#006400")

        # AUTO-VISIBILITY: Switch to Compact Mode and Show
        self.after(0, self.deiconify)
        if not self.is_compact:
            self.after(0, self.toggle_compact_mode)
        # Keep it topmost to be "Visually Accessible" per requirement
        self.after(100, lambda: self.attributes('-topmost', True))

    def stop_tracking(self, reason="Manual"):
        """Stops the LOCAL activity tracking."""
        if not self.tracking_active:
             return

        self.log_msg(f"System: Tracking Stopped ({reason}).")
        self.tracking_active = False
        self.tracker.stop()
        self.lbl_status.configure(text="OFF THE CLOCK", text_color="gray")
        self.btn_start.configure(fg_color="#1E1E1E")
        self.btn_stop.configure(fg_color="#1E1E1E")
        self.save_local_stats()
        self.show_notification(f"HRMS EVENT: STOPPED ({reason})")
        
        # UX: Disable "Always on Top" when stopped so it doesn't block user
        self.attributes('-topmost', False)

        # ACTION: Generate Report if Punched Out
        if reason == "Punched Out":
            self.generate_report()

    def load_local_stats(self):
        """Loads today's stats from JSON to preserve analytics."""
        try:
            import json
            import os
            import datetime
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            user_id = self.get_current_user_identifier()
            filename = f"daily_stats_{user_id}.json"
            file_path = self.get_app_path(filename)
            
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
                if data.get("date") == today_str:
                    self.total_work_seconds = data.get("work", 0)
                    self.total_idle_seconds = data.get("idle", 0)
                    self.hourly_stats = data.get("hourly", {})
                else:
                    # New day, start from 0
                    self.total_work_seconds = 0
                    self.total_idle_seconds = 0
                    self.hourly_stats = {}
            else:
                # No existing file, start from 0
                self.total_work_seconds = 0
                self.total_idle_seconds = 0
                self.hourly_stats = {}
        except:
            pass

    def save_local_stats(self):
        """Saves current stats to JSON."""
        try:
            import json
            import datetime
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            user_id = self.get_current_user_identifier()
            filename = f"daily_stats_{user_id}.json"
            file_path = self.get_app_path(filename)
            
            data = {
                "date": today_str,
                "work": self.total_work_seconds,
                "idle": self.total_idle_seconds,
                "hourly": self.hourly_stats
            }
            with open(file_path, "w") as f:
                json.dump(data, f)
        except:
            pass

    def show_notification(self, message):
        """Displays a non-blocking toast notification."""
        try:
            toast = ctk.CTkToplevel(self)
            toast.geometry("300x80")
            toast.title("")
            
            # Remove title bar (Frameless)
            toast.overrideredirect(True)
            toast.attributes('-topmost', True)
            
            # Position: Center of parent or Bottom Right?
            # Let's try bottom right of screen for "Notification" feel
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = screen_w - 320
            y = screen_h - 150
            toast.geometry(f"+{x}+{y}")
            
            # Content
            # Background frame
            bg = ctk.CTkFrame(toast, fg_color="#333333", border_width=2, border_color="#00FF00")
            bg.pack(fill="both", expand=True)
            
            label = ctk.CTkLabel(bg, text=message, font=("Arial", 14, "bold"), text_color="white")
            label.pack(expand=True, fill="both", padx=10, pady=10)
            
            # Auto close after 3 seconds
            toast.after(3000, toast.destroy)
            
            # Force update to show immediately
            toast.update()
        except:
            print("Notification Failed")


    def generate_report(self):
        """Generates a PDF report with charts and stats."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            import io
            from matplotlib.figure import Figure # Lazy Import

            # 1. Create Data
            today_str = datetime.date.today().strftime("%d-%b-%Y")
            user_id = self.api.employee_id if hasattr(self.api, 'employee_id') else "Unknown"
            role = self.api.course_role if hasattr(self.api, 'course_role') else "Employee"
            
            # CUMULATIVE CALCULATION: Sum up hourly stats to get the true daily total
            # This ensures that even if 'total_work_seconds' was reset for a new session,
            # the report includes ALL work done today.
            report_work_seconds = sum(d.get("work", 0) for d in self.hourly_stats.values())
            report_idle_seconds = sum(d.get("idle", 0) for d in self.hourly_stats.values())
            
            # Fallback: If hourly stats are empty (e.g. very short session < 1 min?), use current timers
            if report_work_seconds == 0 and report_idle_seconds == 0:
                report_work_seconds = self.total_work_seconds
                report_idle_seconds = self.total_idle_seconds

            work_formatted = self.format_time(report_work_seconds)
            idle_formatted = self.format_time(report_idle_seconds)
            
            total_sec = report_work_seconds + report_idle_seconds
            work_pct = (report_work_seconds / total_sec * 100) if total_sec > 0 else 0
            idle_pct = (report_idle_seconds / total_sec * 100) if total_sec > 0 else 0

            # 2. Setup Filename
            home_dir = os.path.expanduser("~")
            save_dir = os.path.join(home_dir, "Downloads")
            # Add Timestamp to avoid "Permission Denied" if file is open
            timestamp = datetime.datetime.now().strftime("%H-%M-%S")
            filename = os.path.join(save_dir, f"WorkResult_{user_id}_{today_str}_{timestamp}.pdf")
            
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter

            # 3. Draw Header
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 40, "Daily Activity Report")
            
            c.setFont("Helvetica", 10)
            c.setFillColor("gray")
            c.drawString(50, height - 60, f"Date: {today_str}")
            
            c.setLineWidth(1)
            c.setStrokeColor("gray")
            c.line(50, height - 70, width - 50, height - 70)

            # 4. User Info (Compressed)
            c.setFillColor("black")
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 100, "Employee Details:")
            
            c.setFont("Helvetica", 10)
            c.drawString(70, height - 120, f"ID: {user_id}   |   Role: {role}")
            c.drawString(70, height - 135, f"Generated At: {datetime.datetime.now().strftime('%H:%M:%S')}")

            # 5. Statistics Box (Compressed)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 165, "Time Summary:")
            
            # Draw Box
            box_top = height - 180
            c.rect(50, box_top - 50, 400, 50, fill=0)
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(70, box_top - 20, "WORK TIME")
            c.drawString(250, box_top - 20, "IDLE TIME")
            
            c.setFont("Helvetica", 12)
            c.setFillColor("#008000") # Green
            c.drawString(70, box_top - 40, work_formatted)
            
            c.setFillColor("#FFA500") # Orange
            c.drawString(250, box_top - 40, idle_formatted)
            
            c.setFillColor("black")

            # 7. Hourly Timeline Table (Moved Up)
            c.setFont("Helvetica-Bold", 12)
            timeline_start_y = height - 260
            c.drawString(50, timeline_start_y, "Hourly Timeline:")
            
            # Table Header
            c.setFont("Helvetica-Bold", 9)
            y_pos = timeline_start_y - 20
            c.drawString(70, y_pos, "Time Slot")
            c.drawString(200, y_pos, "Work Time")
            c.drawString(350, y_pos, "Idle Time")
            
            c.setLineWidth(0.5)
            c.line(50, y_pos - 5, 500, y_pos - 5)
            y_pos -= 20
            
            # Iterate through hours (sorted)
            c.setFont("Helvetica", 9)
            sorted_hours = sorted(self.hourly_stats.keys())
            
            # Layout Calculation: Chart uses bottom 250px. Safety line at y=300.
            chart_height = 200
            chart_y_pos = 80
            safety_margin = chart_y_pos + chart_height + 20 # ~300
            
            for h in sorted_hours:
                stats = self.hourly_stats[h]
                w_sec = stats.get("work", 0)
                i_sec = stats.get("idle", 0)
                
                time_slot = f"{h}:00 - {int(h)+1:02d}:00"
                work_t = self.format_time(w_sec)
                idle_t = self.format_time(i_sec)
                
                c.drawString(70, y_pos, time_slot)
                c.setFillColor("green")
                c.drawString(200, y_pos, work_t)
                c.setFillColor("orange")
                c.drawString(350, y_pos, idle_t)
                c.setFillColor("black")
                y_pos -= 15
                
                # Page Break if we hit the Chart area
                if y_pos < safety_margin: 
                    c.showPage()
                    y_pos = height - 50

            # 6. Chart (Trick: Save Matplotlib figure to BytesIO buffer)
            buf = io.BytesIO()
            # Reuse existing figure to save resources, but we need to ensure it's not transparent for PDF maybe
            # Create a dedicated figure for report to control styling purely for PDF
            fig = Figure(figsize=(6, 3), dpi=100) # Flatter chart
            ax = fig.add_subplot(111)
            
            labels = [f'Working ({work_pct:.1f}%)', f'Idle ({idle_pct:.1f}%)']
            sizes = [max(1, report_work_seconds), max(0, report_idle_seconds)]
            colors = ['#2CC985', '#FFB347']
            
            if report_work_seconds == 0 and report_idle_seconds == 0:
                sizes = [1]
                labels = ["No Data"]
                colors = ["#CCCCCC"]
            
            ax.pie(sizes, labels=labels, autopct=None, startangle=90, colors=colors)
            ax.set_title("Activity Distribution")
            
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Draw Image on PDF (Anchored to Bottom)
            c.drawImage(ImageReader(buf), 50, chart_y_pos, width=400, height=chart_height)
            
            # 8. Footer
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColor("gray")
            c.drawString(50, 40, "Generated by Automated Time Tracking System")
            
            c.save()
            buf.close()
            
            self.show_notification(f"Report Saved to Downloads!")
            self.log_msg(f"System: Report generated: {filename}")
            
            # Open the folder/file automatically for convenience
            try:
                os.startfile(filename)
            except:
                pass
                
        except Exception as e:
            print(f"Report Generation Failed: {e}")
            self.log_msg("Error generating report. Check console.")


if __name__ == "__main__":
    try:
        app = TimeTrackerApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[System] Application stopped by user.")
    except Exception as e:
        print(f"\n[System] Critical Error: {e}")
