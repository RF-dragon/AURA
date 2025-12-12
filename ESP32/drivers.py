# drivers.py - Hardware Abstraction Layer for AURA
import machine
import math
import time
import neopixel
import ssd1306
from machine import I2S, Pin, I2C, PWM, RTC
import ntptime

# =========================================
#            PIN CONFIGURATION
# =========================================

# --- I2C Bus ---
PIN_SDA = 21
PIN_SCL = 22

# --- Outputs ---
PIN_LED_STRIP = 26   # NeoPixel Data
PIN_BUZZER = 25      # Passive Buzzer

# --- Inputs (Buttons) ---
PIN_BTN_LEFT = 33    # Scroll Up
PIN_BTN_MID_L = 27   # Scroll Down
PIN_BTN_MID_R = 18   # Select
PIN_BTN_RIGHT = 5    # Back

# --- Inputs (PIR Motion Sensor) ---
PIN_PIR_FRONT = 23

# --- Microphones (Dual I2S) ---
# Mic 1 (Left)
PIN_MIC1_SCK = 14
PIN_MIC1_WS = 15
PIN_MIC1_SD = 32

# Mic 2 (Right)
PIN_MIC2_SCK = 14
PIN_MIC2_WS = 15 
PIN_MIC2_SD = 4

# =========================================
#            GLOBAL OBJECTS
# =========================================
oled = None
np = None
# i2s_mic1 = None
# i2s_mic2 = None
i2s_mics = None
buzzer_pwm = None
pir_front = None
btns = []
i2c = None

# Constants
NUM_LEDS = 40        
BH1750_ADDR_1 = 0x23 # Right Sensor
BH1750_ADDR_2 = 0x5C # Left Sensor

# Global brightness scaling (0.0–1.0)
GLOBAL_BRIGHTNESS = 0.55


def init_hardware():
    global oled, np, i2s_mics, pir_front, btns, buzzer_pwm, i2c
    
    print("Initializing Hardware...")
    
    # 1. I2C Bus
    try:
        i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA))
        # Wake up sensors
        try: i2c.writeto(BH1750_ADDR_1, b'\x10'); i2c.writeto(BH1750_ADDR_2, b'\x10')
        except: pass
        oled = ssd1306.SSD1306_I2C(128, 32, i2c)
        oled.fill(0); oled.text("AURA Booting...", 0, 0); oled.show()
    except Exception as e: print("I2C Error:", e)

    # 2. LED Strip
    np = neopixel.NeoPixel(Pin(PIN_LED_STRIP), NUM_LEDS)
    led_strip_off()

    # 3. PIR Sensor
    pir_front = Pin(PIN_PIR_FRONT, Pin.IN)

    # 4. Buttons
    btns = [
        Pin(PIN_BTN_LEFT, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_MID_L, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_MID_R, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_RIGHT, Pin.IN, Pin.PULL_UP)
    ]
    
    # 5. Buzzer
    buzzer_pwm = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)

    # 6. Microphones
    try:
        # Mic1 – main recording mic (I2S1) – using your proven-good config
        i2s_mics = I2S(
            0,
            sck=Pin(PIN_MIC1_SCK),
            ws=Pin(PIN_MIC1_WS),
            sd=Pin(PIN_MIC1_SD),   # IMPORTANT: only SD1 connected here
            mode=I2S.RX,
            bits=32,               # because stereo 16-bit + 16-bit
            format=I2S.STEREO,
            rate=16000,
            ibuf=4096
        )

    except Exception as e: print("Mic Init Error:", e)

    # 7. Time Sync
    try: ntptime.settime()
    except: pass

    print("Hardware Ready.")

# =========================================
#          SENSOR FUNCTIONS
# =========================================

def read_pir_all():
    """ Returns state of PIR (Simplified for single sensor) """
    return pir_front.value()

def read_raw_button(index):
    return btns[index].value() == 0

