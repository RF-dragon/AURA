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
AWAY_TIMEOUT_MS = 5 * 60 * 1000  # 5 Minutes to trigger Away Mode
CLOUD_UPDATE_INTERVAL_MS = 5000  # Send data to cloud every 5 seconds
# SERVER_URL = # Replace with your laptop IP

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
sensor_buffer = []

def get_auto_mode(motion_status, lux, noise):
    """ Determines System Mode based on sensor inputs. """
    if manual_override: return current_mode
    
    now = time.ticks_ms()
    is_moving = motion_status['any']
    
    # 1. AWAY Logic (Priority)
    if not is_moving and time.ticks_diff(now, last_motion_time) > AWAY_TIMEOUT_MS:
        if current_mode == "AWAY" and is_moving: return "ALERT"
        return "AWAY"

    # 2. SLEEP Logic
    if lux < 100 and noise < 1000: return "SLEEP"

    # 3. RELAX Logic
    # Simple logic: If it's noisy and somewhat bright, relax? 
    # (Adjust logic based on your preference)
    if noise > 3000 and lux > 300: return "RELAX"

    # 4. Default
    return "STUDY"

def apply_mode_effects(mode, lux, noise):
    """ Controls LED Strip based on Mode. """
    if mode == "ALERT": 
        drivers.led_strip_flash((255, 0, 0)) # Panic Flash Red
    elif mode == "SLEEP": 
        drivers.led_strip_off() # Lights Out
    elif mode == "AWAY": 
        drivers.led_strip_solid((0, 0, 50)) # Dim Blue 'Security' Light
    elif mode == "RELAX":
        # Adaptive Lighting: Dimmer room = Dimmer/Warmer LED
        brightness = max(10, min(100, lux))
        drivers.led_strip_solid((255, 140, 0), int(brightness)) # Warm Orange
    elif mode == "STUDY": 
        drivers.led_strip_solid((200, 200, 255), 200) # Bright Cool White

def handle_voice_command():
    drivers.display_text("Listening...")
    drivers.led_strip_solid((0, 255, 0), 100) # Green
    
    # Record 3 seconds
    audio_data = drivers.record_audio(3)
    
    drivers.display_text("Thinking...")
    try:
        res = urequests.post(f"{SERVER_URL}/command", data=audio_data)
        cmd = res.json()
        action = cmd.get('name')
        print(f"AI Action: {action}")
        
        global manual_override, current_mode
        if action == "turn_on_lights":
            manual_override = True
            current_mode = "STUDY"
            drivers.display_text("Lights ON")
        elif action == "party_mode":
            drivers.led_strip_rainbow()
        
        res.close()
    except Exception as e:
        print("Cloud Error:", e)
        drivers.display_text("Net Error")
    
    time.sleep(1)

def execute_menu_action(index):
    global current_mode, manual_override, current_state
    item = ui.MENU_ITEMS[index] # Access menu items from UI class
    print(f"Selected: {item}")
    
    if item == "Auto Mode":
        manual_override = False
        drivers.display_text("Auto Active")
        current_state = STATE_HOME
    elif item in ["Study Mode", "Relax Mode", "Away Mode", "Sleep Mode"]:
        manual_override = True
        current_mode = item.split()[0].upper()
        current_state = STATE_HOME
    elif item == "Set Alarm":
        current_state = STATE_ALARM_SET
        alarm_sys.reset_edit_state()
    elif item == "Voice Cmd":
        handle_voice_command()
        current_state = STATE_HOME
    elif item == "Report Status":
        drivers.play_audio_cue("status_report")
        current_state = STATE_HOME

