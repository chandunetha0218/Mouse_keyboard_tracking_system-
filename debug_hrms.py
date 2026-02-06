import requests
import json
import os

def debug_hrms():
    if not os.path.exists("session.json"):
        print("No session.json found. Please login via the main app first.")
        return

    with open("session.json", "r") as f:
        creds = json.load(f)
    
    username = creds.get("username")
    password = creds.get("password")
    
    print(f"Logging in as {username}...")
    
    url = "https://hrms-ask-1.onrender.com/api/auth/login"
    try:
        resp = requests.post(url, json={"email": username, "password": password}, timeout=30)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} - {resp.text}")
            return
            
        data = resp.json()
        token = data.get("token")
        print("Login successful. Token acquired.")
        
        # Fetch Attendance
        att_url = "https://hrms-ask-1.onrender.com/api/attendance"
        headers = {"Authorization": f"Bearer {token}", "Cache-Control": "no-cache"}
        
        print(f"Fetching {att_url}...")
        att_resp = requests.get(att_url, headers=headers, timeout=30)
        
        if att_resp.status_code == 200:
            att_data = att_resp.json()
            print("\n--- RAW ATTENDANCE DATA (LATEST RECORD) ---")
            
            records = []
            if isinstance(att_data, list):
                records = att_data
            elif isinstance(att_data, dict):
                records = att_data.get('data') or att_data.get('attendance') or []
            
            if records:
                print(json.dumps(records[-1], indent=4))
            else:
                print("No records found in response.")
                print("Full Response keys:", att_data.keys() if isinstance(att_data, dict) else "List")
        else:
            print(f"Attendance fetch failed: {att_resp.status_code} - {att_resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_hrms()
