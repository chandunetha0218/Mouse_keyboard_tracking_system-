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
        
        # Long Press Detection
        self.last_keypress_key = None
        self.last_keypress_time = 0

    def _on_move(self, x, y):
        try:
            if x is None or y is None: 
                return
            import math
            dist = math.hypot(x - self.last_x, y - self.last_y)
            # 3 Pixel Threshold for better trackpad detection
            if dist < 3: 
                return
                 
            self.last_x = x
            self.last_y = y
            self._update_activity()
        except Exception:
            pass

    def _on_click(self, x, y, button, pressed):
        try:
            self._update_activity()
        except Exception:
            pass

    def _on_scroll(self, x, y, dx, dy):
        try:
            self._update_activity()
        except Exception:
            pass

    def _on_key_press(self, key):
        current_time = time.time()
        
        # Check if it's the same key as before
        if key == self.last_keypress_key:
            duration = current_time - self.last_keypress_time
            if duration > 10:
                # User is holding key > 10s. Treat as IDLE (Do not update activity)
                return
        else:
            # New key pressed
            self.last_keypress_key = key
            self.last_keypress_time = current_time
            
        self._update_activity()

    def _on_key_release(self, key):
        # Reset on release
        if key == self.last_keypress_key:
            self.last_keypress_key = None
            self.last_keypress_time = 0
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
            on_press=self._on_key_press,
            on_release=self._on_key_release
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
