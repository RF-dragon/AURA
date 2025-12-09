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
PIN_MIC_SCK1 = 14
PIN_MIC_WS1 = 15
PIN_MIC_SD1 = 32

# Mic 2 (Right)
PIN_MIC_SCK2 = 12
PIN_MIC_WS2 = 13 
PIN_MIC_SD2 = 4

# =========================================
#            GLOBAL OBJECTS
# =========================================
oled = None
np = None
i2s_mic1 = None
i2s_mic2 = None
buzzer_pwm = None
pir_front = None
btns = []
i2c = None

# Constants
NUM_LEDS = 144       # 1m 144LEDs/m Strip
BH1750_ADDR_1 = 0x23 # Right Sensor
BH1750_ADDR_2 = 0x5C # Left Sensor

def init_hardware():
    global oled, np, i2s_mic1, i2s_mic2, pir_front, btns, buzzer_pwm, i2c
    
    print("Initializing Hardware...")
    
    # 1. I2C Bus & OLED
    try:
        i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA))
        # Wake up light sensors
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
        config = {'bits': 16, 'format': I2S.MONO, 'rate': 16000, 'ibuf': 4096}
        i2s_mic1 = I2S(0, sck=Pin(PIN_MIC_SCK1), ws=Pin(PIN_MIC_WS1), sd=Pin(PIN_MIC_SD1), mode=I2S.RX, **config)
        i2s_mic2 = I2S(1, sck=Pin(PIN_MIC_SCK2), ws=Pin(PIN_MIC_WS2), sd=Pin(PIN_MIC_SD2), mode=I2S.RX, **config)
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
    f = pir_front.value()
    return {
        "front": f,
        "any": f 
    }

def read_raw_button(index):
    return btns[index].value() == 0

def read_light_sensors():
    total_lux = 0
    count = 0
    for addr in [BH1750_ADDR_1, BH1750_ADDR_2]:
        try:
            data = i2c.readfrom(addr, 2)
            lux = (data[0] << 8 | data[1]) / 1.2
            total_lux += lux
            count += 1
        except: pass
    if count == 0: return 0
    return int(total_lux / count)

def read_mic_volume():
    """ Returns tuple (vol_mic1, vol_mic2) """
    def get_rms(mic):
        if not mic: return 0
        buf = bytearray(1024)
        mic.readinto(buf)
        total = 0
        for i in range(0, len(buf), 2):
            sample = int.from_bytes(buf[i:i+2], 'little')
            if sample > 32768: sample -= 65536
            total += sample * sample
        return math.sqrt(total / (len(buf)//2))
    
    return get_rms(i2s_mic1), get_rms(i2s_mic2)

def get_datetime():
    # Returns (year, month, day, hour, minute, second)
    # Adjust -18000 (5 hours) for EST 
    return time.localtime(time.time() - 18000)

def get_current_time():
    # Returns "HH:MM" string for main.py
    t = get_datetime()
    return "{:02d}:{:02d}".format(t[3], t[4])

# =========================================
#          ACTUATOR FUNCTIONS
# =========================================

def led_strip_solid(color, brightness=255):
    factor = brightness / 255.0
    c = (int(color[0]*factor), int(color[1]*factor), int(color[2]*factor))
    np.fill(c)
    np.write()

def led_strip_rainbow():
    colors = [(255,0,0), (255,127,0), (255,255,0), (0,255,0), (0,0,255), (75,0,130), (148,0,211)]
    for c in colors:
        np.fill(c)
        np.write()
        time.sleep(0.02)
    led_strip_off()

def led_strip_off():
    np.fill((0,0,0))
    np.write()

def led_strip_flash(color):
    for _ in range(3):
        np.fill(color); np.write(); time.sleep(0.1)
        np.fill((0,0,0)); np.write(); time.sleep(0.1)

def led_strip_flow_red(offset):
    """ Animated red flow for Alarm """
    np.fill((0,0,0))
    for i in range(15): # Flow width
        idx = (offset + i) % NUM_LEDS
        np[idx] = (255, 0, 0)
    np.write()

def led_startup_animation():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for color in colors:
        for i in range(0, NUM_LEDS, 2): 
            np[i] = color
            if i+1 < NUM_LEDS: np[i+1] = color
            np.write()
    led_strip_off()

# =========================================
#          DISPLAY FUNCTIONS
# =========================================

def display_text(text):
    """ Helper to show text on OLED """
    if oled:
        oled.fill(0)
        oled.text(text, 0, 10)
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
    elif name == "status_report": play_tone(800, 100); time.sleep(0.1); play_tone(800, 100)

def record_audio(duration=3):
    rate = 8000
    buf = bytearray(rate * 2 * duration)
    try:
        i2s_mic1.init(rate=rate)
        i2s_mic1.readinto(buf)
        i2s_mic1.init(rate=16000) # Restore
    except: pass
    return buf
