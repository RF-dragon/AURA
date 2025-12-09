# interface.py
import drivers

MENU_ITEMS = ["Auto Mode", 
              "Study Mode", 
              "Relax Mode", 
              "Away Mode", 
              "Sleep Mode", 
              "Set Alarm", 
              "Voice Cmd", 
              "Report Status"]

class UserInterface:
    def __init__(self):
        self.idx = 0
        self.top = 0
    
    def scroll_up(self):
        self.idx = max(0, self.idx - 1)
        if self.idx < self.top: self.top = self.idx

    def scroll_down(self):
        self.idx = min(len(MENU_ITEMS)-1, self.idx + 1)
        if self.idx >= self.top + 3: self.top = self.idx - 2

    def get_selected_item(self):
        return MENU_ITEMS[self.idx]

    def draw_home(self, mode, lux, noise):
        if not drivers.oled: return
        t = drivers.get_datetime() # (y, m, d, h, m, s)
        date_str = "{:04d}-{:02d}-{:02d}".format(t[0], t[1], t[2])
        time_str = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
        
        drivers.oled.fill(0)
        drivers.oled.text(date_str, 20, 0)
        drivers.oled.text(time_str, 30, 10)
        drivers.oled.text(f"{mode} L:{lux} N:{int(noise)}", 0, 22)
        drivers.oled.show()

    def draw_menu(self):
        if not drivers.oled: return
        drivers.oled.fill(0)
        for i in range(3):
            item_idx = self.top + i
            if item_idx < len(MENU_ITEMS):
                prefix = ">" if item_idx == self.idx else " "
                drivers.oled.text(f"{prefix} {MENU_ITEMS[item_idx]}", 0, i * 10)
        drivers.oled.show()

    def draw_alarm_set(self, alarm_sys):
        if not drivers.oled: return
        drivers.oled.fill(0)
        drivers.oled.text("Set Alarm:", 0, 0)
        h_str = f">{alarm_sys.hour:02d}<" if alarm_sys.edit_mode_hour else f"{alarm_sys.hour:02d}"
        m_str = f">{alarm_sys.minute:02d}<" if not alarm_sys.edit_mode_hour else f"{alarm_sys.minute:02d}"
        drivers.oled.text(f"{h_str} : {m_str}", 20, 12)
        drivers.oled.text("UP/DN | SEL=Next", 0, 24)
        drivers.oled.show()