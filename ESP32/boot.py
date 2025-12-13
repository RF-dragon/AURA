# boot.py - Early Wi-Fi behavior
#
# Policy:
# - Try saved networks first.
# - If none connect, start a captive-ish config AP so the user can provision SSID/password.

import wifi_manager

if not wifi_manager.try_connect_saved():
    wifi_manager.start_config_ap()
