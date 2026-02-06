import requests

url = "https://hrms-ask-1.onrender.com/api/auth/login"
print(f"Testing Connection to: {url}")

try:
    # Sending junk credentials. We expect 401 (Unauthorized) if server is UP.
    resp = requests.post(url, json={"email": "test@test.com", "password": "wrongpassword"}, timeout=10)
    
    print(f"Response Code: {resp.status_code}")
    
    if resp.status_code == 401:
        print("✅ SUCCESS: Server REJECTED invalid credentials. This means we ARE connected and talking to the backend!")
    elif resp.status_code == 200:
        print("✅ SUCCESS: Server accepted (Unexpected for fake data, but connected!)")
    elif resp.status_code == 404:
        print("❌ FAILURE: Endpoint not found (404).")
    else:
        print(f"⚠️ UNKNOWN: Server replied with {resp.status_code}")

except Exception as e:
    print(f"❌ FAILURE: Could not connect. Reason: {e}")
