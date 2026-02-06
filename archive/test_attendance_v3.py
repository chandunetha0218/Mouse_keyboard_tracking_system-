import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
MONGO_ID = "691471d0bac79c4ffb317ede"

headers = {"Authorization": f"Bearer {TOKEN}"}

endpoints = [
    f"/api/attendance/employee/{MONGO_ID}",
    f"/api/attendance/user/{MONGO_ID}",
    f"/api/attendance/{MONGO_ID}",
    f"/api/employee/{MONGO_ID}",
    "/api/holidays"
]

print("--- PROBE V3 ---")
for path in endpoints:
    url = BASE_URL + path
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"GET {path} -> {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS!")
            try:
                print(resp.json())
            except:
                pass
    except Exception as e:
        print(f"Err {path}: {e}")
