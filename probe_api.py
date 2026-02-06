import requests

base = "https://hrms-420.netlify.app"
endpoints = [
    "/api/v1/auth/login",
    "/api/auth/login",
    "/api/login",
    "/auth/login",
    "/login",
    "/.netlify/functions/api/v1/auth/login",
    "/.netlify/functions/api",
    "/.netlify/functions/login",
    "/.netlify/functions/auth",
    "/users/login",
    "/api/users/login"
]

print(f"Scanning {base} for active endpoints...")

for ep in endpoints:
    url = base + ep
    try:
        # We use POST because login is usually POST
        resp = requests.post(url, json={"email": "test", "password": "test"}, timeout=2)
        print(f"[{resp.status_code}] {ep}")
    except Exception as e:
        print(f"[ERR] {ep}: {e}")
