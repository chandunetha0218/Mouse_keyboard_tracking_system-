import requests
import json
import datetime

# Use the Token valid for user
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
ID = "INT2607"

headers = {"Authorization": f"Bearer {TOKEN}"}

endpoints = [
    "/api/attendance/current",
    "/api/attendance/status",
    "/api/attendance/today",
    "/api/attendance/check",
    "/api/attendance/last",
    "/api/attendance/latest",
    f"/api/employee/{ID}/attendance",
    f"/api/attendance/employee/{ID}",
    "/api/attendance/my-status",
    "/api/attendance/me"
]

print(f"--- PROBING STATUS ENDPOINTS FOR {ID} ---")

for ep in endpoints:
    url = f"{BASE_URL}{ep}"
    print(f"Testing {ep} ...", end=" ")
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"[{resp.status_code}]")
        if resp.status_code == 200:
            print(f"SUCCESS BODY: {resp.text[:200]}")
    except Exception as e:
        print(f"Err: {e}")
        
    # Ask Try POST for same?
    # Many status checks must not be POST.
