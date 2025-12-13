"""
buttons.py - Button scanning + debouncing for AURA (polling model).

Design:
- main.py polls ButtonHandler.check_buttons() in the event loop.
- We debounce "first press" edges and optionally auto-repeat UP/DOWN while held.
- Button indices follow the drivers layer: 0=Up, 1=Down, 2=Select, 3=Back.
"""

import time
import drivers

# Timing parameters (tuned for HUZZAH buttons + typical loop rates).
DEBOUNCE_MS = 50
HOLD_DELAY_MS = 500
REPEAT_RATE_MS = 150

class ButtonHandler:
    def __init__(self):
        # Per-button state (4 buttons total).
        self.last_press = [0, 0, 0, 0]     # last accepted press time (for debounce)
        self.down_time = [0, 0, 0, 0]      # when button first went down (for hold)
        self.last_repeat = [0, 0, 0, 0]    # last repeat event time (for auto-repeat)
        self.held = [False, False, False, False]  # pressed latch

    def check_buttons(self):
        """
        Scan all buttons once.

        Returns:
            0..3 if a button event should be handled this cycle, else -1.

        Event rules:
        - Any button triggers immediately on a debounced *edge* (press).
        - UP/DOWN (0/1) also trigger repeated events while held (after HOLD_DELAY_MS).
        """
        now = time.ticks_ms()
        triggered_btn = -1
        
        for i in range(4):
            # drivers.read_raw_button(i) should be True while physically pressed.
            is_pressed = drivers.read_raw_button(i)
            
            if is_pressed:
                if not self.held[i]:
                    # First press (edge): accept only if outside debounce window.
                    if time.ticks_diff(now, self.last_press[i]) > DEBOUNCE_MS:
                        self.held[i] = True
                        self.down_time[i] = now
                        self.last_press[i] = now
                        triggered_btn = i
                else:
                    # Held: auto-repeat only for UP/DOWN to support menu scrolling.
                    if i in [0, 1]: 
                        if time.ticks_diff(now, self.down_time[i]) > HOLD_DELAY_MS:
                            if time.ticks_diff(now, self.last_repeat[i]) > REPEAT_RATE_MS:
                                self.last_repeat[i] = now
                                triggered_btn = i
            else:
                # Released: clear latch so the next press can generate an edge.
                self.held[i] = False
                
        return triggered_btn
    