import requests
from requests.auth import HTTPDigestAuth
import re
import socket
import sys
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class HikvisionScanner:
    def __init__(self, username="admin", password="a1234@4321"):
        self.username = username
        self.password = password
        self.auth = HTTPDigestAuth(username, password)
    
    def get_subnet(self):
        """Get current subnet automatically"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return '.'.join(ip.split('.')[:-1])
    
    def check_device(self, ip):
        """Check if IP is a Hikvision device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            if sock.connect_ex((ip, 80)) != 0:
                sock.close()
                return None
            sock.close()
            
            r = requests.get(f"http://{ip}/ISAPI/System/deviceinfo", 
                           auth=self.auth, timeout=2)
            
            if r.status_code == 200 and 'DeviceInfo' in r.text:
                model = re.search(r'<model>(.*?)</model>', r.text)
                name = re.search(r'<deviceName>(.*?)</deviceName>', r.text)
                serial = re.search(r'<serialNumber>(.*?)</serialNumber>', r.text)
                
                device_info = {
                    'ip': ip,
                    'model': model.group(1) if model else 'Unknown',
                    'name': name.group(1) if name else 'Unknown',
                    'serial': serial.group(1) if serial else 'Unknown',
                    'basic_info': r.text
                }
                
                print(f"✓ {ip} - {device_info['model']} - {device_info['name']}")
                return device_info
        except:
            pass
        return None
    
    def get_capabilities(self, ip):
        """Get device capabilities"""
        capabilities = {
            'max_users': None,
            'max_cards': None,
            'max_faces': None,
            'max_fingerprints': None,
            'fingerprint_supported': False,
            'fingerprints_per_user': 0
        }
        
        # Get user management capability
        try:
            r = requests.get(f"http://{ip}/ISAPI/AccessControl/UserInfo/capabilities?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'UserInfo' in data:
                    capabilities['max_users'] = data['UserInfo'].get('maxRecordNum', None)
        except:
            pass
        
        # Get card management capability
        try:
            r = requests.get(f"http://{ip}/ISAPI/AccessControl/CardInfo/capabilities?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'CardInfo' in data:
                    capabilities['max_cards'] = data['CardInfo'].get('maxRecordNum', None)
        except:
            pass
        
        # Get face library capability
        try:
            r = requests.get(f"http://{ip}/ISAPI/Intelligent/FDLib/capabilities?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                capabilities['max_faces'] = data.get('FDRecordDataMaxNum', None)
        except:
            pass
        
        # Get fingerprint capability
        try:
            r = requests.get(f"http://{ip}/ISAPI/AccessControl/CaptureFingerPrint/capabilities",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                finger_nos = root.findall('.//{http://www.isapi.org/ver20/XMLSchema}fingerNo')
                if finger_nos:
                    capabilities['fingerprint_supported'] = True
                    capabilities['fingerprints_per_user'] = int(finger_nos[0].get('max', 0))
                    # Calculate max fingerprints (max users * fingerprints per user)
                    if capabilities['max_users']:
                        capabilities['max_fingerprints'] = capabilities['max_users'] * capabilities['fingerprints_per_user']
            else:
                capabilities['fingerprint_supported'] = False
        except:
            pass
        
        return capabilities
    
    def get_counts(self, ip):
        """Get current counts of enrolled users, cards, faces, and fingerprints"""
        counts = {
            'total_users': 0,
            'total_cards': 0,
            'total_faces': 0,
            'users_with_cards': 0,
            'users_with_faces': 0,
            'users_with_fingerprints': 0,
            'total_fingerprints': 0
        }
        
        # Get user count
        try:
            r = requests.get(f"http://{ip}/ISAPI/AccessControl/UserInfo/Count?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'UserInfoCount' in data:
                    counts['total_users'] = data['UserInfoCount'].get('userNumber', 0)
                    counts['users_with_cards'] = data['UserInfoCount'].get('bindCardUserNumber', 0)
                    counts['users_with_faces'] = data['UserInfoCount'].get('bindFaceUserNumber', 0)
        except:
            pass
        
        # Get card count
        try:
            r = requests.get(f"http://{ip}/ISAPI/AccessControl/CardInfo/Count?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'CardInfoCount' in data:
                    counts['total_cards'] = data['CardInfoCount'].get('cardNumber', 0)
        except:
            pass
        
        # Get face count
        try:
            r = requests.get(f"http://{ip}/ISAPI/Intelligent/FDLib/Count?format=json",
                           auth=self.auth, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'FDRecordDataInfo' in data:
                    total_faces = 0
                    for fd_info in data['FDRecordDataInfo']:
                        total_faces += int(fd_info.get('recordDataNumber', 0))
                    counts['total_faces'] = total_faces
        except:
            pass
        
        return counts
    
    def get_all_users_with_pagination(self, ip):
        """Get all users using pagination"""
        all_users = []
        total_fingerprints = 0
        search_position = 0
        max_results = 30
        
        while True:
            try:
                url = f'http://{ip}/ISAPI/AccessControl/UserInfo/Search?format=json'
                payload = {
                    "UserInfoSearchCond": {
                        "searchID": "1",
                        "searchResultPosition": search_position,
                        "maxResults": max_results,
                    }
                }
                
                response = requests.post(url, json=payload, auth=self.auth, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "UserInfoSearch" in data:
                        user_list = data["UserInfoSearch"].get("UserInfo", [])
                        
                        if not user_list:
                            break
                        
                        # Process users and count fingerprints
                        for user in user_list:
                            all_users.append(user)
                            total_fingerprints += user.get('numOfFP', 0)
                        
                        # Check if we got all users
                        if len(user_list) < max_results:
                            break
                        
                        # Move to next page
                        search_position += max_results
                    else:
                        break
                else:
                    break
            except Exception as e:
                print(f"Error fetching users from {ip}: {e}")
                break
        
        return all_users, total_fingerprints
    
    def scan_and_analyze(self, subnet=None):
        """Scan network for Hikvision devices and analyze their capabilities"""
        if not subnet:
            subnet = self.get_subnet()
        
        print(f"Scanning: {subnet}.0/24")
        print("-" * 50)
        
        # Generate IPs
        ips = [f"{subnet}.{i}" for i in range(1, 255)]
        devices = []
        
        # Parallel device discovery
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(self.check_device, ip) for ip in ips]
            for future in as_completed(futures):
                device = future.result()
                if device:
                    devices.append(device)
        
        print(f"\nFound {len(devices)} devices")
        print("-" * 50)
        
        # Analyze each device
        results = []
        for device in devices:
            ip = device['ip']
            print(f"\nAnalyzing {ip} - {device['model']}")
            
            # Get capabilities
            capabilities = self.get_capabilities(ip)
            
            # Get current counts
            counts = self.get_counts(ip)
            
            # Get all users and count fingerprints
            all_users, total_fingerprints = self.get_all_users_with_pagination(ip)
            counts['total_fingerprints'] = total_fingerprints
            counts['users_with_fingerprints'] = sum(1 for user in all_users if user.get('numOfFP', 0) > 0)
            
            # Compile results
            result = {
                'device': device,
                'capabilities': capabilities,
                'counts': counts,
                'total_users_fetched': len(all_users),
                'consistency_check': {
                    'users_match': counts['total_users'] == len(all_users),
                    'fingerprints_match': counts['users_with_fingerprints'] == sum(1 for user in all_users if user.get('numOfFP', 0) > 0)
                }
            }
            
            results.append(result)
            
            # Display summary
            print(f"\nDevice: {ip} - {device['model']} ({device['name']})")
            print(f"Capabilities:")
            print(f"  Max Users: {capabilities['max_users']}")
            print(f"  Max Cards: {capabilities['max_cards']}")
            print(f"  Max Faces: {capabilities['max_faces']}")
            print(f"  Fingerprint Support: {capabilities['fingerprint_supported']}")
            if capabilities['fingerprint_supported']:
                print(f"  Fingerprints per User: {capabilities['fingerprints_per_user']}")
                print(f"  Max Total Fingerprints: {capabilities['max_fingerprints']}")
            
            print(f"\nCurrent Enrollment:")
            print(f"  Total Users: {counts['total_users']}")
            print(f"  Users with Cards: {counts['users_with_cards']}")
            print(f"  Users with Faces: {counts['users_with_faces']}")
            print(f"  Users with Fingerprints: {counts['users_with_fingerprints']}")
            print(f"  Total Cards: {counts['total_cards']}")
            print(f"  Total Faces: {counts['total_faces']}")
            print(f"  Total Fingerprints: {counts['total_fingerprints']}")
            
            print(f"\nData Consistency:")
            print(f"  User count matches fetched users: {result['consistency_check']['users_match']}")
            print(f"  Total users fetched via pagination: {result['total_users_fetched']}")
        
        # Save comprehensive report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"hikvision_scan_report_{timestamp}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n\nComprehensive report saved to: {report_filename}")
        
        return results

if __name__ == "__main__":
    subnet = sys.argv[1] if len(sys.argv) > 1 else None
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "a1234@4321"
    
    scanner = HikvisionScanner(username=username, password=password)
    scanner.scan_and_analyze(subnet)