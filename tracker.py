import time
import threading
from pynput import mouse, keyboard
from datetime import datetime

class ActivityTracker:
    def __init__(self, idle_threshold_seconds=30):
        self.idle_threshold = idle_threshold_seconds
        self.last_activity_time = time.time()
        self.running = False
        self.lock = threading.Lock()
        
        # Listeners
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # Jitter Filter
        self.last_x = 0
        self.last_y = 0

    def _on_move(self, x, y):
        # Ignore small movements (Jitter)
        import math
        dist = math.hypot(x - self.last_x, y - self.last_y)
        if dist < 5: # 5 Pixel Threshold (More Sensitive)
             return
             
        self.last_x = x
        self.last_y = y
        self._update_activity()

    def _on_click(self, x, y, button, pressed):
        self._update_activity()

    def _on_scroll(self, x, y, dx, dy):
        self._update_activity()

    def _on_key_press(self, key):
        self._update_activity()

    def _update_activity(self):
        with self.lock:
            self.last_activity_time = time.time()

    def start(self):
        """Start monitoring inputs."""
        if self.running:
            return
            
        self.running = True
        self.last_activity_time = time.time() # Reset to "Now" to start as WORKING
        
        # Start listeners in non-blocking mode
        self.mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        print("Tracker started.")

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        print("Tracker stopped.")

    def get_status(self):
        """Returns 'WORKING' or 'IDLE' and the seconds since last activity."""
        with self.lock:
            time_since_last_action = time.time() - self.last_activity_time
        
        if time_since_last_action > self.idle_threshold:
            return "IDLE", time_since_last_action
        else:
            return "WORKING", time_since_last_action
