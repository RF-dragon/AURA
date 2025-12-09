import machine
import time
import urequests
import json
import gc

# --- Hardware & Module Imports ---
import drivers
from buttons import ButtonHandler
from alarm_system import AlarmSystem
from menu_page import UserInterface

# ----- Configuration -----
AWAY_TIMEOUT_MS = 5 * 60 * 1000  # 5 Minutes of no motion -> AWAY mode
CLOUD_UPDATE_INTERVAL_MS = 5000  # Send status to cloud every 5 secs
# REPLACE WITH YOUR LAPTOP IP! Example: "http://192.168.1.5:5000"
SERVER_URL = "http://10.206.147.172:5000" 

# ----- Global State Variables -----
current_mode = "STUDY"
manual_override = False        # True if user manually sets a mode
last_motion_time = time.ticks_ms()
last_cloud_update = time.ticks_ms()

# --- Alarm Animation State ---
led_flow_tick = 0 

# --- Instantiate Objects ---
input_mgr = ButtonHandler()
alarm_sys = AlarmSystem()
ui = UserInterface()

# --- System States ---
STATE_HOME = 0      
STATE_MENU = 1      
STATE_ALARM_SET = 2 
current_state = STATE_HOME
sensor_buffer = []

# =========================================
#            CORE LOGIC FUNCTIONS
# =========================================

def get_auto_mode(motion_status, lux, noise):
    """ 
    Determines the System Mode based on sensor inputs.
    Returns: "STUDY", "RELAX", "SLEEP", "AWAY", or "ALERT".
    """
    # If user manually set a mode, ignore sensors (until they select "Auto Mode")
    global sensor_buffer
    # If user manually set a mode, ignore sensors (until they select "Auto Mode")
    if manual_override or len(sensor_buffer) < 40: 
        return current_mode
    
    try:
        payload = {"data": sensor_buffer}
        response = urequests.post(f"{SERVER_URL}/get-mode", json=payload).text
        print(f"ML model returned mode: {response}.")
        sensor_buffer = []
        return response
    
    except Exception:
        pass
    
    now = time.ticks_ms()
    is_moving = motion_status['any']
    
    # 1. AWAY Logic: No motion for X minutes
    if not is_moving and time.ticks_diff(now, last_motion_time) > AWAY_TIMEOUT_MS:
        # Security Feature: If we are AWAY and see motion -> ALERT
        if current_mode == "AWAY" and is_moving:
            return "ALERT"
        return "AWAY"

    # 2. SLEEP Logic: Dark (< 10 lux) AND Quiet (< 1000 volume)
    if lux < 100 and noise < 1000: 
        return "SLEEP"

    # 3. RELAX Logic: Dim light (< 100 lux)
    if noise > 3000 and lux > 300: 
        return "RELAX"

    # 4. Default: Bright/Active
    return "STUDY"

def apply_mode_effects(mode, lux, noise):
    """
    Controls LED Strip based on the current Mode.
    This was missing in your previous version.
    """
    if mode == "ALERT": 
        drivers.led_strip_flash((255, 0, 0)) # Panic Flash Red
        
    elif mode == "SLEEP": 
        drivers.led_strip_off() # Lights Out
        
    elif mode == "AWAY": 
        drivers.led_strip_solid((0, 0, 50)) # Dim Blue 'Security' Light
        
    elif mode == "RELAX":
        # Adaptive Lighting: 
        # In Relax mode, we want a warm light.
        # We can make it dimmer if the room is dark to match the vibe.
        # Clamp brightness between 10 and 100.
        brightness = max(10, min(100, lux))
        drivers.led_strip_solid((255, 140, 0), int(brightness)) # Warm Orange
        
    elif mode == "STUDY": 
        drivers.led_strip_solid((200, 200, 255), 200) # Bright Cool White

def handle_voice_command():
    """ Records audio, sends to Cloud, executes returned command. """
    global current_mode, manual_override
    
    drivers.display_text("Listening...")
    drivers.led_strip_solid((0, 255, 0), 100) # Green Status
    
    # 1. Record Audio
    audio_data = drivers.record_audio(3) # 3 Seconds
    
    drivers.display_text("Thinking...")
    
    # 2. Send to Cloud
    try:
        res = urequests.post(f"{SERVER_URL}/command", data=audio_data)
        cmd = res.json()
        action = cmd.get('name')
        args = cmd.get('args', [])
        print(f"AI Action: {action} | Args: {args}")
        
        # 3. Execute Command
        if action == "turn_on_lights":
            manual_override = True
            current_mode = "STUDY"
            drivers.display_text("Lights ON")
            
        elif action == "relax_mode":
            manual_override = True
            current_mode = "RELAX"
            drivers.display_text("Relaxing...")

        elif action == "party_mode":
            # Party mode isn't a persistent state, just an effect
            drivers.led_strip_rainbow()
            drivers.display_text("Party Mode!")
            
        elif action == "set_alarm":
            # Advanced: Could parse args ["08", "30"] and set alarm_sys directly
            # For now, just confirming receipt
            drivers.display_text("Alarm Cmd Rx")
            
        elif action == "report_status":
            drivers.play_audio_cue("status_report")
            
        res.close()
    except Exception as e:
        print("Cloud Error:", e)
        drivers.display_text("Net Error")
    
    time.sleep(1)

