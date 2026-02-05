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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TimeTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Activity Tracker v2.2")
        self.geometry("600x700") # Increased size for chart
        
        # State Variables
        self.total_work_seconds = 0
        self.total_idle_seconds = 0 # Accumulate idle time
        self.is_punched_in = False
        self.target_seconds = 7 * 3600 # 7 Hours
        self.current_state = "WAITING"
        
        # Logic Components
        self.tracker = ActivityTracker(idle_threshold_seconds=10) # 10 Seconds per User Request
        self.api = ApiClient("https://hrms-420.netlify.app/.netlify/functions/api") # Prod URL
        self.tracking_active = False
        self.app_running = True # Control flag for background threads
        self.last_sync_time = time.time() # For high-precision deltas
        self.current_date = datetime.date.today().strftime("%Y-%m-%d")
        
        # Office Hours Configuration (24h format)
        self.OFFICE_START_HOUR = 10 # 10:00 AM
        self.OFFICE_END_HOUR = 18   # Official: 6:00 PM

        # GUI Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Views
        self.login_view = self.create_login_view()
        self.dashboard_view = self.create_dashboard_view()

        # PROTOCOLS
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Show Login Screen Immediately (Instant Startup)
        self.show_login()
        
        # Start Auto-Login in Background
        threading.Thread(target=self.handle_auto_login, daemon=True).start()
             
        # Load Persistence
        self.load_local_stats()

        # Start UI Update Loop (Main Thread)
        self.update_ui_loop()

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

    def on_closing(self):
        if self.tracking_active:
             self.destroy() # Allow closing, stop_tracking will be called during destruction/sync loop halt
        else:
            self.destroy()

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
        
        # 1. Status Header
        self.lbl_status = ctk.CTkLabel(frame, text="WAITING FOR PUNCH IN", font=("Roboto", 24, "bold"), text_color="grey")
        self.lbl_status.pack(pady=(10, 5))

        # USER INFO LABEL (ID & ROLE)
        self.lbl_user_info = ctk.CTkLabel(frame, text="", font=("Roboto", 14), text_color="silver")
        self.lbl_user_info.pack(pady=(0, 5))

        # CONNECTIVITY STATUS
        self.lbl_bridge = ctk.CTkLabel(frame, text="Browser Sync: 🔴 Waiting...", font=("Roboto", 12), text_color="#A0A0A0")
        self.lbl_bridge.pack(pady=(0, 10))

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
        self.lbl_target = ctk.CTkLabel(frame, text="Target: 7 Hours")
        self.lbl_target.pack(pady=(10, 0))
        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(5, 20))

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
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args): pass

        try:
            server = HTTPServer(('localhost', 12345), CommandHandler)
            server.serve_forever()
        except:
            print("Could not start Command Server")

    def process_sync_data(self, punch_in, punch_out, attendance_date, server_work_seconds=None):
        """Processes punch data received via bridge or polling."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # Validation: Only process if it's for today
        if attendance_date and str(attendance_date) != today_str:
            print(f"[SYNC] WARNING: Data Date '{attendance_date}' != System Date '{today_str}'. Ignoring?")
            # Relaxed check: If it's a valid punch-in and we are desperate, maybe we allow it?
            # For now, strict but voiced.
            return

        invalid_vals = [None, "null", "none", "", "-", "undefined", "false"]
        is_punched_in = punch_in not in invalid_vals
        is_punched_out = punch_out not in invalid_vals

        print(f"[SYNC] Received - In: '{punch_in}', Out: '{punch_out}', Date: '{attendance_date}'")

        if is_punched_in and not is_punched_out:
            # Update Total Work Seconds from Server if available
            if server_work_seconds is not None and float(server_work_seconds) > 0:
                print(f"[SYNC] Using Server Work Time: {server_work_seconds}s")
                self.total_work_seconds = float(server_work_seconds)
            
            # Auto-start logic
            if not self.tracking_active:
                print(f"[SYNC] Auto-starting tracking based on punch-in: {punch_in}")
                self.start_tracking(punch_in_time_str=punch_in)
            else:
                # If already tracking, ensure time is synced with punch-in (FALLBACK Only)
                if not server_work_seconds:
                    self.sync_timers_with_punch_in(punch_in)
        elif is_punched_out:
            if self.tracking_active:
                print(f"[SYNC] Auto-stopping tracking based on punch-out: {punch_out}")
                self.stop_tracking()
        else:
            # If no punch-in is detected but we are tracking, maybe we should stop?
            # User says candidate is punched in, so if we aren't seeing it, it might be a script issue.
            print(f"[SYNC] No active punch detected. In='{punch_in}', Out='{punch_out}'")
            if self.tracking_active:
                 # Be cautious about auto-stopping if we could be missing a selector
                 pass 

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
            if self.total_work_seconds == 0 or abs(calculated_work - self.total_work_seconds) > 10:
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
        else:
             self.lbl_status.configure(text="OFF THE CLOCK", text_color="grey")

        # Just show totals
        work_str = self.format_time(self.total_work_seconds)
        idle_str = self.format_time(self.total_idle_seconds)
        
        self.btn_start.configure(text=f"WORK TIME\n\n{work_str}")
        self.btn_stop.configure(text=f"IDLE TIME\n\n{idle_str}")
        
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
                        if state == "WORKING":
                            self.total_work_seconds += delta
                        else:
                            self.total_idle_seconds += delta
                    
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

        self.tracking_active = True
        self.tracker.start()
        self.show_notification("HRMS EVENT: PUNCH IN DETECTED")
        self.btn_start.configure(fg_color="#006400")

    def stop_tracking(self):
        """Stops the LOCAL activity tracking."""
        if not self.tracking_active:
             return

        self.log_msg("System: HRMS Punch-Out detected. Stopping tracking.")
        self.tracking_active = False
        self.tracker.stop()
        self.lbl_status.configure(text="OFF THE CLOCK", text_color="gray")
        self.btn_start.configure(fg_color="#1E1E1E")
        self.btn_stop.configure(fg_color="#1E1E1E")
        self.save_local_stats()
        self.show_notification("HRMS EVENT: PUNCH OUT DETECTED")

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
                else:
                    # New day, start from 0
                    self.total_work_seconds = 0
                    self.total_idle_seconds = 0
            else:
                # No existing file, start from 0
                self.total_work_seconds = 0
                self.total_idle_seconds = 0
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
                "idle": self.total_idle_seconds
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


if __name__ == "__main__":
    app = TimeTrackerApp()
    app.mainloop()
