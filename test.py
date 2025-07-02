import JSON


def get_device_location_by_ip(deviceIP):
    if os.path.exists('appSettings.json'):
        with open('appSettings.json', 'r') as f:
            data = json.load(f)
    for device in data.get("devices", []):
        if device.get("ip") == deviceIP:
            return device.get("location", "Location not found")
    return "Device with this IP not found"

get_device_location_by_ip(deviceIP)