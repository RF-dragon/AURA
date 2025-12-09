import time
import drivers

DEBOUNCE_MS = 50
HOLD_DELAY_MS = 500
REPEAT_RATE_MS = 150

class ButtonHandler:
    def __init__(self):
        self.last_press = [0, 0, 0, 0]
        self.down_time = [0, 0, 0, 0]
        self.last_repeat = [0, 0, 0, 0]
        self.held = [False, False, False, False]

    def check_buttons(self):
        now = time.ticks_ms()
        triggered_btn = -1
        
        for i in range(4):
            pressed = drivers.read_raw_button(i)
            if pressed:
                if not self.held[i]: # First Press
                    if time.ticks_diff(now, self.last_press[i]) > DEBOUNCE_MS:
                        self.held[i] = True
                        self.down_time[i] = now
                        self.last_press[i] = now
                        triggered_btn = i
                else: # Held
                    if i in [0, 1]: # Only repeat UP/DOWN
                        if time.ticks_diff(now, self.down_time[i]) > HOLD_DELAY_MS:
                            if time.ticks_diff(now, self.last_repeat[i]) > REPEAT_RATE_MS:
                                self.last_repeat[i] = now
                                triggered_btn = i
            else:
                self.held[i] = False
        return triggered_btn