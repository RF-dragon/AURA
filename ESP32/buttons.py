import time
import drivers

# --- Constants for Timing ---
DEBOUNCE_MS = 50       # Ignore signal noise shorter than this
HOLD_DELAY_MS = 500    # Time to hold before auto-repeat starts
REPEAT_RATE_MS = 150   # Speed of auto-repeat while holding

class ButtonHandler:
    def __init__(self):
        # Tracking state for 4 buttons
        self.last_press = [0, 0, 0, 0]   # Timestamp of last valid press
        self.down_time = [0, 0, 0, 0]    # Timestamp when button was first held down
        self.last_repeat = [0, 0, 0, 0]  # Timestamp of last auto-repeat event
        self.held = [False, False, False, False] # Current state (Held vs Released)

    def check_buttons(self):
        """
        Scans all buttons.
        Returns: 
            The index (0-3) of the triggered button.
            Returns -1 if no action is triggered this cycle.
        """
        now = time.ticks_ms()
        triggered_btn = -1
        
        # Iterate through all 4 buttons (0=Up, 1=Down, 2=Select, 3=Back)
        for i in range(4):
            # drivers.read_raw_button returns True if pressed
            is_pressed = drivers.read_raw_button(i)
            
            if is_pressed:
                if not self.held[i]:
                    # --- EVENT: FIRST PRESS ---
                    # Check debounce timer
                    if time.ticks_diff(now, self.last_press[i]) > DEBOUNCE_MS:
                        self.held[i] = True
                        self.down_time[i] = now
                        self.last_press[i] = now
                        triggered_btn = i # Trigger immediately on press
                else:
                    # --- EVENT: HOLDING ---
                    # Only Buttons 0 (Up) and 1 (Down) support auto-repeat scrolling
                    if i in [0, 1]: 
                        # Check if held longer than the initial delay
                        if time.ticks_diff(now, self.down_time[i]) > HOLD_DELAY_MS:
                            # Check if enough time passed for the next repeat step
                            if time.ticks_diff(now, self.last_repeat[i]) > REPEAT_RATE_MS:
                                self.last_repeat[i] = now
                                triggered_btn = i # Trigger repeat event
            else:
                # Button Released
                self.held[i] = False
                
        return triggered_btn