def read_light_sensors():
    """Returns: (lux_left, lux_right)"""

    lux_left = None
    lux_right = None

    # Left sensor (BH1750_ADDR_2 = 0x5C)
    try:
        data = i2c.readfrom(BH1750_ADDR_2, 2)
        lux_left = (data[0] << 8 | data[1]) / 1.2
    except:
        lux_left = 0

    # Right sensor (BH1750_ADDR_1 = 0x23)
    try:
        data = i2c.readfrom(BH1750_ADDR_1, 2)
        lux_right = (data[0] << 8 | data[1]) / 1.2
    except:
        lux_right = 0

    return int(lux_left), int(lux_right)


def read_stereo_volume():
    """Returns RMS audio volume: (sound_left, sound_right)"""

    buf = bytearray(1024)
    n = i2s_mics.readinto(buf)
    if not n:
        return 0, 0

    left_sq = 0
    right_sq = 0
    samples = n // 4   # 2 bytes left + 2 bytes right

    for i in range(0, n, 4):
        # 16-bit signed
        left  = int.from_bytes(buf[i:i+2], 'little')
        right = int.from_bytes(buf[i+2:i+4], 'little')

        left_sq  += left * left
        right_sq += right * right

    rms_left = (left_sq // samples) ** 0.5
    rms_right = (right_sq // samples) ** 0.5

    return rms_left, rms_right


def get_datetime():
    # Returns (year, month, day, hour, minute, second)
    # Adjust -18000 (5 hours) for EST 
    return time.localtime(time.time() - 18000)

def get_current_time():
    """ Returns HH:MM string for main.py """
    t = get_datetime()
    return "{:02d}:{:02d}".format(t[3], t[4])

# =========================================
#          ACTUATOR FUNCTIONS
# =========================================

def _scale_color_tuple(color, extra_factor=1.0):
    """
    Applies global brightness + an extra factor (0.0–1.0).
    Returns a scaled (r,g,b) tuple.
    """
    factor = GLOBAL_BRIGHTNESS * extra_factor
    r = int(color[0] * factor)
    g = int(color[1] * factor)
    b = int(color[2] * factor)
    # Clamp to [0,255]
    r = 0 if r < 0 else (255 if r > 255 else r)
    g = 0 if g < 0 else (255 if g > 255 else g)
    b = 0 if b < 0 else (255 if b > 255 else b)
    return (r, g, b)

def led_strip_solid(color, brightness=255):
    if np is None:
        return
    extra = brightness / 255.0            # per-call scaling
    c = _scale_color_tuple(color, extra_factor=extra)
    np.fill(c)
    np.write()

def led_strip_rainbow():
    if np is None:
        return
    colors = [
        (255, 0, 0),
        (255, 127, 0),
        (255, 255, 0),
        (0, 255, 0),
        (0, 0, 255),
        (75, 0, 130),
        (148, 0, 211)
    ]
    for c in colors:
        np.fill(_scale_color_tuple(c))
        np.write()
        time.sleep(0.02)
    led_strip_off()

def led_strip_off():
    if np is None:
        return
    np.fill((0, 0, 0))
    np.write()

def led_strip_flash(color):
    if np is None:
        return
    for _ in range(3):
        np.fill(_scale_color_tuple(color))
        np.write()
        time.sleep(0.1)
        np.fill((0, 0, 0))
        np.write()
        time.sleep(0.1)

def led_strip_flow_red(offset):
    """Animated red flow for Alarm."""
    if np is None:
        return
    np.fill((0, 0, 0))
    base = (255, 0, 0)
    c = _scale_color_tuple(base)
    for i in range(15):
        idx = (offset + i) % NUM_LEDS
        np[idx] = c
    np.write()

def led_startup_animation():
    if np is None:
        return
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for color in colors:
        c = _scale_color_tuple(color, extra_factor=0.8)
        for i in range(0, NUM_LEDS, 2):
            np[i] = c
            if i + 1 < NUM_LEDS:
                np[i + 1] = c
            np.write()
    led_strip_off()

# =========================================
#      ADVANCED LED ANIMATION HELPERS
# =========================================

def _color_wheel(pos):
    """Color wheel helper: pos 0-255 -> (r,g,b)."""
    pos &= 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def led_rainbow_flow(offset=0):
    if np is None:
        return
    for i in range(NUM_LEDS):
        raw = _color_wheel((i * 256 // NUM_LEDS + offset) & 255)
        np[i] = _scale_color_tuple(raw)
    np.write()

def led_transition_center_out(color, delay=0.04):
    if np is None:
        return

    np.fill((0, 0, 0))
    np.write()

    center_left = (NUM_LEDS - 1) // 2
    center_right = NUM_LEDS // 2

    c = _scale_color_tuple(color)

    for step in range(center_left + 1):
        left = center_left - step
        right = center_right + step
        if left >= 0:
            np[left] = c
        if right < NUM_LEDS:
            np[right] = c
        np.write()
        time.sleep(delay)

def get_mode_color(mode):
    mapping = {
        "STUDY": (120, 170, 230),   # cool light blue
        "RELAX": (255, 80, 0),      # sunset orange
        "AWAY":  (180, 80, 200),    # purple
        "SLEEP": (255, 140, 50),    # dim amber
        "ALERT": (255, 40, 40),     # red
    }
    return mapping.get(mode, (200, 200, 200))

# =========================================
#          DISPLAY FUNCTIONS
# =========================================

def display_text(text):
    """ Helper to show text on OLED """
    if oled:
        oled.fill(0)
        oled.text(text, 0, 10)
        oled.show()

def display_welcome_screen():
    """Draw a simple welcome page on the 128x32 OLED."""
    global oled
    if oled is None:
        return

    oled.fill(0)
    oled.text("Hello!", 32, 0)
    oled.text("Press any button", 0, 12)
    oled.text("to start AURA", 0, 24)
    oled.show()

def update_oled(mode, lux, noise):
    """ Dashboard update helper for main.py """
    if oled:
        oled.fill(0)
        oled.text(f"Mode: {mode}", 0, 0)
        oled.text(f"Lux: {lux}", 0, 10)
        oled.text(f"Vol: {int(noise)}", 0, 20)
        oled.show()
        
def draw_menu(items, selected_index, start_row):
    """ Draws the menu list """
    if not oled: return
    oled.fill(0)
    for i in range(3): 
        item_idx = start_row + i
        if item_idx < len(items):
            prefix = ">" if item_idx == selected_index else " "
            oled.text(f"{prefix} {items[item_idx]}", 0, i * 10)
    oled.show()

def draw_alarm_ui(hour, minute, setting_hour):
    """ Draws the Alarm Setting UI """
    if not oled: return
    oled.fill(0)
    oled.text("Set Alarm:", 0, 0)
    h_str = f">{hour:02d}<" if setting_hour else f"{hour:02d}"
    m_str = f">{minute:02d}<" if not setting_hour else f"{minute:02d}"
    oled.text(f"{h_str} : {m_str}", 20, 12)
    oled.text("UP/DN | SEL=Next", 0, 24)
    oled.show()

# =========================================
#          AUDIO FUNCTIONS
# =========================================

def play_tone(freq, duration_ms):
    buzzer_pwm.freq(freq)
    buzzer_pwm.duty(512)
    time.sleep_ms(duration_ms)
    buzzer_pwm.duty(0)

def play_audio_cue(name):
    if name == "startup": play_tone(1000, 100); play_tone(2000, 100)
    elif name == "mode_switch": play_tone(1500, 100)
    elif name == "select": play_tone(2000, 50)
    elif name == "back": play_tone(500, 50)
    elif name == "alarm": play_tone(2000, 200)




