import requests
import json
import datetime

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
ID = "INT2607"

headers = {"Authorization": f"Bearer {TOKEN}"}

today = datetime.date.today().isoformat()
# Try different query param styles
urls = [
    f"{BASE_URL}/api/attendance/by-range?startDate={today}&endDate={today}&employeeId={ID}",
    f"{BASE_URL}/api/attendance/by-range?from={today}&to={today}&employeeId={ID}",
    f"{BASE_URL}/api/attendance?date={today}&employeeId={ID}",
    f"{BASE_URL}/api/attendance/user/{ID}?date={today}"
]

print(f"--- PROBING LIST ENDPOINTS FOR {ID} ---")

for url in urls:
    print(f"GET {url} ...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"[{resp.status_code}]")
        if resp.status_code == 200:
             print(f"BODY: {resp.text[:500]}")
    except Exception as e:
        print(f"Err: {e}")
