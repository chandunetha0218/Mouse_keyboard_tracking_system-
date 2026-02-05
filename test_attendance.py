# Updated test script with dynamic login
import requests
import json

BASE_URL = "https://hrms-ask-1.onrender.com"
EMAIL = "oragantisagar719@gmail.com"
PASSWORD = "123456789"

print("Logging in to get fresh token...")
login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code}")
    exit()

TOKEN = login_resp.json().get('token')
user_data = login_resp.json().get('data', {})
MONGO_ID = user_data.get('_id')
ID = user_data.get('employeeId') or "INT2607"

headers = {"Authorization": f"Bearer {TOKEN}"}
print(f"Token obtained: {TOKEN[:10]}...")
print(f"IDs: Mongo={MONGO_ID}, EmpID={ID}")

endpoints = [
    "/api/attendance",
    "/api/attendance/all",
    "/api/attendance/my-attendance",
    "/api/attendance/current",
    "/api/attendance/status",
    "/api/attendance/check-status",
    f"/api/employees/{ID}/attendance",
    f"/api/attendance/employee/{ID}",
    f"/api/attendance/{MONGO_ID}",
    "/api/user/attendance"
]

results = []

print(f"Testing {len(endpoints)} endpoints...")

def try_url(path):
    url = BASE_URL + path
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"GET {path} -> {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                with open("found_attendance.json", "w") as f:
                    json.dump(data, f, indent=4, default=str)
                print(f"SUCCESS! Saved data from {path}")
                return True
            except:
                pass
    except Exception as e:
        print(f"Error {path}: {e}")
    return False

for path in endpoints:
    if try_url(path):
        break # Found it
