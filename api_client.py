import requests
import time

class ApiClient:
    def __init__(self, base_url):
        # Ensure the URL doesn't have a trailing slash
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.employee_id = None
        self.course_role = "Employee" # Default to prevent AttributeError

    def login(self, username, password):
        """
        Authenticate user. Tries local backend first, then Render fallback.
        """
        # URLs to try (Localhost first for dev)
        urls_to_try = ["http://localhost:5000", "https://hrms-ask-1.onrender.com"]
        
        last_error = ""

        for base_url in urls_to_try:
            try:
                print(f"[API] Attempting login at {base_url}...")
                payload = {"email": username, "password": password} 
                target_url = f"{base_url}/api/auth/login"
                
                # Shorter timeout for localhost, longer for Render
                timeout = 5 if "localhost" in base_url else 45
                resp = requests.post(target_url, json=payload, timeout=timeout)
                
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data.get('token')
                    user_data = data.get('data') or data.get('user', data)
                    
                    self.mongo_id = user_data.get('_id') or user_data.get('id')
                    self.user_name = user_data.get('name') or "Unknown"
                    self.employee_id = user_data.get('employeeId') or user_data.get('empId') or "UNKNOWN"
                    
                    # Store Role
                    exp_details = user_data.get('experienceDetails', [])
                    if isinstance(exp_details, list) and len(exp_details) > 0:
                        self.course_role = exp_details[0].get('role')
                    if not self.course_role:
                        self.course_role = user_data.get('role') or "Employee"

                    # Special case for user
                    if username == "oragantisagar719@gmail.com":
                        if "UNKNOWN" in str(self.employee_id): self.employee_id = "INT2607"

                    self.base_url = base_url
                    print(f"[API] Login Successful at {base_url}")
                    return True, "Login Successful"
                else:
                    last_error = f"Status {resp.status_code}"
                    print(f"[API] Login failed at {base_url}: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"[API] Error at {base_url}: {last_error}")
                continue
        
        return False, f"Login failed: {last_error}"

    def check_punch_status(self):
        """
        Derives status by checking the latest attendance record.
        """
        if not self.token or not hasattr(self, 'base_url'):
            return False, 0, None

        try:
            headers = {"Authorization": f"Bearer {self.token}", "Cache-Control": "no-cache"}
            url = f"{self.base_url}/api/attendance"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                records = data if isinstance(data, list) else (data.get('data') or data.get('attendance') or [])
                
                if not records:
                    return False, 0, None
                    
                last_record = records[-1]
                punch_in = last_record.get('punchIn') or last_record.get('loginTime')
                punch_out = last_record.get('punchOut') or last_record.get('logoutTime')
                
                raw_status = str(last_record.get('status', '')).upper()
                # Active if Punched In but not Punched Out
                is_active = (punch_in is not None and str(punch_in).lower() not in ["null", "none", "", "00:00"]) and \
                            (punch_out is None or str(punch_out).lower() in ["null", "none", "", "00:00"])
                
                punch_data = {
                    "punch_in": punch_in,
                    "punch_out": punch_out,
                    "date": last_record.get('date'),
                    "raw_status": raw_status
                }
                return is_active, 0, punch_data
            
            return None, 0, None
        except Exception as e:
            print(f"[API] Check Error: {e}")
            return None, 0, None

    def punch_in(self):
        """ Read-only mode: This app no longer supports punching in. """
        return False, "Manual Punching Disabled: Use the HRMS Portal."

    def punch_out(self):
        """ Read-only mode: This app no longer supports punching out. """
        return False, "Manual Punching Disabled: Use the HRMS Portal."
            
    def upload_activity_log(self, status, duration_seconds, idle_since=None):
        """Sends Live Telemetry to the Admin Dashboard."""
        if not self.token or not self.employee_id or not hasattr(self, 'base_url'):
            return

        try:
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            url = f"{self.base_url}/api/idletime/live-status"
            payload = {
                "employeeId": self.employee_id,
                "status": status,
                "duration_seconds": duration_seconds,
                "timestamp": time.time()
            }
            if idle_since:
                payload["idle_since"] = idle_since
            requests.post(url, json=payload, headers=headers, timeout=5)
        except:
            pass

    def save_idle_session(self, idle_start, idle_end, duration_seconds):
        """Uploads a completed idle session to the backend."""
        if not self.token or not self.employee_id or not hasattr(self, 'base_url'):
            return

        try:
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            url = f"{self.base_url}/api/idletime" 
            
            payload = {
                "employeeId": self.employee_id,
                "name": getattr(self, 'user_name', "Unknown"),
                "department": "Technical",
                "role": getattr(self, 'course_role', "Employee"),
                "date": idle_start.strftime("%Y-%m-%d"),
                "idleStart": idle_start.isoformat(),
                "idleEnd": idle_end.isoformat(),
                "idleDurationSeconds": int(duration_seconds)
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                print(f"[API] Idle Session Saved: {int(duration_seconds)}s")
            else:
                print(f"[API] Save Failed: {resp.status_code}")
        except Exception as e:
            print(f"[API] Save Error: {e}")
