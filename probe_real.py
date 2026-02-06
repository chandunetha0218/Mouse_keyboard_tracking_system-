import requests
import json
import datetime

def probe():
    login_url = "https://hrms-ask-1.onrender.com/api/auth/login"
    payload = {"email": "oragantisagar719@gmail.com", "password": "123456789"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=payload, timeout=20)
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    token = data.get('token')
    
    print(f"Auth Success. Token: {token[:10]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    attendance_url = "https://hrms-ask-1.onrender.com/api/attendance"
    
    print("Fetching attendance...")
    resp = requests.get(attendance_url, headers=headers, timeout=20)
    if resp.status_code != 200:
        print(f"Fetch failed: {resp.status_code}")
        return

    attendance_data = resp.json()
    records = []
    if isinstance(attendance_data, list):
        records = attendance_data
    elif isinstance(attendance_data, dict):
        records = attendance_data.get('data') or attendance_data.get('attendance') or []
        
    if not records:
        print("No records found.")
        return
        
    last = records[-1] if records else {}
    print("\n--- Records ---")
    print(f"Count: {len(records)}")
    
    # Try alternate endpoints with MONGO_ID
    target_endpoints = [
        f"/api/attendance/employee/{MONGO_ID}",
        f"/api/attendance/my-attendance",
        f"/api/attendance/user/{MONGO_ID}",
        f"/api/v1/attendance/employee/{MONGO_ID}"
    ]
    
    for tep in target_endpoints:
        turl = f"https://hrms-ask-1.onrender.com{tep}"
        tr = requests.get(turl, headers=headers)
        print(f"GET {tep} -> {tr.status_code}")
        if tr.status_code == 200:
            print(json.dumps(tr.json(), indent=2))
            break

if __name__ == "__main__":
    probe()
