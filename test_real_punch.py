import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"

headers = {"Authorization": f"Bearer {TOKEN}"}

print("--- TESTING PUNCH API ---")

# 1. TRY GET (Maybe status check?)
url = f"{BASE_URL}/api/attendance/punch-in"
print(f"GET {url}")
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"GET Err: {e}")

# 2. TRY POST (Real Punch?)
# We send empty payload to see validation errors
print(f"\nPOST {url}")
try:
    resp = requests.post(url, headers=headers, json={}, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"POST Err: {e}")
