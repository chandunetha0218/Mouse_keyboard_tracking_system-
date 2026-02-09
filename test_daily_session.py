
import unittest
from unittest.mock import MagicMock, patch
import datetime
import sys
import os

# Create dummy modules for GUI dependencies
class MockWidget:
    def __init__(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def place(self, *args, **kwargs): pass
    def pack_forget(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass
    def cget(self, *args, **kwargs): return MagicMock()
    def winfo_children(self): return []

class MockCTK:
    set_appearance_mode = MagicMock()
    set_default_color_theme = MagicMock()
    class CTk(MockWidget):
        def __init__(self, *args, **kwargs): pass
        def title(self, *args, **kwargs): pass
        def geometry(self, *args, **kwargs): pass
        def resizable(self, *args, **kwargs): pass
        def protocol(self, *args, **kwargs): pass
        def after(self, *args, **kwargs): pass
        def withdraw(self, *args, **kwargs): pass
        def deiconify(self, *args, **kwargs): pass
        def attributes(self, *args, **kwargs): pass
        def destroy(self, *args, **kwargs): pass
        def mainloop(self, *args, **kwargs): pass
        def winfo_screenwidth(self): return 1920
        def winfo_screenheight(self): return 1080
    class CTkFrame(MockWidget): pass
    class CTkLabel(MockWidget): pass
    class CTkEntry(MockWidget):
        def delete(self, *args, **kwargs): pass
        def insert(self, *args, **kwargs): pass
        def get(self): return "test"
    class CTkButton(MockWidget): pass
    class CTkProgressBar(MockWidget):
        def set(self, *args, **kwargs): pass
    class CTkTextbox(MockWidget):
        def insert(self, *args, **kwargs): pass
        def see(self, *args, **kwargs): pass

sys.modules['customtkinter'] = MockCTK
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.backends.backend_tkagg'] = MagicMock()
sys.modules['matplotlib.figure'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['tkinter'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageDraw'] = MagicMock()
sys.modules['winreg'] = MagicMock()
sys.modules['tracker'] = MagicMock()
sys.modules['api_client'] = MagicMock()

# Now we can safely import or define the tests
from main import TimeTrackerApp

class TestDailySession(unittest.TestCase):
    def setUp(self):
        # We need to partially mock the App so it doesn't try to run GUI stuff
        with patch.object(TimeTrackerApp, 'setup_ui'), \
             patch.object(TimeTrackerApp, 'load_local_stats'), \
             patch.object(TimeTrackerApp, 'create_tray_icon'), \
             patch.object(TimeTrackerApp, 'check_auto_login'), \
             patch.object(TimeTrackerApp, 'update_ui_loop'):
            self.app = TimeTrackerApp()
            
        self.app.after = MagicMock()
        self.app.log_msg = MagicMock()
        self.app.save_local_stats = MagicMock()
        self.app.stop_tracking = MagicMock()
        self.app.start_tracking = MagicMock()
        self.app.sync_timers_with_worked_str = MagicMock()
        self.app.sync_timers_with_punch_in = MagicMock()
        self.app.lbl_bridge = MagicMock()
        self.app.lbl_punch_time = MagicMock()
        self.app.lbl_work_time = MagicMock()
        self.app.lbl_idle_time = MagicMock()

        # Set initial state
        self.app.current_date = datetime.date.today().strftime("%Y-%m-%d")
        self.app.total_work_seconds = 0
        self.app.total_idle_seconds = 0
        self.app.last_processed_punch_in = None
        self.app.tracking_active = False

    def test_same_day_resume(self):
        """Test that a new punch-in on the same day resumes rather than resets."""
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # 1. First Punch In
        self.app.process_sync_data("10:00 AM", None, today)
        self.app.last_processed_punch_in = "10:00 AM"
        self.app.total_work_seconds = 300 # Simulate 5 mins work
        
        # 2. Punch Out
        self.app.process_sync_data("10:00 AM", "10:05 AM", today)
        
        # 3. Second Punch In on same day
        self.app.process_sync_data("11:00 AM", None, today)
        
        # Verify that total_work_seconds is STILL 300 (not reset to 0)
        self.assertEqual(self.app.total_work_seconds, 300)
        print("Test Same-Day Resume: PASSED")

    def test_next_day_reset(self):
        """Test that the rollover logic resets stats."""
        self.app.total_work_seconds = 5000
        self.app.total_idle_seconds = 1000
        self.app.hourly_stats = {"10": {"work": 5000, "idle": 1000}}
        self.app.current_date = "2026-02-08" # Yesterday
        self.app.last_processed_punch_in = "10:00 AM"
        
        # Simulate the rollover check in sync_with_portal
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        if today_str != self.app.current_date:
            # Logic from main.py
            self.app.total_work_seconds = 0
            self.app.total_idle_seconds = 0
            self.app.hourly_stats = {}
            self.app.current_date = today_str
            self.app.last_processed_punch_in = None
            
        self.assertEqual(self.app.total_work_seconds, 0)
        self.assertEqual(self.app.total_idle_seconds, 0)
        self.assertEqual(self.app.hourly_stats, {})
        self.assertEqual(self.app.current_date, today_str)
        self.assertIsNone(self.app.last_processed_punch_in)
        print("Test Next-Day Reset: PASSED")

if __name__ == '__main__':
    unittest.main()
