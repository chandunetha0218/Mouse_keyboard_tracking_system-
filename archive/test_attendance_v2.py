import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
ID = "456"
MONGO_ID = "691471d0bac79c4ffb317ede"

headers = {"Authorization": f"Bearer {TOKEN}"}

print("--- PROBE V2 ---")

# 1. Check Profile
print("Checking Profile...")
url = f"{BASE_URL}/api/employees/{MONGO_ID}"
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"GET Profile: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Profile Keys: {list(data.keys())}")
        if 'attendance' in data:
            print("FOUND ATTENDANCE IN PROFILE!")
            with open("found_attendance.json", "w") as f:
                json.dump(data['attendance'], f, default=str)
except Exception as e:
    print(f"Profile Error: {e}")

# 2. Check POST /attendance/all
print("Checking POST /attendance/all...")
url = f"{BASE_URL}/api/attendance/all"
try:
    # Try empty body
    resp = requests.post(url, headers=headers, json={}, timeout=10)
    print(f"POST all (empty): {resp.status_code}")
    
    # Try with ID
    resp = requests.post(url, headers=headers, json={"employeeId": MONGO_ID}, timeout=10)
    print(f"POST all (ID): {resp.status_code}")
except Exception as e:
    print(f"POST Error: {e}")

# 3. Check POST /attendance (Get my attendance)
print("Checking POST /attendance/getmyattendance...")
url = f"{BASE_URL}/api/attendance/getmyattendance" # Guess
resp = requests.post(url, headers=headers, json={}, timeout=5)
print(f"POST getmyattendance: {resp.status_code}")