def main():
    global current_mode, last_motion_time, last_cloud_update, \
           current_state, menu_index, menu_top_row, sensor_buffer
    
    # Initialize Hardware
    print("AURA System Starting...")
    drivers.init_hardware()
    
    # Startup Animation
    drivers.display_text("AURA Init...")
    drivers.play_audio_cue("startup")
    drivers.led_startup_animation() 
    
    # Alarm Animation Helper
    led_flow_tick = 0
    
    while True:
        try:
            # --- 1. SENSE Phase ---
            motion_data = drivers.read_pir_all()
            lux = drivers.read_light_sensors()
            n1, n2 = drivers.read_mic_volume()
            noise = (n1 + n2) // 2 
            btn_idx = input_mgr.check_buttons() 
            curr_time_str = drivers.get_current_time()
            
            if motion_data['any']: last_motion_time = time.ticks_ms()

            # --- 2. ALARM CHECK ---
            if alarm_sys.check_trigger():
                # Alarm is Ringing!
                drivers.play_audio_cue("alarm")
                drivers.display_text("ALARM!!!")
                
                # Flowing Red LED Effect
                drivers.led_strip_flow_red(led_flow_tick)
                led_flow_tick += 1
                
                # ANY button stops it
                if btn_idx != -1:
                    print("Alarm Dismissed")
                    alarm_sys.stop()
                    drivers.play_audio_cue("back")
                
                time.sleep(0.1) # Fast loop for animation
                continue 

            # --- 3. INPUT HANDLER ---
            if btn_idx != -1:
                drivers.play_audio_cue("select" if btn_idx == 2 else "back")
                
                if current_state == STATE_HOME:
                    if btn_idx == 2: # SELECT -> Menu
                        current_state = STATE_MENU
                        # Reset menu position
                        ui.idx = 0
                        ui.top = 0
                
                elif current_state == STATE_MENU:
                    if btn_idx == 0: ui.scroll_up()      # UP
                    elif btn_idx == 1: ui.scroll_down()  # DOWN
                    elif btn_idx == 3: current_state = STATE_HOME # BACK
                    elif btn_idx == 2: # SELECT
                        execute_menu_action(ui.idx)

                elif current_state == STATE_ALARM_SET:
                    if btn_idx == 0: alarm_sys.increment_time() # UP
                    elif btn_idx == 1: alarm_sys.decrement_time() # DOWN
                    elif btn_idx == 2: # SELECT
                        if alarm_sys.edit_mode_hour:
                            alarm_sys.toggle_edit_field() # Move to Minute
                        else:
                            alarm_sys.enabled = True # Save
                            drivers.display_text("Alarm Saved!")
                            time.sleep(1)
                            current_state = STATE_HOME
                            alarm_sys.reset_edit_state()
                    elif btn_idx == 3: # BACK
                        current_state = STATE_MENU

            # --- 4. THINK & ACT ---
            new_mode = get_auto_mode(motion_data, lux, noise)
            
            if not manual_override and new_mode != current_mode:
                drivers.play_audio_cue("mode_switch")
                current_mode = new_mode

            # Only apply effects if NOT ringing alarm
            if not alarm_sys.ringing:
                if current_state == STATE_HOME:
                    apply_mode_effects(current_mode, lux, noise)
                    ui.draw_home(current_mode, lux, noise)
                elif current_state == STATE_MENU:
                    ui.draw_menu()
                elif current_state == STATE_ALARM_SET:
                    ui.draw_alarm_set(alarm_sys)

            # --- 5. CLOUD SYNC ---
            if time.ticks_diff(time.ticks_ms(), last_cloud_update) > CLOUD_UPDATE_INTERVAL_MS:
                try:
                    payload = {"mode": current_mode, "lux": lux, "noise": noise}
                    # Send Heartbeat
                    # urequests.post(f"{SERVER_URL}/status", json=payload).close()
                    print(f"Cloud Heartbeat: {payload}")
                    
                    # Buffer Logic (Fixed Syntax)
                    sensor_buffer.extend([lux, noise, int(motion_data["any"])])
                    if len(sensor_buffer) > 40:
                        sensor_buffer = sensor_buffer[-40:] # Keep last 40 items
                except Exception as e: 
                    print("Cloud Error:", e)
                last_cloud_update = time.ticks_ms()

            time.sleep(0.05)
            gc.collect()

        except Exception as e:
            print("Main Error:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()