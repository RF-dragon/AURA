# menu_page.py - Handles OLED Graphics & UI Logic
import drivers

class UserInterface:
    def __init__(self):
        # Menu Configuration
        self.MENU_ITEMS = [
            "Auto Mode",
            "Study Mode",
            "Relax Mode",
            "Away Mode",
            "Sleep Mode",
            "Set Alarm",
            "Voice Cmd",
        ]

        # Mode abbreviations for compact display
        self.MODE_ABBREVIATIONS = {
            "STUDY": "STY",
            "RELAX": "RLX",
            "SLEEP": "SLP",
            "AWAY":  "AWY",
            "ALERT": "ALT",
            "MANUAL": "MAN"
        }

        # State persistence: current selection + scroll window
        self.idx = 0      # currently highlighted item
        self.top = 0      # top-of-window index (for 3 visible lines)

        # Backwards-compat alias for main.py
        self.menu_index = self.idx
        self.menu_top_row = self.top
    
    def scroll_up(self):
        """Moves selection up, wraps to bottom from top."""
        if self.idx == 0:
            self.idx = len(self.MENU_ITEMS) - 1
        else:
            self.idx -= 1
        # Put selected item at top row
        self.top = self.idx
        self.menu_index = self.idx
        self.menu_top_row = self.top

    def scroll_down(self):
        """Moves selection down, wraps to top from bottom."""
        if self.idx == len(self.MENU_ITEMS) - 1:
            self.idx = 0
        else:
            self.idx += 1
        # Put selected item at top row
        self.top = self.idx
        self.menu_index = self.idx
        self.menu_top_row = self.top

    def get_selected_item(self):
        """ Returns the string of the currently selected item """
        return self.MENU_ITEMS[self.idx]

    # =========================================
    #            DRAWING FUNCTIONS
    # =========================================

    def draw_home(self, mode, lux, noise):
        """ 
        Renders the Main Dashboard (128x32, 3 lines):
        L1: YYYY-MM-DD
        L2: HH:MM:SS
        L3: MODE  L:xxx  N:yyy
        (mode_source is ignored for display)
        """
        if not drivers.oled:
            return

        # Small helper to center a string horizontally on 128px width.
        # SSD1306 default font is ~8px per character.
        def center_x(text):
            w = len(text) * 8
            x = (128 - w) // 2
            return 0 if x < 0 else x

        t = drivers.get_datetime()
        
        date_str = "{:04d}-{:02d}-{:02d}".format(t[0], t[1], t[2])
        time_str = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
        
        short_mode = self.MODE_ABBREVIATIONS.get(mode, (mode or "")[:3])
        status_line = "{}  L:{}  N:{}".format(short_mode, int(lux), int(noise))

        drivers.oled.fill(0)

        # Vertically similar to before, but each line horizontally centered
        drivers.oled.text(date_str,   center_x(date_str),   2)   # L1
        drivers.oled.text(time_str,   center_x(time_str),  12)   # L2
        drivers.oled.text(status_line,center_x(status_line),22)  # L3

        drivers.oled.show()

    def draw_menu(self):
        """ 
        Renders the Scrolling Menu List.
        Shows 3 items based on self.top window.
        """
        if not drivers.oled: return
        
        drivers.oled.fill(0)
        
        # Loop through the 3 visible slots
        for i in range(3):
            item_idx = self.top + i
            
            # Ensure we don't try to draw items that don't exist
            if item_idx < len(self.MENU_ITEMS):
                # Draw the cursor ">" if this is the selected item
                prefix = ">" if item_idx == self.idx else " "
                
                # Draw text at y = 0, 10, 20
                drivers.oled.text(f"{prefix} {self.MENU_ITEMS[item_idx]}", 0, i * 10)
                
        drivers.oled.show()

    def draw_alarm_set(self, alarm_system):
        """ 
        Renders the Alarm Setting UI.
        Shows: "Set Alarm:" and "HH : MM" with cursor highlighting.
        """
        if not drivers.oled: return
        
        drivers.oled.fill(0)
        drivers.oled.text("Set Alarm:", 0, 0)
        
        # Determine which part is being edited (Hour or Minute) to add brackets > <
        if alarm_system.edit_mode_hour:
            h_str = f">{alarm_system.hour:02d}<"
            m_str = f"{alarm_system.minute:02d}"
        else:
            h_str = f"{alarm_system.hour:02d}"
            m_str = f">{alarm_system.minute:02d}<"
        
        # Combine string: ">08< : 00"
        time_display = f"{h_str} : {m_str}"
        
        drivers.oled.text(time_display, 20, 15)
        drivers.oled.text("UP/DN | SEL=Next", 0, 25) # Instruction text
        
        drivers.oled.show()
        
