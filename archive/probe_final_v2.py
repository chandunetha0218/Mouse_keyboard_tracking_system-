import requests
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MTQ3MWQwYmFjNzljNGZmYjMxN2VkZSIsInJvbGUiOiJlbXBsb3llZSIsImlhdCI6MTc3MDAxNjU3MCwiZXhwIjoxNzc3NzkyNTcwfQ.jErMkPAwCc7ExzA4vPqCC8m3vpV3cNetygRXRcMhKTs"
BASE_URL = "https://hrms-ask-1.onrender.com"
headers = {"Authorization": f"Bearer {TOKEN}"}

endpoints = [
    "/api/employee/status",
    "/api/user/status",
    "/api/me/status",
    "/api/attendance/my-last",
    "/api/attendance/last-punch",
    "/api/attendance/today-status",
    "/api/employee/attendance/today",
    "/api/user/attendance",
    "/api/profile/status",
    "/api/auth/me"
]

print("--- FINAL PROBE ---")
for ep in endpoints:
    print(f"GET {ep} ...", end=" ")
    try:
        resp = requests.get(f"{BASE_URL}{ep}", headers=headers, timeout=5)
        print(f"[{resp.status_code}]")
        if resp.status_code == 200:
            print(f"BODY: {resp.text[:200]}")
    except Exception as e:
        print(f"Err: {e}")
