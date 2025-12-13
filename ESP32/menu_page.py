# menu_page.py - OLED UI rendering + menu state for AURA
#
# Notes:
# - This module is intentionally “dumb UI”: it does not own the event loop.
# - main.py (or the controller layer) updates idx/top via scroll_up/down and calls draw_*.
import drivers

class UserInterface:
    def __init__(self):
        # Menu items shown on the OLED (3 rows visible at once).
        self.MENU_ITEMS = [
            "Auto Mode",
            "Study Mode",
            "Relax Mode",
            "Away Mode",
            "Sleep Mode",
            "Set Alarm",
            "Voice Cmd",
        ]

        # Compact labels to fit 128x32 layout cleanly.
        self.MODE_ABBREVIATIONS = {
            "STUDY": "STY",
            "RELAX": "RLX",
            "SLEEP": "SLP",
            "AWAY":  "AWY",
            "ALERT": "ALT",
            "MANUAL": "MAN"
        }

        # Menu cursor state
        self.idx = 0   # selected item index
        self.top = 0   # top-of-window index (for 3 visible items)

        # Backwards-compat aliases used elsewhere in the codebase
        self.menu_index = self.idx
        self.menu_top_row = self.top
    
    def scroll_up(self):
        """Move selection up (wrap at top). Window follows selection."""
        if self.idx == 0:
            self.idx = len(self.MENU_ITEMS) - 1
        else:
            self.idx -= 1
        
        self.top = self.idx
        self.menu_index = self.idx
        self.menu_top_row = self.top

    def scroll_down(self):
        """Move selection down (wrap at bottom). Window follows selection."""
        if self.idx == len(self.MENU_ITEMS) - 1:
            self.idx = 0
        else:
            self.idx += 1

        self.top = self.idx
        self.menu_index = self.idx
        self.menu_top_row = self.top

    def get_selected_item(self):
        """Return the currently selected menu item label."""
        return self.MENU_ITEMS[self.idx]

    # =========================================
    #            DRAWING FUNCTIONS
    # =========================================

    def draw_home(self, mode, lux, noise):
        """
        Main dashboard (128x32, centered 3-line layout):
        - YYYY-MM-DD
        - HH:MM:SS
        - MODE  L:<lux>  N:<noise>
        """
        if not drivers.oled:
            return

        # Center helper: SSD1306 font is ~8 px per character.
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
        drivers.oled.text(date_str,   center_x(date_str),   2)
        drivers.oled.text(time_str,   center_x(time_str),  12)
        drivers.oled.text(status_line,center_x(status_line),22)

        drivers.oled.show()

    def draw_menu(self):
        """Menu list view: renders 3 rows starting at self.top with '>' cursor."""
        if not drivers.oled: 
            return
        
        drivers.oled.fill(0)
        
        for i in range(3):
            item_idx = self.top + i
            if item_idx < len(self.MENU_ITEMS):
                prefix = ">" if item_idx == self.idx else " "
                drivers.oled.text(f"{prefix} {self.MENU_ITEMS[item_idx]}", 0, i * 10)
                
        drivers.oled.show()

    def draw_alarm_set(self, alarm_system):
        """
        Alarm setting UI:
        - Highlights the editable field using > < around HH or MM.
        """
        if not drivers.oled: return
        
        drivers.oled.fill(0)
        drivers.oled.text("Set Alarm:", 0, 0)
        
        if alarm_system.edit_mode_hour:
            h_str = f">{alarm_system.hour:02d}<"
            m_str = f"{alarm_system.minute:02d}"
        else:
            h_str = f"{alarm_system.hour:02d}"
            m_str = f">{alarm_system.minute:02d}<"
        
        time_display = f"{h_str} : {m_str}"
        
        drivers.oled.text(time_display, 20, 15)
        drivers.oled.text("UP/DN | SEL=Next", 0, 25)
        
        drivers.oled.show()
