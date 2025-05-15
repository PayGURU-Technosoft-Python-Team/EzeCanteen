import requests
from requests.auth import HTTPDigestAuth
import json
from datetime import datetime, timedelta

# Device configuration
ip = "192.168.0.82"
port = 80
username = "admin"
password = "a1234@4321"

# Set time range (last 24 hours)
# Hikvision requires ISO 8601 format with timezone
end_time = datetime.now() 
start_time = end_time - timedelta(minutes=5)

# Format times with timezone (Z for UTC or +HH:MM for local)
# Try different formats based on common Hikvision requirements
end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')  # Adjust timezone as needed
start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')

# Alternative formats to try:
# end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
# end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
# end_time_str = end_time.isoformat()

# Build URL
url = f"http://{ip}:{port}/ISAPI/AccessControl/AcsEvent?format=json"

# Create payload
payload = {
    "AcsEventCond": {
        "searchID": "1",
        "searchResultPosition": 0,  # Note: lowercase 's'
        "maxResults": 30,
        "major": 5,
        "minor": 75,
        "startTime": start_time_str,
        "endTime": end_time_str
    }
}

# Try the request
try:
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Time range: {start_time_str} to {end_time_str}")
    print("-" * 50)
    
    response = requests.post(
        url,
        json=payload,
        auth=HTTPDigestAuth(username, password),
        timeout=15,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print("\nRaw Response:")
    print(response.text)
    
    # Parse JSON response if successful
    if response.status_code == 200:
        try:
            data = response.json()
            print("\nParsed JSON:")
            print(json.dumps(data, indent=2))
            
            # Extract event information if available
            if "AcsEvent" in data:
                info_list = data["AcsEvent"].get("InfoList", [])
                print(f"\nFound {len(info_list)} events")
                
                for i, event in enumerate(info_list):
                    print(f"\nEvent {i+1}:")
                    print(f"  Time: {event.get('time', 'N/A')}")
                    print(f"  Employee No: {event.get('employeeNoString', event.get('employeeNo', 'N/A'))}")
                    print(f"  Card No: {event.get('cardNo', 'N/A')}")
                    print(f"  Name: {event.get('name', 'N/A')}")
                    print(f"  Door: {event.get('doorName', 'N/A')}")
                    print(f"  Major: {event.get('major', 'N/A')}")
                    print(f"  Minor: {event.get('minor', 'N/A')}")
                    
                    # Check for attendance info
                    if "AttendanceInfo" in event:
                        att = event["AttendanceInfo"]
                        print(f"  Attendance Status: {att.get('attendanceStatus', 'N/A')}")
                        print(f"  Label: {att.get('labelName', 'N/A')}")
            
        except json.JSONDecodeError:
            print("Response is not valid JSON")
    else:
        # If error, try to provide more detail
        try:
            error_data = response.json()
            print(f"\nError Details:")
            print(f"  Status Code: {error_data.get('statusCode')}")
            print(f"  Status String: {error_data.get('statusString')}")
            print(f"  Sub Status: {error_data.get('subStatusCode')}")
            print(f"  Error Code: {error_data.get('errorCode')}")
            print(f"  Error Message: {error_data.get('errorMsg')}")
        except:
            pass
    
    # Save to file
    filename = f"acs_events_{ip.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(f"URL: {url}\n")
        f.write(f"Payload: {json.dumps(payload, indent=2)}\n")
        f.write(f"Status Code: {response.status_code}\n")
        f.write(f"Headers: {response.headers}\n\n")
        f.write("Raw Response:\n")
        f.write(response.text)
    
    print(f"\nSaved to: {filename}")
    
except Exception as e:
    print(f"Error: {e}")

# If the above doesn't work, try this minimal version
print("\n\nTrying minimal payload...")
print("-" * 50)

minimal_payload = {
    "AcsEventCond": {
        "searchID": "1",
        "searchResultPosition": 0,
        "maxResults": 1
    }
}

try:
    response = requests.post(
        url,
        json=minimal_payload,
        auth=HTTPDigestAuth(username, password),
        timeout=10
    )
    
    print(f"Minimal Payload Status: {response.status_code}")
    print(f"Minimal Response: {response.text[:200]}...")
    
except Exception as e:
    print(f"Minimal request error: {e}")
    
def check_time_range(self):
    """Check if current time is within the specified meal time range"""
    if not self.from_time_str or not self.to_time_str:
        return True  # If no time range specified, always proceed
        
    current_time = datetime.now().strftime('%H:%M')
    return self.from_time_str <= current_time <= self.to_time_str
    