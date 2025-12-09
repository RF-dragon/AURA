import machine
import time
import urequests
import json
import gc

# Hardware & Modules
import drivers
from buttons import ButtonHandler
from alarm_system import AlarmSystem
from menu_page import UserInterface

# ----- Configuration -----
AWAY_TIMEOUT_MS = 5 * 60 * 1000
CLOUD_UPDATE_INTERVAL_MS = 5000

# Replace with your IP address
SERVER_URL = "http://<YOUR_SERVER_IP>:5000"

# ----- Global State -----
current_mode = "STARTUP"
manual_override = False
last_motion_time = time.ticks_ms()
last_cloud_update = time.ticks_ms()

# --- Instantiate Objects ---
input_mgr = ButtonHandler()
alarm_sys = AlarmSystem()
ui = UserInterface()

# --- States ---
STATE_HOME = 0 
STATE_MENU = 1 
STATE_ALARM_SET = 2 
current_state = STATE_HOME

def get_auto_mode(motion_status, lux, noise):
    if manual_override: return current_mode
    now = time.ticks_ms()
    
    # 1. AWAY Logic
    if not motion_status['any'] and time.ticks_diff(now, last_motion_time) > AWAY_TIMEOUT_MS:
        if current_mode == "AWAY" and motion_status['any']: return "ALERT"
        return "AWAY"

    # 2. SLEEP Logic
    if lux < 10 and noise < 1000: return "SLEEP"
    # 3. RELAX Logic
    if lux < 100: return "RELAX"
    
    return "STUDY"

def handle_visuals(mode, lux, noise):
    if mode == "ALERT": drivers.led_strip_flash((255, 0, 0))
    elif mode == "SLEEP": drivers.led_strip_off()
    elif mode == "AWAY": drivers.led_strip_solid((0, 0, 50))
    elif mode == "RELAX":
        brightness = max(10, 255 - int(lux * 2))
        drivers.led_strip_solid((255, 140, 0), int(brightness))
    elif mode == "STUDY": drivers.led_strip_solid((200, 200, 255), 200)

def handle_voice_command():
    drivers.display_text("Listening...")
    drivers.led_strip_solid((0, 255, 0), 100)
    audio_data = drivers.record_audio(3)
    
    try:
        res = urequests.post(f"{SERVER_URL}/command", data=audio_data)
        cmd = res.json()
        action = cmd.get('name')
        
        global manual_override, current_mode
        if action == "turn_on_lights":
            manual_override = True
            current_mode = "STUDY"
        elif action == "party_mode":
            drivers.led_strip_rainbow()
        
        res.close()
    except:
        drivers.display_text("Net Error")

def main():
    global current_mode, last_motion_time, last_cloud_update, \
           current_state, manual_override
    
    drivers.init_hardware()
    drivers.led_startup_animation()
    drivers.play_audio_cue("startup")
    
    # Alarm Animation Helper
    led_flow_tick = 0
    
    while True:
        try:
            # --- 1. SENSE ---
            motion_data = drivers.read_pir_all()
            lux = drivers.read_light_sensors()
            n1, n2 = drivers.read_mic_volume()
            noise = (n1 + n2) // 2 # Average noise from both mics
            btn_idx = input_mgr.check_buttons()
            
            if motion_data['any']: last_motion_time = time.ticks_ms()

            # --- 2. ALARM CHECK ---
            if alarm_sys.check_trigger():
                drivers.play_audio_cue("alarm")
                drivers.display_text("ALARM!!!")
                
                # Flowing Red Effect
                drivers.led_strip_flow_red(led_flow_tick)
                led_flow_tick += 1
                
                if btn_idx != -1: # Any button stops alarm
                    alarm_sys.stop()
                    drivers.play_audio_cue("back")
                
                time.sleep(0.1) 
                continue 

            # --- 3. INPUT HANDLER ---
            if btn_idx != -1:
                drivers.play_audio_cue("select" if btn_idx == 2 else "back")
                
                if current_state == STATE_HOME:
                    if btn_idx == 2: current_state = STATE_MENU
                
                elif current_state == STATE_MENU:
                    if btn_idx == 0: ui.scroll_up()
                    elif btn_idx == 1: ui.scroll_down()
                    elif btn_idx == 3: current_state = STATE_HOME
                    elif btn_idx == 2: 
                        sel = ui.get_selected_item()
                        if sel == "Auto Mode":
                            manual_override = False
                            current_state = STATE_HOME
                        elif sel in ["Study Mode", "Relax Mode", "Sleep Mode"]:
                            manual_override = True
                            current_mode = sel.split()[0].upper()
                            current_state = STATE_HOME
                        elif sel == "Set Alarm":
                            current_state = STATE_ALARM_SET
                        elif sel == "Voice Cmd":
                            handle_voice_command()
                            current_state = STATE_HOME
                        elif sel == "Report Status":
                            drivers.play_audio_cue("status_report")
                            current_state = STATE_HOME

                elif current_state == STATE_ALARM_SET:
                    if btn_idx == 0: alarm_sys.increment_time()
                    elif btn_idx == 1: alarm_sys.decrement_time()
                    elif btn_idx == 2: 
                        if alarm_sys.edit_mode_hour: alarm_sys.toggle_edit_field()
                        else: 
                            alarm_sys.enabled = True
                            drivers.display_text("Saved!")
                            time.sleep(1)
                            current_state = STATE_HOME
                            alarm_sys.reset_edit_state()
                    elif btn_idx == 3: current_state = STATE_MENU

            # --- 4. THINK & ACT ---
            new_mode = get_auto_mode(motion_data, lux, noise)
            if not manual_override and new_mode != current_mode:
                drivers.play_audio_cue("mode_switch")
                current_mode = new_mode

            if current_state == STATE_HOME:
                apply_mode_effects(current_mode, lux, noise)
                ui.draw_home(current_mode, lux, noise)
            elif current_state == STATE_MENU:
                ui.draw_menu()
            elif current_state == STATE_ALARM_SET:
                ui.draw_alarm_set(alarm_sys)

            # --- 5. CLOUD ---
            if time.ticks_diff(time.ticks_ms(), last_cloud_update) > CLOUD_UPDATE_INTERVAL_MS:
                try:
                    payload = {"mode": current_mode, "lux": lux, "noise": noise}
                    urequests.post(f"{SERVER_URL}/status", json=payload).close()
                except: pass
                last_cloud_update = time.ticks_ms()

            time.sleep(0.05)
            gc.collect()

        except Exception as e:
            print("Main Error:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()