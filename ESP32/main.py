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

from voice_ws import start_server

# ----- Configuration -----
AWAY_TIMEOUT_MS = 5 * 60 * 1000
SAMPLE_INTERVAL_MS = 1750
WINDOW_SIZE = 30          # Bigger window for ML stability

ML_PREDICTION_INTERVAL = 60   # Only classify every _ seconds

SERVER_URL = "http://10.207.104.96:5000"

# ----- Global State Variables -----
current_mode = "STUDY"
manual_override = False        # True if user manually sets a mode
last_motion_time = time.ticks_ms()
last_cloud_update = time.ticks_ms()

last_ml_check = 0

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

def get_auto_mode():
    global sensor_buffer, last_ml_check, current_mode, manual_override

    # Do not override manual mode
    if manual_override:
        return current_mode

    # Not enough data
    if len(sensor_buffer) < WINDOW_SIZE:
        return current_mode

    # Don’t classify too often
    if time.ticks_diff(time.ticks_ms(), last_ml_check) < ML_PREDICTION_INTERVAL * 1000:
        return current_mode

    last_ml_check = time.ticks_ms()

    try:
        payload = {"data": sensor_buffer}
        res = urequests.post(f"{SERVER_URL}/get-mode", json=payload)
        response_json = res.json()
        predicted = response_json.get("mode", "").upper()
        res.close()
    
        print("ML predicted:", predicted)

        if predicted not in ("STUDY", "RELAX", "SLEEP", "AWAY"):
            print("Invalid ML mode, ignoring.")
            return current_mode

        # send_auto_prediction(predicted)

        sensor_buffer = []

        return predicted

    except Exception as e:
        print("ML prediction error:", e)
        return current_mode


def send_auto_prediction(predicted_mode):
    global sensor_buffer
    try:
        payload = {
            "mode": predicted_mode.upper(),
            "data": sensor_buffer[:]      # send full 30-sample window
        }
        res = urequests.post(f"{SERVER_URL}/status", json=payload)
        print("Sent auto predicted window:", res.text)
        res.close()
        sensor_buffer = []

    except Exception as e:
        print("Failed auto prediction send:", e)


def send_status_to_server(mode):
    """
    Sends the REAL buffered 10-sample training window to the server (/status)
    """
    global sensor_buffer

    try:
        if len(sensor_buffer) < WINDOW_SIZE:
            print("Not enough samples yet to send training data.")
            return

        payload = {
            "mode": mode.upper(),
            "data": sensor_buffer[:]     # full real 10-sample buffer
        }

        res = urequests.post(f"{SERVER_URL}/status", json=payload)
        print("Status send result:", res.text)
        res.close()

        # Clear buffer once successfully sent
        sensor_buffer = []

    except Exception as e:
        print("Failed to send /status:", e)


def apply_mode_effects(mode, lux, noise, animate=False):
    """
    Controls LED strip based on the current Mode.
    If animate=True, use center-out transition; otherwise just set solid.
    """
    # Determine base color from mode
    color = drivers.get_mode_color(mode)

    if mode == "ALERT":
        # ALERT: quick flashing red
        drivers.led_strip_flash((255, 0, 0))
        return

    if mode == "SLEEP":
        # Very dim
        bright = 40
        if animate:
            drivers.led_transition_center_out(color)
        else:
            drivers.led_strip_solid(color, brightness=bright)
        return

    if mode == "AWAY":
        # Dim purple "presence"
        bright = 80
        if animate:
            drivers.led_transition_center_out(color)
        else:
            drivers.led_strip_solid(color, brightness=bright)
        return

    if mode == "RELAX":
        # Warm orange, brightness reacts to lux
        bright = max(40, min(160, int(lux)))
        if animate:
            drivers.led_transition_center_out(color)
        else:
            drivers.led_strip_solid(color, brightness=bright)
        return

    if mode == "STUDY":
        # Bright cool blue/white
        bright = 200
        if animate:
            drivers.led_transition_center_out(color)
        else:
            drivers.led_strip_solid(color, brightness=bright)
        return

