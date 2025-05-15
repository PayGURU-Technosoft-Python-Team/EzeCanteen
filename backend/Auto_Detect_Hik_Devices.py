import requests
from requests.auth import HTTPDigestAuth
import re
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_subnet():
    """Get current subnet automatically"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return '.'.join(ip.split('.')[:-1])

def check_device(ip, user="admin", pwd="a1234@4321"):
    """Check if IP is a Hikvision device"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        if sock.connect_ex((ip, 80)) != 0:
            sock.close()
            return None
        sock.close()
        
        r = requests.get(f"http://{ip}/ISAPI/System/deviceinfo", 
                       auth=HTTPDigestAuth(user, pwd), timeout=2)
        
        if r.status_code == 200 and 'DeviceInfo' in r.text:
            model = re.search(r'<model>(.*?)</model>', r.text)
            name = re.search(r'<deviceName>(.*?)</deviceName>', r.text)
            
            print(f"✓ {ip} - {model.group(1) if model else 'Unknown'} - {name.group(1) if name else 'Unknown'}")
            
            with open(f'device_{ip.replace(".", "_")}.xml', 'w') as f:
                f.write(r.text)
            
            return ip
    except:
        pass
    return None

def scan(subnet=None):
    """Scan network for Hikvision devices"""
    # Use provided subnet or auto-detect
    if not subnet:
        subnet = get_subnet()
    
    print(f"Scanning: {subnet}.0/24")
    
    # Generate IPs
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    found = []
    
    # Parallel scan
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_device, ip) for ip in ips]
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
    
    print(f"\nFound {len(found)} devices")
    return found

# Run with optional subnet argument
if __name__ == "__main__":
    subnet = sys.argv[1] if len(sys.argv) > 1 else None
    scan(subnet)