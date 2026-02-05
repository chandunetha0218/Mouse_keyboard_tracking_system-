import requests
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
headers = {"Authorization": f"Bearer {TOKEN}"}

print("Testing GET /api/attendance")
try:
    resp = requests.get(f"{BASE_URL}/api/attendance", headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(resp.text[:500])
except Exception as e:
    print(f"Error: {e}")
