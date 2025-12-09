# drivers.py - Hardware Abstraction Layer
import machine
import time
import neopixel
import ssd1306
from machine import I2S, Pin, I2C, PWM, RTC
import ntptime 

# =========================================
#            PIN CONFIGURATION
# =========================================

# --- I2C Bus (Shared by OLED and Light Sensors) ---
PIN_SDA = 21
PIN_SCL = 22

# --- Outputs ---
PIN_LED_STRIP = 26   # NeoPixel Data Pin
PIN_BUZZER = 25     # Passive Buzzer (PWM)

# --- Inputs (Buttons) ---
# All mapped to pins that support Internal Pull-ups (Active LOW)
PIN_BTN_LEFT = 33   # Function: Scroll Up / Volume Up
PIN_BTN_MID_L = 27  # Function: Scroll Down / Volume Down
PIN_BTN_MID_R = 18  # Function: Select / Enter
PIN_BTN_RIGHT = 5   # Function: Back / Cancel

# --- Inputs (PIR Motion Sensors) ---
PIN_PIR_FRONT = 23
PIN_PIR_RIGHT = 26
PIN_PIR_LEFT = 19

# --- Microphone (I2S Bus) ---
PIN_MIC_SCK1 = 14
PIN_MIC_SCK2 = 12    # Bit Clock
PIN_MIC_WS1 = 15     # Word Select (Left/Right Clock)
PIN_MIC_WS2 = 13
PIN_MIC_SD1 = 32     # Serial Data In
PIN_MIC_SD2 = 4

# =========================================
#            GLOBAL OBJECTS
# =========================================
oled = None
np = None
i2s_mic = None
buzzer_pwm = None
pir_front = None
pir_right = None
pir_left = None
btns = []
i2c = None

# BH1750 Addresses
BH1750_ADDR_1 = 0x23 
BH1750_ADDR_2 = 0x5C 

# TIMEZONE OFFSET (Hours from UTC)
# Change this to match your location (e.g., -5 for EST, -4 for EDT)
TIMEZONE_OFFSET = -5 

def init_hardware():
    global oled, np, i2s_mic, pir_front, pir_right, pir_left, btns, buzzer_pwm, i2c
    
    print("Initializing Hardware...")
    
    # 1. I2C Bus & OLED
    try:
        i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA))
        # Wake up sensors
        try: i2c.writeto(BH1750_ADDR_1, b'\x10')
        except: pass
        try: i2c.writeto(BH1750_ADDR_2, b'\x10')
        except: pass

        oled = ssd1306.SSD1306_I2C(128, 32, i2c)
        oled.fill(0)
        oled.text("AURA Booting...", 0, 0)
        oled.show()
    except Exception as e:
        print("I2C Error:", e)

    # 2. NeoPixel
    np = neopixel.NeoPixel(Pin(PIN_LED_STRIP), 8)
    led_strip_off()

    # 3. Sensors
    pir_front = Pin(PIN_PIR_FRONT, Pin.IN)
    pir_right = Pin(PIN_PIR_RIGHT, Pin.IN)
    pir_left = Pin(PIN_PIR_LEFT, Pin.IN)

    # 4. Buttons
    btns = [
        Pin(PIN_BTN_LEFT, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_MID_L, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_MID_R, Pin.IN, Pin.PULL_UP),
        Pin(PIN_BTN_RIGHT, Pin.IN, Pin.PULL_UP)
    ]
    
    # 5. Buzzer
    buzzer_pwm = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)

    # 6. Microphone
    try:
        i2s_mic = I2S(1, sck=Pin(PIN_MIC_SCK), ws=Pin(PIN_MIC_WS), sd=Pin(PIN_MIC_SD),
                  mode=I2S.RX, bits=16, format=I2S.STD, rate=8000, ibuf=20000)
    except Exception as e:
        print("Mic Init Error:", e)
        
    # 7. Time Sync
    try:
        ntptime.settime()
        print("Time Synced")
    except:
        print("Time Sync Failed")

    print("Hardware Ready.")

# ---- Sensor Functions -----
def read_pir_all():
    return {
        "front": pir_front.value(),
        "right": pir_right.value(),
        "left": pir_left.value(),
        "any": pir_front.value() or pir_right.value() or pir_left.value()
    }

def read_raw_button(index):
    # Returns True if pressed (Active Low)
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
    samples = bytearray(512) 
    try:
        num_read = i2s_mic.readinto(samples)
        total = 0
        for i in range(0, num_read, 2):
            sample = int.from_bytes(samples[i:i+2], 'little')
            if sample > 32768: sample -= 65536
            total += abs(sample)
        return (total / (num_read/2)) * 5 
    except:
        return 0

def get_datetime():
    """ Returns (year, month, day, hour, minute, second) adjusted for timezone """
    t = time.localtime(time.time() + (TIMEZONE_OFFSET * 3600))
    return t[0], t[1], t[2], t[3], t[4], t[5]

# ----- Actuator Functions -----
def led_strip_solid(color, brightness=255):
    factor = brightness / 255.0
    r = int(color[0] * factor)
    g = int(color[1] * factor)
    b = int(color[2] * factor)
    np.fill((r, g, b))
    np.write()

def led_strip_rainbow():
    colors = [(255,0,0), (255,127,0), (255,255,0), (0,255,0), (0,0,255), (75,0,130), (148,0,211)]
    for color in colors:
        np.fill(color)
        np.write()
        time.sleep(0.05)
    led_strip_off()

def led_startup_animation():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for color in colors:
        for i in range(8):
            np[i] = color
            np.write()
            time.sleep(0.05)
    led_strip_off()

def led_strip_off():
    np.fill((0,0,0))
    np.write()

def led_strip_flash(color):
    for _ in range(3):
        np.fill(color)
        np.write()
        time.sleep(0.1)
        np.fill((0,0,0))
        np.write()
        time.sleep(0.1)

def led_strip_flow_red(offset):
    """ Creates a flowing red line effect for Alarm """
    np.fill((0,0,0))
    # Light up 3 pixels in a row, shifting by offset
    for i in range(3):
        idx = (offset + i) % 8
        np[idx] = (255, 0, 0)
    np.write()

# ----- Audio Functions -----
def play_tone(freq, duration_ms):
    if buzzer_pwm:
        buzzer_pwm.freq(freq)
        buzzer_pwm.duty(512)
        time.sleep_ms(duration_ms)
        buzzer_pwm.duty(0)

def play_audio_cue(cue_name):
    if cue_name == "startup":
        play_tone(1000, 100)
        play_tone(2000, 100)
    elif cue_name == "mode_switch":
        play_tone(1500, 100)
    elif cue_name == "select":
        play_tone(2000, 50)
    elif cue_name == "back":
        play_tone(500, 50)
    elif cue_name == "alarm":
        play_tone(2000, 200)

def record_audio(duration=3):
    rate = 8000 
    buf = bytearray(rate * 2 * duration)
    try:
        i2s_mic.readinto(buf)
    except:
        pass
    return buf