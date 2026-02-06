
import unittest
from unittest.mock import MagicMock
import datetime

# Mock customtkinter to avoid GUI errors
import sys
from unittest.mock import MagicMock
sys.modules['customtkinter'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.backends.backend_tkagg'] = MagicMock()
sys.modules['matplotlib.figure'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['tkinter'] = MagicMock()

# Now import the class to test
# We need to bypass the actual import of main because it runs code at module level sometimes
# But looking at main.py, it imports ctk at top. We mocked it.

# We also need to mock ActivityTracker and ApiClient if they are imported
sys.modules['tracker'] = MagicMock()
sys.modules['api_client'] = MagicMock()

from main import TimeTrackerApp

class TestApp(TimeTrackerApp):
    def __init__(self):
        # Completely skip super().__init__ to avoid any GUI creation
        self.tracking_active = True
        self.total_work_seconds = 100 # Initial value
        self.is_punched_in = False
        self.api = MagicMock()
        self.sync_timers_with_punch_in = MagicMock()
        self.start_tracking = MagicMock()
        # Mock other needed attribs
        self.lbl_status = MagicMock()

    # Override log_msg and show_notification to avoid side effects
    def log_msg(self, msg): pass
    def show_notification(self, msg): pass

class TestSync(unittest.TestCase):
    def test_sync_uses_server_time(self):
        app = TestApp()
        # Simulate active punch-in
        # server_work_seconds = 5000
        app.process_sync_data("10:00", None, datetime.date.today().strftime("%Y-%m-%d"), server_work_seconds=5000)
        
        # Verify it updated to 5000
        self.assertEqual(app.total_work_seconds, 5000)
        # Verify it DID NOT call the fallback local calc
        app.sync_timers_with_punch_in.assert_not_called()
        print("Test 1 Passed: Server time used.")

    def test_sync_fallback_if_no_server_time(self):
        app = TestApp()
        # Simulate active punch-in, but server time is None/0
        app.process_sync_data("10:00", None, datetime.date.today().strftime("%Y-%m-%d"), server_work_seconds=0)
        
        # Verify fallback was called
        app.sync_timers_with_punch_in.assert_called_with("10:00")
        print("Test 2 Passed: Fallback to local used.")

if __name__ == '__main__':
    unittest.main()
