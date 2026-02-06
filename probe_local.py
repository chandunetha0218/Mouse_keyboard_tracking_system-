import requests

# CLUE: Screenshot showed connection attempts to localhost:5000
bases = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8080"
]

endpoints = [
    "/api/v1/auth/login",
    "/api/auth/login",
    "/api/login",
    "/auth/login",
    "/login",
    "/users/login"
]

print(f"Scanning LOCALHOST for active API...")

found = False
for base in bases:
    for ep in endpoints:
        url = base + ep
        try:
            # Short timeout because localhost is fast
            resp = requests.post(url, json={"email": "test", "password": "test"}, timeout=0.5)
            print(f"[{resp.status_code}] {url}")
            if resp.status_code != 404 and resp.status_code != 500: # 401/400/200 are good
                print(f"!!! FOUND IT !!! -> {url}")
                found = True
        except:
            pass # Port closed or idle

if not found:
    print("Scan Complete. No local API found.")
