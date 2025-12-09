# alarm_system.py - Manages Alarm State & Logic
import drivers

class AlarmSystem:
    def __init__(self):
        self.hour = 8
        self.minute = 0
        self.enabled = False       # Is the alarm set?
        self.ringing = False       # Is it currently making noise?
        self.edit_mode_hour = True # UI State: True=Editing Hour, False=Editing Minute

    def check_trigger(self):
        """ 
        Checks if the current time matches the alarm time.
        Returns True if alarm should start ringing.
        """
        if not self.enabled or self.ringing: 
            return False
            
        # Get current time from drivers (NTP synced)
        # time.localtime() returns (yr, mo, day, hr, min, sec, wkday, yearday)
        t = drivers.get_datetime()
        
        # Compare Hour (index 3) and Minute (index 4)
        # We ignore seconds to trigger as soon as the minute flips
        if t[3] == self.hour and t[4] == self.minute:
            self.ringing = True
            return True
            
        return False

    def stop(self):
        """ Stops the ringing and resets the alarm state """
        self.ringing = False
        self.enabled = False # Alarm is one-shot (disables after ringing)
        drivers.led_strip_off()

    def increment_time(self):
        """ Increments the selected field by 1 """
        if self.edit_mode_hour:
            self.hour = (self.hour + 1) % 24
        else:
            self.minute = (self.minute + 1) % 60

    def decrement_time(self):
        """ Decrements the selected field by 1 """
        if self.edit_mode_hour:
            self.hour = (self.hour - 1) % 24
        else:
            self.minute = (self.minute - 1) % 60
            
    def toggle_edit_field(self):
        """ Switches focus between Hour and Minute """
        self.edit_mode_hour = not self.edit_mode_hour
        
    def reset_edit_state(self):
        """ Resets UI to start editing at Hour """
        self.edit_mode_hour = True