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
            "Report Status"
        ]
        
        # Abbreviations for Home Screen (Fits 128px width)
        self.MODE_ABBREVIATIONS = {
            "STARTUP": "INIT",
            "STUDY": "STY",
            "RELAX": "RLX",
            "SLEEP": "SLP",
            "AWAY":  "AWY",
            "ALERT": "ALT",
            "MANUAL": "MAN"
        }

        # State persistence: These variables keep track of where you were
        self.idx = 0     # Currently highlighted item index
        self.top = 0     # Index of the item at the top of the screen (scroll window)
    
    def scroll_up(self):
        """ Moves selection up, scrolls window if needed """
        self.idx = max(0, self.idx - 1)
        # If we move above the visible window, shift the window up
        if self.idx < self.top: 
            self.top = self.idx

    def scroll_down(self):
        """ Moves selection down, scrolls window if needed """
        self.idx = min(len(self.MENU_ITEMS)-1, self.idx + 1)
        # If we move below the visible window (3 lines), shift window down
        if self.idx >= self.top + 3: 
            self.top = self.idx - 2

    def get_selected_item(self):
        """ Returns the string of the currently selected item """
        return self.MENU_ITEMS[self.idx]

    # =========================================
    #            DRAWING FUNCTIONS
    # =========================================

    def draw_home(self, mode, lux, noise):
        """ 
        Renders the Main Dashboard.
        Line 1: YYYY-MM-DD
        Line 2: HH:MM:SS
        Line 3: MODE L:xxx N:xxx
        """
        if not drivers.oled: return
        
        # Get Time from Drivers (Synced via NTP)
        t = drivers.get_datetime()
        
        # Format strings (YYYY-MM-DD)
        date_str = "{:04d}-{:02d}-{:02d}".format(t[0], t[1], t[2])
        # Format Time (HH:MM:SS)
        time_str = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
        
        # Create Status Line: "STY L:120 N:50"
        short_mode = self.MODE_ABBREVIATIONS.get(mode, mode[:3])
        status_str = f"{short_mode} L:{int(lux)} N:{int(noise)}"
        
        drivers.oled.fill(0) # Clear screen
        
        # Layout for 128x32 screen (approx 10px height per line)
        drivers.oled.text(date_str, 20, 0)   # Top center
        drivers.oled.text(time_str, 28, 10)  # Middle center
        drivers.oled.text(status_str, 0, 22) # Bottom
        
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
        