def execute_menu_action(index):
    """ Handles Menu Selections. """
    global current_mode, manual_override, current_state
    
    # Get the string item from the UI class list
    item = ui.MENU_ITEMS[index]
    print(f"Selected: {item}")
    
    if item == "Auto Mode":
        manual_override = False
        drivers.display_text("Auto Active")
        current_state = STATE_HOME
        
    elif item == "Study Mode":
        manual_override = True
        current_mode = "STUDY"
        current_state = STATE_HOME
        
    elif item == "Relax Mode":
        manual_override = True
        current_mode = "RELAX"
        current_state = STATE_HOME
        
    elif item == "Sleep Mode":
        manual_override = True
        current_mode = "SLEEP"
        current_state = STATE_HOME

    elif item == "Away Mode":
        manual_override = True
        current_mode = "AWAY"
        current_state = STATE_HOME
        
    elif item == "Set Alarm":
        current_state = STATE_ALARM_SET # Enter Time Picker UI
        alarm_sys.reset_edit_state()
        
    elif item == "Voice Cmd":
        handle_voice_command()
        current_state = STATE_HOME
        
    elif item == "Report Status":
        drivers.play_audio_cue("status_report")
        current_state = STATE_HOME

# =========================================
#               MAIN LOOP
# =========================================

def main():
    global current_mode, last_motion_time, last_cloud_update, \
           current_state, led_flow_tick, sensor_buffer
    
    print("AURA System Starting...")
    drivers.init_hardware()
    
    # --- Startup Animation ---
    drivers.display_text("AURA Init...")
    drivers.play_audio_cue("startup")
    drivers.led_startup_animation() 
    
    while True:
        try:
            # --- 1. SENSE Phase ---
            motion_data = drivers.read_pir_all()
            lux = drivers.read_light_sensors()
            n1, n2 = drivers.read_mic_volume()
            noise = (n1 + n2) // 2 
            btn_idx = input_mgr.check_buttons() 
            curr_time_str = drivers.get_current_time()
            
            # Update Motion Timer
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

            # --- 3. INPUT HANDLER (Button State Machine) ---
            if btn_idx != -1:
                # Play click sound (Higher pitch for Select)
                drivers.play_audio_cue("select" if btn_idx == 2 else "back")
                
                # STATE: HOME DASHBOARD
                if current_state == STATE_HOME:
                    # Only 'Select' (Btn 2) enters Menu.
                    if btn_idx == 2: 
                        current_state = STATE_MENU
                        ui.menu_index = 0
                        ui.menu_top_row = 0
                
                # STATE: SCROLLING MENU
                elif current_state == STATE_MENU:
                    if btn_idx == 0: ui.scroll_up()      # UP
                    elif btn_idx == 1: ui.scroll_down()  # DOWN
                    elif btn_idx == 3: current_state = STATE_HOME # BACK
                    elif btn_idx == 2: # SELECT
                        execute_menu_action(ui.menu_index)

                # STATE: ALARM SET UI
                elif current_state == STATE_ALARM_SET:
                    if btn_idx == 0: alarm_sys.increment_time() # UP
                    elif btn_idx == 1: alarm_sys.decrement_time() # DOWN
                    elif btn_idx == 2: # SELECT
                        if alarm_sys.edit_mode_hour:
                            alarm_sys.toggle_edit_field() # Move to Minute
                        else:
                            alarm_sys.enabled = True # Save & Enable
                            drivers.display_text("Alarm Saved!")
                            time.sleep(1)
                            current_state = STATE_HOME
                            alarm_sys.reset_edit_state()
                    elif btn_idx == 3: # BACK
                        current_state = STATE_MENU

                time.sleep(0.2) # Debounce (Handled partly by input_mgr but safety here)

            # --- 4. THINK & ACT (Core Logic) ---
            # Calculate Target Mode
            new_mode = get_auto_mode(motion_data, lux, noise)
            
            # Mode Change Logic
            if new_mode != current_mode and not manual_override:
                drivers.play_audio_cue("mode_switch")
                current_mode = new_mode

            # Apply Effects (Lights)
            # Only apply if not ringing alarm (Alarm takes priority)
            if not alarm_sys.ringing:
                if current_state == STATE_HOME:
                    apply_mode_effects(current_mode, lux, noise)
                    ui.draw_home(current_mode, lux, noise)
                elif current_state == STATE_MENU:
                    ui.draw_menu()
                elif current_state == STATE_ALARM_SET:
                    ui.draw_alarm_set(alarm_sys)

            # --- 5. CLOUD SYNC ---
            # Background task: Send status every 5s
            if time.ticks_diff(time.ticks_ms(), last_cloud_update) > CLOUD_UPDATE_INTERVAL_MS:
                sensor_buffer += [lux, n1, n2, motion_data["front"]]
                if len(sensor_buffer) > 40:
                    sensor_buffer = sensor_buffer[4:]
                # try:
                #     payload = {"mode": current_mode, "lux": lux, "noise": int(noise)}
                #     # Send Heartbeat
                #     urequests.post(f"{SERVER_URL}/status", json=payload).close()
                #     print(f"Cloud Heartbeat: {payload}")
                # except Exception as e: 
                #     # print("Cloud Error:", e) # Suppress spam
                #     pass
                last_cloud_update = time.ticks_ms()

            time.sleep(0.05) 
            gc.collect()

        except Exception as e:
            raise e

if __name__ == "__main__":
    main()