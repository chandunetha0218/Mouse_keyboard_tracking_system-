import requests
import re

url = "https://hrms-420.netlify.app/assets/index-Dy-qz3hk.js"
print(f"Downloading {url}...")

try:
    resp = requests.get(url)
    content = resp.text
    print(f"Downloaded {len(content)} bytes.")
    
    with open("site_bundle.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved to site_bundle.js")

    # Search for Attendance specific paths
    print("--- Searching for ATTENDANCE Paths ---")
    # emerging pattern: /api/attendance/...
    attendance_urls = re.findall(r'"/api/attendance/[^"]+"', content)
    for p in attendance_urls:
        print(f"FOUND ATTENDANCE: {p}")
        
    # Search for generic API string formations
    print("--- Searching for any API usage ---")
    # Finds "get('/api/...')" or similar
    api_calls = re.findall(r"(get|post|put|patch)\(['\"]/api/[^'\"]+['\"]", content)
    for call in api_calls[:20]:
        print(f"FOUND API CALL: {call}")

except Exception as e:
    print(f"Error: {e}")
