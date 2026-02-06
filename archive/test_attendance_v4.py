import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
ID = "456" # User's Readable ID
MONGO_ID = "691471d0bac79c4ffb317ede"

headers = {"Authorization": f"Bearer {TOKEN}"}

print("--- PROBE V4 ---")
url = f"{BASE_URL}/api/attendance/all"

payloads = [
    {"employeeId": ID},
    {"employeeId": MONGO_ID},
    {"userId": MONGO_ID},
    {"_id": MONGO_ID},
    {"code": ID}
]

for p in payloads:
    print(f"POST {url} with {p}")
    try:
        resp = requests.post(url, headers=headers, json=p, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS!")
            try:
                print(resp.json())
            except:
                pass
    except Exception as e:
        print(f"Err: {e}")
