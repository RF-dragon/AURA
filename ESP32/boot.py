import wifi_manager

if not wifi_manager.try_connect_saved():
    wifi_manager.start_config_ap()

