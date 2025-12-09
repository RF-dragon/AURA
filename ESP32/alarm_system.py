import drivers

class AlarmSystem:
    def __init__(self):
        self.hour = 8
        self.minute = 0
        self.enabled = False
        self.ringing = False
        self.edit_mode_hour = True

    def check_trigger(self):
        if not self.enabled or self.ringing: return False
        t = drivers.get_datetime()
        if t[3] == self.hour and t[4] == self.minute:
            self.ringing = True
            return True
        return False

    def stop(self):
        self.ringing = False
        self.enabled = False
        drivers.led_strip_off()

    def increment_time(self):
        if self.edit_mode_hour: self.hour = (self.hour + 1) % 24
        else: self.minute = (self.minute + 1) % 60

    def decrement_time(self):
        if self.edit_mode_hour: self.hour = (self.hour - 1) % 24
        else: self.minute = (self.minute - 1) % 60
            
    def toggle_edit_field(self):
        self.edit_mode_hour = not self.edit_mode_hour
        
    def reset_edit_state(self):
        self.edit_mode_hour = True