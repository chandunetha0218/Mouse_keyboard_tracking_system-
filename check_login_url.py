import requests
import json

URLS = [
    "https://hrms-ask-1.onrender.com/api/auth/login",
    "https://hrms-420.netlify.app/.netlify/functions/api/auth/login"
]

email = "oragantisagar719@gmail.com"
password = "dummy_password" # Just checking if endpoint exists (401 vs 404)

print("--- TESTING LOGIN ENDPOINTS ---")
for url in URLS:
    print(f"POST {url} ...", end=" ")
    try:
        resp = requests.post(url, json={"email": email, "password": password}, timeout=10)
        print(f"[{resp.status_code}]")
    except Exception as e:
        print(f"Error: {e}")