def handle_voice_text(payload):
    """
    Called whenever a voice command arrives from Gradio -> Flask -> ESP32.
    payload is expected to be a dict: {"mode": "<mode_label>", "transcription": "..."}.
    """
    global current_mode, manual_override, sensor_buffer, current_state, last_ml_check

    mode_label = None
    transcription = ""

    # Accept dict or string
    if isinstance(payload, dict):
        mode_label = payload.get("mode", "").upper()
        transcription = payload.get("transcription", "")
    elif isinstance(payload, str):
        mode_label = payload.upper().strip()

    if not mode_label:
        print("handle_voice_text: invalid payload:", payload)
        drivers.display_text("Cmd?")
        return

    print("Voice received:", transcription)
    print("Parsed mode:", mode_label)

    # AUTO MODE
    if mode_label == "AUTO_MODE":
        manual_override = False
        sensor_buffer = []
        last_ml_check = 0
        current_state = STATE_HOME
        drivers.display_text("Auto Active")
        return

    # === VALID MANUAL MODES ===
    if mode_label in ("STUDY", "RELAX", "SLEEP", "AWAY"):

        manual_override = True
        current_mode = mode_label
        sensor_buffer = []
        last_ml_check = 0
        current_state = STATE_HOME

        # Read live sensors (for brightness/animation)
        lux1, lux2 = drivers.read_light_sensors()
        lux = (lux1 + lux2) // 2

        n1, n2 = drivers.read_stereo_volume()
        noise = (n1 + n2) // 2

        # Same animation as menu:
        apply_mode_effects(current_mode, lux, noise, animate=True)

        # Update OLED visual feedback
        drivers.display_text(f"{current_mode} Mode")

        print("✔ Voice applied:", current_mode)
        return

    # UNKNOWN MODE
    drivers.display_text("Cmd?")
    print("Unknown voice mode:", mode_label)


