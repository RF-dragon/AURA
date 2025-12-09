import drivers

# --- Menu Configuration ---
# The order here must match the logic in main.py
MENU_ITEMS = [
    "Auto Mode",     
    "Study Mode",    
    "Relax Mode",   
    "Sleep Mode",    
    "Set Alarm",     
    "Voice Cmd",
    "Report Status"
]

# Short names for Home Screen to fit 128px width
# (Screen allows approx 16 characters per line)
MODE_ABBREVIATIONS = {
    "STARTUP": "INIT",
    "STUDY": "STY",
    "RELAX": "RLX",
    "SLEEP": "SLP",
    "AWAY":  "AWY",
    "ALERT": "ALT",
    "MANUAL": "MAN"
}

class UserInterface:
    def __init__(self):
        # State persistence: These variables keep track of where you were
        self.menu_index = 0     # Currently highlighted item index
        self.menu_top_row = 0   # Index of the item at the top of the screen
    
    def scroll_up(self):
        """ Moves selection up, scrolls window if needed """
        self.menu_index = max(0, self.menu_index - 1)
        # If we move above the visible window, shift the window up
        if self.menu_index < self.menu_top_row: 
            self.menu_top_row = self.menu_index

    def scroll_down(self):
        """ Moves selection down, scrolls window if needed """
        self.menu_index = min(len(MENU_ITEMS)-1, self.menu_index + 1)
        # If we move below the visible window (3 lines), shift window down
        if self.menu_index >= self.menu_top_row + 3: 
            self.menu_top_row = self.menu_index - 2

    def get_selected_item(self):
        """ Returns the string of the currently selected item """
        return MENU_ITEMS[self.menu_index]

    # =========================================
    #            DRAWING FUNCTIONS
    # =========================================

    def draw_home(self, mode, lux, noise):
        """ 
        Renders the Main Dashboard.
        Layout:
        Line 0: YYYY-MM-DD
        Line 10: HH:MM:SS
        Line 22: MOD L:xxx N:xxx
        """
        if not drivers.oled: return
        
        # Get Time from Drivers (Synced via NTP)
        y, mo, d, h, m, s = drivers.get_datetime()
        
        # Format strings
        date_str = "{:04d}-{:02d}-{:02d}".format(y, mo, d)
        time_str = "{:02d}:{:02d}:{:02d}".format(h, m, s)
        
        # Create Status Line: "STY L:120 N:50"
        short_mode = MODE_ABBREVIATIONS.get(mode, mode[:3])
        status_str = f"{short_mode} L:{lux} N:{int(noise)}"
        
        drivers.oled.fill(0) # Clear screen
        
        # Center the Time (approximate centering)
        drivers.oled.text(date_str, 20, 0)   
        drivers.oled.text(time_str, 28, 10)  
        drivers.oled.text(status_str, 0, 22) 
        
        drivers.oled.show()

    def draw_menu(self):
        """ 
        Renders the Menu List.
        Shows 3 items based on self.menu_top_row.
        """
        if not drivers.oled: return
        
        drivers.oled.fill(0)
        
        # Loop through the 3 visible slots
        for i in range(3):
            item_idx = self.menu_top_row + i
            
            # Ensure we don't try to draw items that don't exist
            if item_idx < len(MENU_ITEMS):
                # Draw the cursor ">" if this is the selected item
                prefix = ">" if item_idx == self.menu_index else " "
                
                # Draw text at y = 0, 10, 20
                drivers.oled.text(f"{prefix} {MENU_ITEMS[item_idx]}", 0, i * 10)
                
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
        
        # Helper text at bottom
        # drivers.oled.text("SEL=Next", 0, 25) # Optional if space permits
        
        drivers.oled.show()
        