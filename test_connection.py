from api_client import ApiClient

def test_connection():
    # Use the hardcoded URL logic
    url = "https://hrms-420.netlify.app/"
    print(f"Testing connection to: {url}")
    
    client = ApiClient(url)
    
    # Try a fake login (since we are simulating) to see if it crashes
    try:
        success, msg = client.login("test_user", "test_pass")
        print(f"Login Function Result: {success} - {msg}")
        
        status = client.check_punch_status()
        print(f"Check Punch Status Result: {status}")
        
        print("TEST PASSED: Connection logic is sound.")
    except Exception as e:
        print(f"TEST FAILED: {e}")

if __name__ == "__main__":
    test_connection()
