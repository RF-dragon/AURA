"""
alarm_system.py - Minimal alarm state/policy for AURA.

Keeps alarm time + armed/ringing state. main.py polls check_trigger() and handles
the actual alarm UI/beep pattern. stop() clears ringing and disarms (one-shot).
"""

import drivers

class AlarmSystem:
    def __init__(self):
        # Default alarm time (24-hour clock) shown on first boot.
        self.hour = 8
        self.minute = 0

        # Armed/ringing latches. "ringing" stays True until stop() is called..
        self.enabled = False
        self.ringing = False

        # UI focus: True => editing hour, False => editing minute.
        self.edit_mode_hour = True

    # -------------------------------
    # Core alarm logic
    # -------------------------------

    def check_trigger(self):
        """
        Poll-based trigger check.

        Returns True only when we *enter* the ringing state (edge trigger).
        Seconds are ignored so the alarm is robust to loop timing.
        """
        if not self.enabled or self.ringing: 
            return False
            
        # Expected tuple: (year, month, day, hour, minute, second, ...)
        t = drivers.get_datetime()
        
        if t[3] == self.hour and t[4] == self.minute:
            self.ringing = True
            return True
            
        return False

    def stop(self):
        """Dismiss alarm: clears ringing and disarms (one-shot), plus LED cleanup."""
        self.ringing = False
        self.enabled = False
        drivers.led_strip_off()

    # -------------------------------
    # UI editing helpers
    # -------------------------------

    def increment_time(self):
        """ Increment currently-selected field with wraparound. """
        if self.edit_mode_hour:
            self.hour = (self.hour + 1) % 24
        else:
            self.minute = (self.minute + 1) % 60

    def decrement_time(self):
        """ Decrement currently-selected field with wraparound. """
        if self.edit_mode_hour:
            self.hour = (self.hour - 1) % 24
        else:
            self.minute = (self.minute - 1) % 60
            
    def toggle_edit_field(self):
        """ Switch UI focus between hour and minute fields. """
        self.edit_mode_hour = not self.edit_mode_hour
        
    def reset_edit_state(self):
        """ When entering the alarm page, start by editing the hour field. """
        self.edit_mode_hour = True
