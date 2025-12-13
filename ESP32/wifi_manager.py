# wifi_manager.py - Wi-Fi provisioning for AURA (MicroPython)
#
# Flow:
# 1) try_connect_saved(): iterate networks.json entries and connect to the first that succeeds.
# 2) start_config_ap(): start AP + minimal HTTP form to save SSID/password into networks.json.

import network, json, time, socket

CONFIG_FILE = "networks.json"

def load_networks():
    """Load list of saved networks from CONFIG_FILE; returns [] if missing/corrupt."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("networks", [])
    except:
        return []

def save_networks(networks):
    """Persist networks as {"networks":[{ssid,password}, ...]}."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"networks": networks}, f)

def try_connect_saved():
    """
    Try STA connections using saved credentials.

    Returns True on first successful connection, else False.
    Notes:
    - Uses short interface resets between attempts to improve reliability.
    - Treats blank password as OPEN network.
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    networks = load_networks()
    for entry in networks:
        ssid = entry["ssid"]
        password = entry["password"]

        print("Trying:", ssid)

        try:
            sta.disconnect()
        except:
            pass

        # Small reset cycle helps on some ESP32 builds.
        sta.active(False)
        time.sleep(0.2)
        sta.active(True)
        time.sleep(0.2)

        if not password or password.strip() == "":
            print("Connecting OPEN network:", ssid)
            sta.connect(ssid)
        else:
            print("Connecting WPA/WPA2 network:", ssid)
            sta.connect(ssid, password)

        # Wait up to ~10 seconds total.
        for _ in range(20):
            if sta.isconnected():
                print("Connected to:", ssid)
                ip = sta.ifconfig()[0]
                print("ESP32 IP Address:", ip)
                return True
            time.sleep(0.5)

        print("Failed:", ssid)

    return False

def start_config_ap():
    """
    Start an AP + provisioning page.
    User connects to SSID 'ESP32-Setup' and visits http://192.168.4.1 to save credentials.
    """
    print("Starting config AP...")
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32-Setup", password="12345678")

    print("Connect to WiFi ESP32-Setup, then open http://192.168.4.1")
    run_web_server()

def run_web_server():
    """Minimal blocking HTTP server for SSID/password form submit."""
    html = '''
<html>
<head><title>ESP32 WiFi Setup</title></head>
<body>
<h2>Configure WiFi</h2>
<form method="POST">
  SSID:<br><input name="ssid"><br>
  Password:<br><input name="password"><br>
  <button type="submit">Save</button>
</form>
</body>
</html>
'''

    s = socket.socket()
    s.bind(("0.0.0.0", 80))
    s.listen(1)

    while True:
        conn, addr = s.accept()
        req = conn.recv(1024).decode()

        if "POST" in req:
            # Basic form parse: body is "ssid=...&password=..."
            body = req.split("\r\n\r\n")[1]
            params = dict(x.split("=") for x in body.split("&"))

            ssid = params.get("ssid").replace("+", " ")
            password = params.get("password")

            networks = load_networks()
            networks.append({"ssid": ssid, "password": password})
            save_networks(networks)

            conn.send("HTTP/1.1 200 OK\r\n\r\nSaved! Reboot ESP32.")
        else:
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html)

        conn.close()
