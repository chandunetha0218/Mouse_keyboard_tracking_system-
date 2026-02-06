import requests
import json
import datetime

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
ID = "456"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Dates
today = datetime.date.today().isoformat() # YYYY-MM-DD
start = today
end = today

endpoints = [
    f"/api/attendance/by-range?startDate={start}&endDate={end}",
    f"/api/attendance?startDate={start}&endDate={end}",
    f"/api/attendance/my-attendance?startDate={start}&endDate={end}",
    f"/api/attendance?date={today}"
]

print("--- PROBE V5 (Ranges) ---")
for path in endpoints:
    url = BASE_URL + path
    print(f"GET {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS! Data:")
            try:
                print(resp.json())
            except:
                pass
    except Exception as e:
        print(f"Err: {e}")
