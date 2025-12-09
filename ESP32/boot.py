import network
import time
from machine import Pin

led = Pin(2, Pin.OUT)
led.value(1)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to network...')
        # Make sure to replace with your actual credentials!
        # wlan.connect('YOUR_WIFI_SSID', 'YOUR_WIFI_PASSWORD')
        wlan.connect('Columbia University')
        max_retries = 20
        while not wlan.isconnected() and max_retries > 0:
            led.value(not led.value())
            time.sleep(0.5)
            max_retries -= 1
            
    if wlan.isconnected():
        print('Network config:', wlan.ifconfig())
         # LED off when connected
        led.value(0)
        # Blink twice to confirm
        for _ in range(2):
            led.value(1)
            time.sleep(0.1)
            led.value(0)
            time.sleep(0.1)
    else:
        print('WiFi Connection Failed!')

connect_wifi()