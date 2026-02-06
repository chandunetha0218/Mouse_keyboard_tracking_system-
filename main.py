import customtkinter as ctk
import threading
import time
import tkinter
import os
import json
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from tracker import ActivityTracker
from api_client import ApiClient
import pystray
from PIL import Image, ImageDraw

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TimeTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Activity Tracker v2.2")
        self.title("Activity Tracker v2.2")
        self.geometry("600x800") # Optimized size
        
        # State Variables
        self.total_work_seconds = 0
        self.total_idle_seconds = 0 # Accumulate idle time
        self.hourly_stats = {} # Format: {"09": {"work": 0, "idle": 0}, ...}
        self.is_punched_in = False
        self.target_seconds = 8 * 3600 # 8 Hours
        self.current_state = "WAITING"
        
        # Logic Components
        self.tracker = ActivityTracker(idle_threshold_seconds=10) # 10 Seconds per User Request
        self.api = ApiClient("https://hrms-420.netlify.app/.netlify/functions/api") # Prod URL
        self.tracking_active = False
        self.app_running = True # Control flag for background threads
        self.last_sync_time = time.time() # For high-precision deltas
        self.current_date = datetime.date.today().strftime("%Y-%m-%d")
        self.last_processed_punch_in = None # To track unique sessions
        
        # Office Hours Configuration (24h format)
        self.OFFICE_START_HOUR = 10 # 10:00 AM
        self.OFFICE_END_HOUR = 18   # Official: 6:00 PM

        # GUI Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Views
        self.login_view = self.create_login_view()
        self.dashboard_view = self.create_dashboard_view()
        self.compact_view = self.create_compact_view()

        # PROTOCOLS
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Track View State
        self.is_compact = False

        # Show Login Screen Immediately (Instant Startup)
        self.show_login()
        
        # Start Auto-Login in Background
        threading.Thread(target=self.handle_auto_login, daemon=True).start()
             
        # Load Persistence
        self.load_local_stats()

        # Start UI Update Loop (Main Thread)
        self.update_ui_loop()
        
        # System Tray Component
        self.tray_icon = None
        self.create_tray_icon()

    def is_within_working_hours(self):
        """Checks if tracking is allowed (10 AM - 6 PM)."""
        now_hour = datetime.datetime.now().hour
        # 10 means 10:00 to 10:59 ... 17 means 17:00 to 17:59. 
        # So we want >= 10 and < 18 (which is 6 PM)
        is_time = self.OFFICE_START_HOUR <= now_hour < self.OFFICE_END_HOUR
        
        if not is_time:
             # Just for debug/status updates
             pass
             
        return is_time

    def get_current_user_identifier(self):
        """Get a safe filename-friendly identifier for the current user."""
        if hasattr(self.api, 'employee_id') and self.api.employee_id:
            return str(self.api.employee_id).replace(" ", "_")
        return "default"

    def handle_auto_login(self):
        """Worker thread to handle auto-login without blocking startup."""
        if not os.path.exists("session.json"):
            return

        try:
            with open("session.json", "r") as f:
                data = json.load(f)
                user = data.get("username")
                pwd = data.get("password")
            
            if user and pwd:
                # Show subtle status on login screen
                self.after(0, lambda: self.lbl_error.configure(text="Auto-logging in...", text_color="orange"))
                
                self.api = ApiClient(base_url="https://hrms-420.netlify.app/.netlify/functions/api")
                success, msg = self.api.login(user, pwd)
                
                if success:
                    print("Auto-login successful")
                    self.after(0, self.show_dashboard)
                    self.after(0, self.load_local_stats)
                    self.after(0, lambda: self.lbl_error.configure(text=""))
                else:
                    self.after(0, lambda: self.lbl_error.configure(text="Session expired. Please login again.", text_color="grey"))
        except Exception as e:
            print(f"Auto-login failed: {e}")

    def save_session(self, username, password):
        """Save credentials locally."""
        with open("session.json", "w") as f:
            json.dump({"username": username, "password": password}, f)

    def logout(self):
        """Clear session and go back to login."""
        if os.path.exists("session.json"):
            os.remove("session.json")
        
        # Save current stats one last time before clearing
        self.save_local_stats()
        
        self.stop_tracking() # Ensure tracking stops if active
        self.app_running = False # Kill the background sync thread
        
        # Reset Timers for next login
        self.total_work_seconds = 0
        self.total_idle_seconds = 0
        
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
        self.dashboard_view.pack_forget()
        self.login_view.pack(fill="both", expand=True)

    def show_dashboard(self):
        self.login_view.pack_forget()
        self.dashboard_view.pack(fill="both", expand=True)
        
        # Display User Details
        if hasattr(self.api, 'employee_id') and hasattr(self.api, 'course_role'):
            self.lbl_user_info.configure(text=f"ID: {self.api.employee_id}  |  Role: {self.api.course_role}")
        
        self.lbl_status.configure(text="SYNCHRONIZING WITH HRMS...", text_color="orange")

        # Start the portal sync loop in background
        self.app_running = True
        
        # Start core threads
        threading.Thread(target=self.sync_with_portal, daemon=True).start()
        threading.Thread(target=self.server_polling_loop, daemon=True).start()
        threading.Thread(target=self.start_command_server, daemon=True).start()
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
                    
                    print(f"[SYNC] Received data for {attendance_date}: In={punch_in}, Out={punch_out}")
                    
                    # Update local bridge status
                    app_ref.after(0, lambda: app_ref.lbl_bridge.configure(text="Browser Sync: 🟢 Connected", text_color="green"))
                    
                    # Process sync on main thread
                    app_ref.after(0, lambda: app_ref.process_sync_data(punch_in, punch_out, attendance_date))
                    
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

    def process_sync_data(self, punch_in, punch_out, attendance_date, server_work_seconds=None, status=None):
        """Processes punch data received via bridge or polling."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # Validation: Only process if it's for today
        if attendance_date and str(attendance_date) != today_str:
            print(f"[SYNC] WARNING: Data Date '{attendance_date}' != System Date '{today_str}'. Ignoring.")
            return

        print(f"[SYNC] Received - In: '{punch_in}', Out: '{punch_out}', Status: '{status}'")

        # 1. HANDLE LOGOUT (Strict Stop)
        if status == "logged_out":
            if self.tracking_active:
                print("[SYNC] User Logged Out. Stopping Tracker.")
                self.stop_tracking("Logged Out")
            return

        # 2. HANDLE PUNCH DATA
        invalid_vals = [None, "null", "none", "", "-", "--", "--:--", "undefined", "false"]
        is_punched_in = punch_in not in invalid_vals
        is_punched_out = punch_out not in invalid_vals

        if is_punched_in:
            # Check if this is a "Fresh" punch (New Session)
            # Logic: If we are stopped, we only start if the punch is DIFFERENT from the last session's punch
            # OR if we haven't tracked anything yet.
            
            is_new_punch = (punch_in != self.last_processed_punch_in)
            
            if is_punched_out:
                # Case: Punched Out (Completed Session)
                # If we are somehow tracking, STOP.
                if self.tracking_active:
                     print(f"[SYNC] Punch Out Detected ({punch_out}). Stopping.")
                     self.stop_tracking("Punched Out")
                # Ensure we don't auto-start again for this specific punch-in time
                self.last_processed_punch_in = punch_in 

            elif not self.tracking_active:
                # Case: Punched In, Not Tracking.
                # Smart Resume Logic (User Request): "If user already punch in, it should run automatically"
                # We check if the punch-in is from Today. Since we only sync Today's data, this is implicit.
                # BUT we need to ensure we don't restart a session that was explicitly stopped by "Punch Out".
                # Here, we are in the "is_punched_in" and NOT "is_punched_out" block. So we are officially "Active".
                
                # We simply allow it to start if we are not tracking.
                print(f"[SYNC] Existing Active Punch detected ({punch_in}). Smart Resume: Starting Tracker.")
                self.start_tracking(punch_in_time_str=punch_in)
                self.last_processed_punch_in = punch_in
            
            else:
                # Case: Tracking Active. Sync timestamps.
                self.sync_timers_with_punch_in(punch_in)
                self.last_processed_punch_in = punch_in
        
        else:
            # Case: No Punch In.
            if self.tracking_active:
                 print(f"[SYNC] No active punch detected. Stopping.")
                 self.stop_tracking("No Data") 

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

    def handle_login(self):
        """Triggers the login process in a background thread to prevent UI freezing."""
        user = self.entry_user.get()
        password = self.entry_pass.get()
        
        if not user or not password:
            self.lbl_error.configure(text="Please enter both email and password")
            return

        # UI Feedback: Show loading state
        self.lbl_error.configure(text="Connecting to server... Please wait.", text_color="orange")
        # Find the login button and disable it
        for child in self.login_view.winfo_children():
            if isinstance(child, ctk.CTkButton) and child.cget("text") == "Login":
                child.configure(state="disabled", text="Logging in...")
                self.login_btn_ref = child

        # Start Login Thread
        threading.Thread(target=self._do_login_thread, args=(user, password), daemon=True).start()

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
            self.save_session(user, password)
            self.show_dashboard()
            self.load_local_stats()
            self.lbl_error.configure(text="") # Clear errors
        else:
            self.lbl_error.configure(text=msg, text_color="red")

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
        # Update Main Status Label safely
        if self.tracking_active:
             color = "green" if self.current_state == "WORKING" else "orange"
             self.lbl_status.configure(text=self.current_state, text_color=color)
             # Update Compact Status too
             self.lbl_compact_status.configure(text=self.current_state, text_color=color)
        else:
             self.lbl_status.configure(text="OFF THE CLOCK", text_color="grey")
             self.lbl_compact_status.configure(text="OFFLINE", text_color="grey")

        # Just show totals
        work_str = self.format_time(self.total_work_seconds)
        idle_str = self.format_time(self.total_idle_seconds)
        
        self.btn_start.configure(text=f"WORK TIME\n\n{work_str}")
        self.btn_stop.configure(text=f"IDLE TIME\n\n{idle_str}")
        
        # Update Compact Labels
        self.lbl_compact_work.configure(text=work_str)
        self.lbl_compact_idle.configure(text=f"Idle: {idle_str}")
        
        # Update progress
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
                self.log_msg(f"System: New day detected ({today_str}). Resetting.")
                self.save_local_stats()
                self.total_work_seconds = 0
                self.total_idle_seconds = 0
                self.current_date = today_str
                self.save_local_stats()
                self.after(0, self.update_chart)

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
        if self.tracking_active:
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

    def load_local_stats(self):
        """Loads today's stats from JSON to preserve analytics."""
        try:
            import json
            import os
            import datetime
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            user_id = self.get_current_user_identifier()
            filename = f"daily_stats_{user_id}.json"
            
            if os.path.exists(filename):
                with open(filename, "r") as f:
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
            
            data = {
                "date": today_str,
                "work": self.total_work_seconds,
                "idle": self.total_idle_seconds,
                "hourly": self.hourly_stats
            }
            with open(filename, "w") as f:
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

            # 1. Create Data
            today_str = datetime.date.today().strftime("%d-%b-%Y")
            user_id = self.api.employee_id if hasattr(self.api, 'employee_id') else "Unknown"
            role = self.api.course_role if hasattr(self.api, 'course_role') else "Employee"
            
            work_formatted = self.format_time(self.total_work_seconds)
            idle_formatted = self.format_time(self.total_idle_seconds)
            
            total_sec = self.total_work_seconds + self.total_idle_seconds
            work_pct = (self.total_work_seconds / total_sec * 100) if total_sec > 0 else 0
            idle_pct = (self.total_idle_seconds / total_sec * 100) if total_sec > 0 else 0

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
            sizes = [max(1, self.total_work_seconds), max(0, self.total_idle_seconds)]
            colors = ['#2CC985', '#FFB347']
            
            if self.total_work_seconds == 0 and self.total_idle_seconds == 0:
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