def execute_menu_action(index):
    """ Handles Menu Selections. """
    global current_mode, manual_override, current_state, sensor_buffer
    
    # Get the string item from the UI class list
    item = ui.MENU_ITEMS[index]
    print("Selected:", item)
    
    if item == "Auto Mode":
        manual_override = False
        drivers.display_text("Auto Active")
        current_state = STATE_HOME
        sensor_buffer = []
        
    elif item == "Study Mode":
        manual_override = True
        current_mode = "STUDY"
        current_state = STATE_HOME
        lux1, lux2 = drivers.read_light_sensors()
        lux = (lux1 + lux2) // 2
        n1, n2 = drivers.read_stereo_volume()
        noise = (n1 + n2) // 2

        apply_mode_effects(current_mode, lux, noise, animate=True)
        sensor_buffer = []
        
    elif item == "Relax Mode":
        manual_override = True
        current_mode = "RELAX"
        current_state = STATE_HOME
        lux1, lux2 = drivers.read_light_sensors()
        lux = (lux1 + lux2) // 2
        n1, n2 = drivers.read_stereo_volume()
        noise = (n1 + n2) // 2

        apply_mode_effects(current_mode, lux, noise, animate=True)
        sensor_buffer = []
        
    elif item == "Sleep Mode":
        manual_override = True
        current_mode = "SLEEP"
        current_state = STATE_HOME
        lux1, lux2 = drivers.read_light_sensors()
        lux = (lux1 + lux2) // 2
        n1, n2 = drivers.read_stereo_volume()
        noise = (n1 + n2) // 2
        motion = drivers.read_pir_all()
        
        apply_mode_effects(current_mode, lux, noise, animate=True)
        sensor_buffer = []

    elif item == "Away Mode":
        manual_override = True
        current_mode = "AWAY"
        current_state = STATE_HOME
        lux1, lux2 = drivers.read_light_sensors()
        lux = (lux1 + lux2) // 2
        n1, n2 = drivers.read_stereo_volume()
        noise = (n1 + n2) // 2
        
        apply_mode_effects(current_mode, lux, noise, animate=True)
        sensor_buffer = []
        
    elif item == "Set Alarm":
        current_state = STATE_ALARM_SET  # Enter Time Picker UI
        alarm_sys.reset_edit_state()
        
    elif item == "Voice Cmd":
        drivers.display_text("Awaiting Cmd")
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

    # --- Welcome Screen ---
    drivers.display_welcome_screen()
    welcome_tick = 0

    while True:
        btn_idx = input_mgr.check_buttons()   # <-- FIXED
        if btn_idx != -1:
            # Any button: exit welcome, start AURA
            drivers.play_audio_cue("select")
            break
    
        # Flowing rainbow around the ring
        drivers.led_rainbow_flow(welcome_tick)
        welcome_tick = (welcome_tick + 4) & 255  # speed of rotation
        time.sleep(0.05)
    
    # Start background voice listener (always listening)
    try:
        start_server(handle_voice_text)
        print("Voice TCP listener started.")
    except Exception as e:
        print("Failed to start voice listener:", e)
    
    # Determine initial auto mode using current sensors
    motion = drivers.read_pir_all()
    lux1, lux2 = drivers.read_light_sensors()
    lux = (lux1 + lux2) // 2
    v1, v2 = drivers.read_stereo_volume()
    noise = (v1 + v2) // 2

    # Auto mode decides initial logical mode
    current_mode = get_auto_mode()

    # if not manual_override:
    #     motion = drivers.read_pir_all()
    #     send_status_to_server(current_mode)

    # Center-out transition into that mode color
    mode_color = drivers.get_mode_color(current_mode)
    drivers.led_transition_center_out(mode_color, delay=0.025)

    # Immediately draw the home dashboard once so we definitely leave the welcome screen
    ui.draw_home(current_mode, lux, noise)

    while True:
        try:
            # --- 1. SENSE Phase ---
            motion = drivers.read_pir_all()
            lux1, lux2 = drivers.read_light_sensors()
            lux = (lux1 + lux2) // 2
            n1, n2 = drivers.read_stereo_volume()
            noise = (n1 + n2) // 2
            btn_idx = input_mgr.check_buttons()

            lux_diff = abs(int(lux1) - int(lux2))
            noise_diff = abs(int(n1) - int(n2))

            sample = [
                int(lux1),
                int(lux2),
                int(n1),
                int(n2),
                int(motion),
                int(lux_diff),
                int(noise_diff)
            ]
            
            # Update Motion Timer
            if motion:
                last_motion_time = time.ticks_ms()

            # --- 2. ALARM CHECK & RINGING HANDLER ---
            # First, see if it's time to start ringing (one-shot trigger)
            if alarm_sys.check_trigger():
                print("Alarm triggered")

            # If alarm is currently ringing, run continuous beeping & flashing
            if alarm_sys.ringing:
                drivers.display_text("ALARM!!!")
                drivers.led_strip_flow_red(led_flow_tick)
                led_flow_tick += 1

                # Fast, continuous beep (blocking but short)
                drivers.play_tone(2000, 80)  # 80 ms beep

                # ANY physical button press stops it:
                if (
                    btn_idx != -1
                    or drivers.read_raw_button(0)
                    or drivers.read_raw_button(1)
                    or drivers.read_raw_button(2)
                    or drivers.read_raw_button(3)
                ):
                    print("Alarm Dismissed")
                    alarm_sys.stop()
                    drivers.play_audio_cue("back")
                    drivers.display_text("Alarm Off")

                time.sleep(0.02)  # keep this loop tight for animation
                continue

            # --- 3. INPUT HANDLER (Button State Machine) ---
            if btn_idx != -1:
                # Play click sound (Higher pitch for Select)
                drivers.play_audio_cue("select" if btn_idx == 2 else "back")

                if current_state == STATE_HOME:
                    # Only 'Select' (Btn 2) enters Menu.
                    if btn_idx == 2: 
                        current_state = STATE_MENU
                        # Keep previous selection, but show it on the top line
                        ui.top = ui.idx
                        ui.menu_index = ui.idx
                        ui.menu_top_row = ui.top

                elif current_state == STATE_MENU:
                    if btn_idx == 0:
                        ui.scroll_up()      # UP
                    elif btn_idx == 1:
                        ui.scroll_down()    # DOWN
                    elif btn_idx == 3:
                        current_state = STATE_HOME  # BACK
                    elif btn_idx == 2:  # SELECT
                        execute_menu_action(ui.idx)

                elif current_state == STATE_ALARM_SET:
                    if btn_idx == 0:
                        alarm_sys.increment_time()  # UP
                    elif btn_idx == 1:
                        alarm_sys.decrement_time()  # DOWN
                    elif btn_idx == 2:  # SELECT
                        if alarm_sys.edit_mode_hour:
                            alarm_sys.toggle_edit_field()  # Move to minute
                        else:
                            alarm_sys.enabled = True  # Save & enable
                            drivers.display_text("Alarm Saved!")
                            time.sleep(1)
                            current_state = STATE_HOME
                            alarm_sys.reset_edit_state()
                    elif btn_idx == 3:  # BACK
                        current_state = STATE_MENU

                time.sleep(0.2)  # extra debounce

            # --- 4. THINK & ACT (Core Logic) ---
            new_mode = get_auto_mode()

            if new_mode != current_mode and not manual_override:
                drivers.play_audio_cue("mode_switch")
                apply_mode_effects(new_mode, lux, noise, animate=True)
                current_mode = new_mode
            else:
                if not alarm_sys.ringing and current_state == STATE_HOME:
                    apply_mode_effects(current_mode, lux, noise, animate=False)

            # --- OLED RENDERING ONLY ---
            if not alarm_sys.ringing:
                if current_state == STATE_HOME:
                    ui.draw_home(current_mode, lux, noise)
                elif current_state == STATE_MENU:
                    ui.draw_menu()
                elif current_state == STATE_ALARM_SET:
                    ui.draw_alarm_set(alarm_sys)

            # --- 5. CLOUD SYNC (build ML window) ---
            if time.ticks_diff(time.ticks_ms(), last_cloud_update) > SAMPLE_INTERVAL_MS:

                # 1. Append one sensor reading
                sensor_buffer.append(sample)

                # Trim BEFORE printing
                if len(sensor_buffer) > WINDOW_SIZE:
                    sensor_buffer.pop(0)

                print("Collected sample:", len(sensor_buffer), "/", WINDOW_SIZE)


                # 3. If manual mode AND window full → send to server
                if manual_override and len(sensor_buffer) == WINDOW_SIZE:
                    send_status_to_server(current_mode)

                last_cloud_update = time.ticks_ms()

            time.sleep(0.05) 
            gc.collect()

        except Exception as e:
            # Don't kill the whole app on a single error; just log it.
            print("Main loop error:", e)
            time.sleep(0.2)

if __name__ == "__main__":
    main()






