import requests
from requests.auth import HTTPDigestAuth
import json
from datetime import datetime, timedelta
import time
import sys
import os
import tempfile
import shutil
import uuid
import mysql.connector
import socket
import logging
import xmltodict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                             QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
                             QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QThread, QFile
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QBrush, QPalette
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy
import urllib.request
from io import BytesIO
from print import print_slip  # Import print_slip function
from PyQt5 import sip

# Default device configuration (will be used if DB fetch fails)
IP = "192.168.0.85"
PORT = 80
USERNAME = "admin"
PASSWORD = "a1234@4321"

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"
DB_TABLE = "sequentiallog"

# Dictionary to store device configurations and their associated printers
DEVICES = {}

# Function to modify user begin time
def modify_user_begin_time(base_url, username, password, employee_no, begin_time, employee_name=None):
    """Update a user's begin time on the device"""
    url = f"{base_url}/ISAPI/AccessControl/UserInfo/Modify?format=json"

    # Payload to update only the beginTime
    payload = {
        "UserInfo": {
            "employeeNo": employee_no,
            "name": employee_name if employee_name else employee_no,  # Use the provided name or employee number
            "Valid": {
                "enable": True,
                "beginTime": begin_time,
                "timeType": "local"
            },
            "addUser": True,
            "checkUser": False
        }
    }

    headers = {'Content-Type': 'application/json'}
    auth = HTTPDigestAuth(username, password)

    try:
        response = requests.put(
            url,
            auth=auth,
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )

        logging.info(f"API response for updating begin time for employee {employee_no}: Status {response.status_code}")
        
        try:
            return response.json()
        except ValueError:
            return {
                "error": "Invalid JSON response",
                "status_code": response.status_code,
                "text": response.text[:200]  # Limit text length for logging
            }
    except Exception as e:
        logging.error(f"Error updating begin time for employee {employee_no}: {str(e)}")
        return {"error": str(e)}

# Function to fetch device configurations from the database
def fetch_device_config():
    """Fetch device configurations from the database"""
    global DEVICES, IP, PORT, USERNAME, PASSWORD
    
    try:
        # Connect to the database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            port=DB_PORT,
            password=DB_PASS,
            database=DB_NAME
        )
        
        # Create a cursor
        cursor = conn.cursor(dictionary=True)
        
        # Query to fetch all devices from configh table
        sql = """
        SELECT 
            SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
            Enable, DevicePrinterIP, DeviceName,
            AES_DECRYPT(comKey, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) as Pwd
        FROM configh
        WHERE Enable = 'Y'
        ORDER BY DeviceType, DeviceNumber
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if not results:
            logging.warning("No enabled devices found in database, using default values")
            return
        
        # Create a dictionary to map printer IPs to their details
        printer_ip_map = {}
        
        # First pass: collect all printers
        for device in results:
            if device.get('DeviceType') == 'Printer':
                printer_ip_map[device['IP']] = {
                    'ip': device['IP'],
                    'port': device.get('Port', 9100) if device.get('Port') else 9100,
                    'name': device.get('DeviceName', 'CITIZEN'),
                    'location': device.get('DeviceLocation', '')
                }
                logging.info(f"Found printer in database: {device['IP']}:{device.get('Port', 9100)} ({device.get('DeviceName', 'CITIZEN')})")
        
        # Second pass: process authentication devices and link them to printers
        for device in results:
            if device.get('DeviceType') == 'Device':
                device_ip = device['IP']
                device_port = device.get('Port', 80) if device.get('Port') else 80
                device_user = device.get('ComUser', 'admin') if device.get('ComUser') else 'admin'
                
                # Handle the decrypted password
                device_pwd = None
                if device.get('Pwd') is not None:
                    try:
                        # Convert bytes to string if needed
                        if isinstance(device['Pwd'], bytes):
                            device_pwd = device['Pwd'].decode('utf-8')
                        else:
                            device_pwd = str(device['Pwd'])
                    except Exception as e:
                        logging.error(f"Error decoding password for device {device_ip}: {e}")
                        device_pwd = PASSWORD  # Use default if decoding fails
                else:
                    device_pwd = PASSWORD  # Use default if no password
                
                # Find associated printer from DevicePrinterIP
                printer_ip = device.get('DevicePrinterIP', '')
                
                logging.info(f"Processing device {device_ip} with DevicePrinterIP: {printer_ip}")
                
                # If printer IP is not in our map, create a virtual printer entry
                if printer_ip and printer_ip not in printer_ip_map:
                    printer_ip_map[printer_ip] = {
                        'ip': printer_ip,
                        'port': 9100,  # Default port for printers
                        'name': 'CITIZEN',  # Default name
                        'virtual': True  # Mark as virtual printer
                    }
                    logging.info(f"Created virtual printer entry for IP: {printer_ip}")
                
                # Get printer details if available
                printer_config = {
                    'ip': printer_ip,
                    'port': 9100  # Default printer port
                }
                
                if printer_ip and printer_ip in printer_ip_map:
                    printer_details = printer_ip_map[printer_ip]
                    printer_config = {
                        'ip': printer_details['ip'],
                        'port': printer_details['port'],
                        'name': printer_details.get('name', 'CITIZEN')
                    }
                
                # Store device configuration with its printer
                DEVICES[device_ip] = {
                    'device': {
                        'ip': device_ip,
                        'port': device_port,
                        'user': device_user,
                        'password': device_pwd,
                        'location': device.get('DeviceLocation', ''),
                        'enable': device.get('Enable', 'Y')
                    },
                    'printer': printer_config
                }
                
                logging.info(f"Loaded device configuration: {device_ip}:{device_port} -> Printer: {printer_config['ip']}:{printer_config['port']}")
        
        # Set default device to the first one for backward compatibility
        if DEVICES:
            first_device = next(iter(DEVICES.values()))
            IP = first_device['device']['ip']
            PORT = first_device['device']['port']
            USERNAME = first_device['device']['user']
            PASSWORD = first_device['device']['password']
            logging.info(f"Set default device to {IP}:{PORT}")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        logging.error(f"Database error while fetching device configurations: {err}")
        print(f"Error fetching device configurations: {err}")
        print("Using default device configuration")
    except Exception as e:
        logging.error(f"Unexpected error loading device configurations: {e}")
        print(f"Unexpected error: {e}")
        print("Using default device configuration")

# Load device configuration from database
fetch_device_config()

# Create temp directory for images
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'ezecanteen_images')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def print_server_addresses():
    """Prints all server addresses used in the application"""
    print("\n===== SERVER ADDRESSES =====")
    print(f"Database Server: {DB_HOST}:{DB_PORT}")
    
    # Print all device and printer configurations
    if DEVICES:
        print("\n   :")
        for device_ip, config in DEVICES.items():
            print(f"  Device: {device_ip}:{config['device']['port']} ({config['device']['location'] or 'No location'})")
            print(f"  Printer: {config['printer']['ip']}:{config['printer']['port']}")
            print("")
    else:
        print(f"\nUsing default device: {IP}:{PORT}")
        
        # Try to get printer IP from appSettings.json
        try:
            with open('appSettings.json', 'r') as f:
                app_settings = json.load(f)
                printer_config = app_settings.get('PrinterConfig', {})
                printer_ip = printer_config.get('IP', "192.168.0.253")
                printer_port = printer_config.get('Port', 9100)
                print(f"Default Printer: {printer_ip}:{printer_port}")
        except Exception as e:
            print(f"Default Printer: Unknown (Error: {e})")
    
    print("===========================\n")


def getDeviceDetails(ip, port, user, psw):
    url = f"http://{ip}:{port}/ISAPI/System/deviceinfo"
    payload = {}
    headers = {}
    response = None
    deviceSerial = ""
    model = ""
    MacAddress = ""  # Initialize MacAddress to prevent UnboundLocalError
 
    try:
        # Log authentication attempt (sanitize password)
        masked_password = psw[:2] + "*" * (len(psw) - 4) + psw[-2:] if len(psw) > 4 else "****"
        logging.info(f"Getting device details for {ip}:{port} with user: {user}")
        print(f"Getting device details for {ip}:{port} with user: {user}")
       
        response = requests.get(url, auth=HTTPDigestAuth(
            user, psw), headers=headers, data=payload, timeout=5)
           
        if response.status_code == 401:
            logging.error(f"Authentication failed (401 Unauthorized) for {ip}:{port} with user: {user}. Check credentials.")
            return deviceSerial, MacAddress
        elif response.status_code != 200:
            logging.error(f"Failed to get device details, received status code {response.status_code}")
            return deviceSerial, MacAddress
           
        # When successful (status code 200)
        if response.status_code == 200:
            logging.info(f"Successfully retrieved device details from {ip}:{port}")
            try:
                data = xmltodict.parse(response.text)
                data = data['DeviceInfo']
                model = data['model']
                model = model.replace(" ", "")
                serialNo = data['serialNumber']
                serialNo = serialNo.replace(" ", "")
                MacAddress = data['macAddress']
                if model.upper() in serialNo.upper():
                    deviceSerial = serialNo
                else:
                    deviceSerial = model + serialNo
                logging.info(f"Device info: Model={model}, Serial={deviceSerial}, MAC={MacAddress}")
            except Exception as parse_err:
                logging.error(f"Error parsing device details XML: {parse_err}. Response: {response.text[:200]}")
    except requests.exceptions.Timeout:
        logging.error(f"Timeout connecting to {ip}:{port}")
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error for {ip}:{port}. Device may be offline or unreachable.")
    except Exception as e:
        logging.error(f"IP: {ip} : An error occurred while fetching device serial: {str(e)}")
    finally:
        if response:
            response.close()
 
    return deviceSerial, MacAddress

# Call the function to print server addresses
print_server_addresses()

class Communicator(QObject):
    # Signal to communicate between components
    stop_server = pyqtSignal()
    new_auth_event = pyqtSignal(dict)

class TimeDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            color: white; 
            font-weight: bold;
            background-color: #1e2b38;
            padding: 8px 12px;
            border-radius: 4px;
        """)
        self.setFont(QFont("Arial", 14))
        
        # Update time every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%d %b %Y")
        self.setText(f"{current_time}\n{current_date}")

class AuthEventMonitor(QThread):
    def __init__(self, communicator, device_ip=None):
        super().__init__()
        self.communicator = communicator
        self.running = True
        self.communicator.stop_server.connect(self.stop)
        self.start_time = datetime.now()  # Store initialization time
        self.consecutive_errors = 0  # Counter for consecutive errors
        self.max_consecutive_errors = 5  # Maximum allowed consecutive errors
        self.last_successful_fetch = datetime.now()  # Track when we last successfully fetched events
        
        # Read appSettings.json to get fromTime and toTime
        try:
            with open('appSettings.json', 'r') as f:
                self.app_settings = json.load(f)
            
            # Get meal schedule
            self.meal_schedule = self.app_settings.get('CanteenMenu', {}).get('MealSchedule', [])
            if self.meal_schedule:
                self.from_time_str = self.meal_schedule[0].get('fromTime', '')
                self.to_time_str = self.meal_schedule[0].get('toTime', '')
                logging.info(f"Meal schedule configured: {self.from_time_str} to {self.to_time_str}")
            else:
                self.from_time_str = ''
                self.to_time_str = ''
                logging.warning("No meal schedule found in app settings")
        except Exception as e:
            logging.error(f"Error reading appSettings.json: {e}")
            self.from_time_str = ''
            self.to_time_str = ''
        
        # Get device configuration
        self.device_ip = device_ip
        
        if device_ip and device_ip in DEVICES:
            # Use the specified device configuration
            device_config = DEVICES[device_ip]['device']
            self.ip = device_config['ip']
            self.port = device_config['port']
            self.username = device_config['user']
            self.password = device_config['password']
            logging.info(f"AuthEventMonitor using device: {self.ip}:{self.port}")
        else:
            # Use the global configuration (default device)
            self.ip = IP
            self.port = PORT
            self.username = USERNAME
            self.password = PASSWORD
            logging.info(f"AuthEventMonitor using default device: {self.ip}:{self.port}")
        
        # URL for access control events
        self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
        logging.info(f"AuthEventMonitor initialized with endpoint: {self.url}")
        logging.info(f"Starting to monitor events from: {self.start_time}")
        
        # Keep track of processed events
        self.processed_events = set()
        
        # Add watchdog timer that will restart the monitor if no events are received for a long time
        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self.check_watchdog)
        self.watchdog_timer.start(60000)  # Check every minute
    
    def check_time_range(self):
        """Check if current time is within the specified meal time range"""
        if not self.meal_schedule:
            return True  # If no meal schedule specified, always proceed
        
        current_time = datetime.now().strftime('%H:%M')
        
        # Check all meal schedule entries
        for meal in self.meal_schedule:
            from_time = meal.get('fromTime', '')
            to_time = meal.get('toTime', '')
            
            if from_time and to_time and from_time <= current_time <= to_time:
                return True
            
        return False
    
    def check_watchdog(self):
        """Check if we haven't received events for too long and reset if needed"""
        if not self.running:
            return
        
        # If it's been more than 10 minutes since our last successful fetch during a meal time
        time_since_last_fetch = (datetime.now() - self.last_successful_fetch).total_seconds()
        
        if self.check_time_range() and time_since_last_fetch > 600:  # 10 minutes
            logging.warning(f"No events received for {time_since_last_fetch} seconds during meal time. Resetting connection.")
            # Reset the start time to now to avoid fetching old events
            self.start_time = datetime.now()
            # Reset consecutive errors counter
            self.consecutive_errors = 0
            # Update last fetch time to avoid immediate reset
            self.last_successful_fetch = datetime.now()
    
    def retry_connection(self):
        """Retry establishing connection with exponential backoff"""
        # Reset the URL just in case
        self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
        
        # Log the retry
        logging.info(f"Retrying connection to {self.url}")
        
        # Refresh credentials from DEVICES if needed
        if self.device_ip and self.device_ip in DEVICES:
            device_config = DEVICES[self.device_ip]['device']
            self.ip = device_config['ip']
            self.port = device_config['port']
            self.username = device_config['user']
            self.password = device_config['password']
            # Update URL with fresh credentials
            self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
            logging.info(f"Updated device credentials for retry: {self.ip}:{self.port}")
    
    def run(self):
        """Main monitoring loop"""
        logging.info("Auth event monitoring started")
        in_meal_time = False  # Track if we were previously in a meal time
        
        while self.running:
            # Check if current time is within a meal time
            current_in_meal_time = self.check_time_range()
            
            # If we just entered a meal time period, update the start time
            if current_in_meal_time and not in_meal_time:
                self.start_time = datetime.now()
                logging.info(f"Entered meal time period. Updated start time to: {self.start_time}")
            
            # Update meal time status for next iteration
            in_meal_time = current_in_meal_time
            
            # If not in meal time, skip processing and sleep
            if not current_in_meal_time:
                # Sleep for shorter intervals to respond to stop signals more quickly
                for _ in range(6):  # 6 x 1 seconds = 6 seconds total
                    if not self.running:
                        logging.info("Auth event monitoring stopping during sleep")
                        return
                    time.sleep(1)
                continue
                
            try:
                # Set time range (from start time to now)
                end_time = datetime.now() 
                
                # Format times with timezone
                end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                start_time_str = self.start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                
                # Initialize pagination variables
                search_position = 0
                total_matches = None
                num_matches = 0
                has_more_pages = True
                processed_ids = set()  # Track processed event IDs to avoid duplicates
                
                # Fetch all pages of results
                while has_more_pages and self.running:
                    # Create payload for authentication events with current search position
                    payload = {
                        "AcsEventCond": {
                            "searchID": "1",
                            "searchResultPosition": search_position,
                            "maxResults": 5,  # Keep batch size reasonable
                            "major": 5,  # Access Control
                            "minor": 0,  # Authentication passed
                            "startTime": start_time_str,
                            "endTime": end_time_str
                        }
                    }
                    
                    # Make the request with increased timeout
                    response = requests.post(
                        self.url,
                        json=payload,
                        auth=HTTPDigestAuth(self.username, self.password),
                        timeout=30,  # Increased timeout from 15 to 30 seconds
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    # Process successful responses
                    if response.status_code == 200:
                        # Reset consecutive errors on success
                        self.consecutive_errors = 0
                        # Update last successful fetch time
                        self.last_successful_fetch = datetime.now()
                        
                        try:
                            data = response.json()
                            
                            # Get pagination information if this is the first page
                            if total_matches is None and "AcsEvent" in data and "totalMatches" in data["AcsEvent"]:
                                total_matches = int(data["AcsEvent"]["totalMatches"])
                                logging.info(f"Found {total_matches} total authentication events")
                            
                            # Extract event information if available
                            if "AcsEvent" in data:
                                info_list = data["AcsEvent"].get("InfoList", [])
                                page_events = len(info_list)
                                
                                # If no events were returned, we've reached the end
                                if page_events == 0:
                                    has_more_pages = False
                                    break
                                
                                # Process each event
                                for event in info_list:
                                    event_time = event.get('time')
                                    event_id = f"{event.get('employeeNoString', event.get('employeeNo', 'N/A'))}-{event_time}"
                                    
                                    # Check for duplicates within this batch
                                    if event_id in processed_ids:
                                        continue
                                        
                                    processed_ids.add(event_id)
                                    
                                    # Check if this is a new event we haven't processed yet
                                    if event_id not in self.processed_events:
                                        self.processed_events.add(event_id)
                                        
                                        # Log the new authentication event
                                        emp_id = event.get('employeeNoString', event.get('employeeNo', 'N/A'))
                                        name = event.get('name', 'N/A')
                                        logging.info(f"New authentication event: Employee ID={emp_id}, Name={name}, Time={event_time}")
                                        
                                        # Add source device information to the event
                                        event['source_device_ip'] = self.device_ip
                                        event['deviceIP'] = self.ip
                                        
                                        # Emit signal with event data
                                        self.communicator.new_auth_event.emit(event)
                                
                                # Update number of processed events
                                num_matches += page_events
                                
                                # Update search position for next page
                                search_position += page_events
                                
                                # Check if we've processed all events or reached a limit
                                if (total_matches is not None and num_matches >= total_matches) or num_matches >= 300:
                                    has_more_pages = False
                                    break
                            else:
                                # No events found in response, exit pagination loop
                                has_more_pages = False
                        
                        except json.JSONDecodeError as json_err:
                            logging.error(f"Response is not valid JSON: {json_err}")
                            self.consecutive_errors += 1
                            has_more_pages = False
                    else:
                        # Log error and increment counter
                        logging.error(f"API request failed with status code: {response.status_code}")
                        self.consecutive_errors += 1
                        has_more_pages = False
                        
                        # If unauthorized, try to refresh credentials
                        if response.status_code == 401:
                            logging.warning("Authentication failed. Attempting to refresh credentials.")
                            self.retry_connection()
                
                # Limit the size of processed_events to avoid memory issues
                if len(self.processed_events) > 1000:
                    # Keep only the most recent 500 events
                    self.processed_events = set(list(self.processed_events)[-500:])
                    logging.info("Pruned processed events cache to 500 entries")
                
            except requests.exceptions.Timeout:
                logging.error(f"Timeout connecting to {self.ip}:{self.port}")
                self.consecutive_errors += 1
                time.sleep(2)  # Short sleep after timeout before retrying
            except requests.exceptions.ConnectionError:
                logging.error(f"Connection error for {self.ip}:{self.port}. Device may be offline or unreachable.")
                self.consecutive_errors += 1
                time.sleep(5)  # Longer sleep after connection error
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                self.consecutive_errors += 1
            
            # Check if we've had too many consecutive errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logging.warning(f"Reached {self.consecutive_errors} consecutive errors. Resetting connection...")
                self.retry_connection()
                self.consecutive_errors = 0  # Reset the counter
                self.start_time = datetime.now()  # Reset start time to avoid fetching old events
                time.sleep(10)  # Wait a bit before retrying
            
            # Sleep for a short period before the next check
            time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread"""
        logging.info("Auth event monitoring stopping...")
        self.running = False
        
        # Stop the watchdog timer
        if self.watchdog_timer.isActive():
            self.watchdog_timer.stop()
        
        # Wait for thread to finish, but with timeout
        if self.isRunning():
            if not self.wait(3000):  # 3 second timeout
                logging.warning("Auth event monitor did not stop gracefully, forcing termination")
                self.terminate()
                self.wait()
        
        logging.info("Auth event monitoring stopped")

class AuthEventItem(QFrame):
    def __init__(self, event_data):
        super().__init__()
        self.event_data = event_data
        # Store the minor value for authentication type
        self.minor = event_data.get('minor', 0)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        # Make box more horizontal to better fit the images
        self.setMinimumSize(220, 180)
        self.setMaximumSize(300, 200)
        
        # Apply subtle shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Create image container - adjusted for horizontal images
        self.image_container = QWidget()
        self.image_container.setStyleSheet("""
            background-color: #1e2b38; 
            border-radius: 4px;
        """)
        self.image_container.setFixedSize(180, 110)
        
        image_layout = QVBoxLayout(self.image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setFixedSize(170, 100)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")
        self.image_label.setScaledContents(True)
        
        image_layout.addWidget(self.image_label)
        image_layout.setAlignment(Qt.AlignCenter)
        
        # Container for the image
        image_outer_container = QWidget()
        image_outer_layout = QHBoxLayout(image_outer_container)
        image_outer_layout.setContentsMargins(0, 0, 0, 0)
        image_outer_layout.addWidget(self.image_container)
        image_outer_layout.setAlignment(Qt.AlignCenter)
        
        # ID (previously name)
        emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', 'N/A'))
        id_label = QLabel(emp_id)
        id_label.setStyleSheet("""
            color: white; 
            font-weight: bold; 
            font-size: 14px;
            background: transparent;
        """)
        id_label.setAlignment(Qt.AlignCenter)
        
        # Create info section
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Get event time for date display
        event_time = event_data.get('time', 'N/A')
        if 'T' in event_time:
            date_parts = event_time.split('T')[0] if 'T' in event_time else event_time
            time_parts = event_time.split('T')[1].split('+')[0] if 'T' in event_time else ""
        else:
            date_parts = ""
            time_parts = event_time
            
        # Left column - Name (previously Status)
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        name_label = QLabel("NAME")
        name_label.setStyleSheet("""
            color: #2ecc71; 
            font-weight: bold; 
            font-size: 13px;
            background: transparent;
        """)

        name = event_data.get('name', 'N/A')
        name_value = QLabel(name)
        name_value.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        
        left_layout.addWidget(name_label)
        left_layout.addWidget(name_value)
        
        # Right column - Date (previously Label)
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        date_title = QLabel("TIME")
        date_title.setStyleSheet("""
            color: #3498db; 
            font-weight: bold; 
            font-size: 13px;
            background: transparent;
        """)
        date_value = QLabel(time_parts)
        date_value.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        
        right_layout.addWidget(date_title)
        right_layout.addWidget(date_value)
        
        # Add columns to info layout
        info_layout.addWidget(left_column)
        info_layout.addWidget(right_column)
        
        # Add all widgets to main layout
        layout.addWidget(image_outer_container)
        layout.addWidget(id_label)
        layout.addWidget(info_widget)
        
        # Load image if available - do this last
        self.is_deleted = False
        self.load_image(event_data.get('pictureURL'))
    
    def load_image(self, url):
        """Load image from URL and display it"""
        # Check minor value to determine which image to display
        if self.minor == 1:  # Card authentication
            try:
                self.image_label.setText("")
                card_pixmap = QPixmap("card.png")
                if not card_pixmap.isNull():
                    scaled_pixmap = card_pixmap.scaled(
                        self.image_label.width(),
                        self.image_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setText("Card Image Not Found")
                    self.image_label.setStyleSheet("color: #bdc3c7; background: transparent;")
            except Exception as e:
                print(f"Error loading card image: {e}")
                self.image_label.setText("Card Error")
                self.image_label.setStyleSheet("color: #e74c3c; background: transparent;")
            return
            
        elif self.minor == 38:  # Fingerprint authentication
            try:
                self.image_label.setText("")
                fp_pixmap = QPixmap("fp.png")
                if not fp_pixmap.isNull():
                    scaled_pixmap = fp_pixmap.scaled(
                        self.image_label.width(),
                        self.image_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setText("FP Image Not Found")
                    self.image_label.setStyleSheet("color: #bdc3c7; background: transparent;")
            except Exception as e:
                print(f"Error loading fingerprint image: {e}")
                self.image_label.setText("FP Error")
                self.image_label.setStyleSheet("color: #e74c3c; background: transparent;")
            return
            
        # For other authentication types or when face image is available
        if not url or url == 'N/A':
            # Set default image if no URL provided
            self.image_label.setText("No Image")
            self.image_label.setStyleSheet("color: #bdc3c7; background: transparent;")
            return
            
        try:
            # Show loading indicator
            self.image_label.setText("Loading...")
            self.image_label.setStyleSheet("color: #bdc3c7; background: transparent;")
            
            # Create a QTimer to load the image asynchronously
            self.timer = QTimer()
            self.timer.timeout.connect(lambda: self._fetch_image(url))
            self.timer.setSingleShot(True)
            self.timer.start(100)  # Start after 100ms
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_label.setText("Error")
            self.image_label.setStyleSheet("color: #e74c3c; background: transparent;")
    
    def _fetch_image(self, url):
        try:
            if hasattr(self, 'is_deleted') and self.is_deleted:
                return
                
            # Generate unique filename for this image
            unique_id = str(uuid.uuid4())
            filename = os.path.join(TEMP_DIR, f"image_{unique_id}.jpg")
            
            # Find appropriate credentials for authentication
            # Extract device IP from URL if possible
            device_ip = None
            if url and "://" in url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    device_ip = parsed_url.netloc.split(':')[0]
                except Exception as e:
                    logging.error(f"Error parsing URL to get device IP: {e}")
            
            # Get authentication credentials
            username = USERNAME
            password = PASSWORD
            
            # If we have device-specific credentials, use them
            if device_ip and DEVICES and device_ip in DEVICES:
                device_config = DEVICES[device_ip]['device']
                username = device_config['user']
                password = device_config['password']
                logging.info(f"Using device-specific credentials for {device_ip} to fetch image")
            
            # Use requests with digest authentication
            response = requests.get(
                url,
                auth=HTTPDigestAuth(username, password),
                timeout=10
            )
            
            if response.status_code == 200:
                # Check if widget still exists
                if hasattr(self, 'is_deleted') and self.is_deleted:
                    return
                
                # Save image to temp directory
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                # Load the image from file
                pixmap = QPixmap(filename)
                
                # Check if widget still exists
                if hasattr(self, 'is_deleted') and self.is_deleted:
                    return
                
                # Scale pixmap to fit the label while preserving aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.image_label.width(),
                    self.image_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                # Check if widget still exists
                if hasattr(self, 'is_deleted') and self.is_deleted:
                    return
                    
                self.image_label.setPixmap(scaled_pixmap)
            else:
                # Check if widget still exists
                if hasattr(self, 'is_deleted') and self.is_deleted:
                    return
                    
                print(f"Error fetching image: HTTP Status {response.status_code}")
                self.image_label.setText(f"Error {response.status_code}")
                self.image_label.setStyleSheet("color: white; background-color: #1f2937; border-radius: 4px;")
                
        except RuntimeError as e:
            # QLabel has been deleted, just ignore
            print(f"Ignoring RuntimeError: {e}")
            return
        except Exception as e:
            # Check if widget still exists
            if hasattr(self, 'is_deleted') and self.is_deleted:
                return
                
            print(f"Error fetching image: {e}")
            self.image_label.setText("Error")
            self.image_label.setStyleSheet("color: white; background-color: #1f2937; border-radius: 4px;")
            
    def deleteLater(self):
        """Override deleteLater to mark as deleted"""
        self.is_deleted = True
        super().deleteLater()

class EzeeCanteen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.communicator = Communicator()
        self.events = []
        self.max_events = 100  # Increased maximum number of events from 18 to 100
        self.token_counter = 0  # Initialize token counter
        self.current_date = datetime.now().date()  # Track date for token counter reset
        self.settings_mode = False  # Flag to indicate if we're in settings mode
        self.parent_window = None  # Reference to parent window if in settings mode
        
        # Store device configurations
        self.active_devices = {}  # Will store device IP -> monitor thread mapping
        self.device_printers = {}  # Will store device IP -> printer details mapping
        
        self.init_ui()
        
        # Test database connection
        self.test_db_connection()
        
        # Connect resize event to refresh grid
        self.resized = False
        
        # Initialize devices and start monitors
        self.initialize_devices()
        
        # Set up timer to periodically check printer connections
        self.printer_check_timer = QTimer(self)
        self.printer_check_timer.timeout.connect(self.test_printer_connections)
        self.printer_check_timer.start(60000)  # Check every 60 seconds
    
    def initialize_devices(self):
        """Initialize all configured authentication devices and their printers"""
        # Clear any existing events when initializing
        self.events = []
        self.clear_grid()
        
        if not DEVICES:
            # If no devices were configured, use a single monitor with default settings
            logging.warning("No devices configured. Using default device configuration.")
            self.setup_single_device_monitor()
            return
            
        logging.info(f"Initializing {len(DEVICES)} authentication devices")
        
        # Start a monitor for each configured device
        for device_ip, config in DEVICES.items():
            try:
                # Get device details
                device_config = config['device']
                printer_config = config['printer']
                
                # Store printer configuration for this device
                self.device_printers[device_ip] = {
                    'ip': printer_config['ip'],
                    'port': printer_config.get('port', 9100),
                    'name': printer_config.get('name', 'CITIZEN'),
                    'available': False  # Will be set by test_printer_connections
                }
                
                # Log the device-to-printer mapping
                logging.info(f"Device {device_ip} mapped to printer {printer_config['ip']}:{printer_config.get('port', 9100)}")
                
                # Get device serial and MAC
                device_serial, device_mac = getDeviceDetails(
                    device_config['ip'], 
                    device_config['port'], 
                    device_config['user'], 
                    device_config['password']
                )
                
                # Store the device serial for the first device (for backward compatibility)
                if not hasattr(self, 'device_serial'):
                    self.device_serial = device_serial
                    self.device_mac = device_mac
                
                # Start authentication event monitor for this device
                auth_monitor = AuthEventMonitor(self.communicator, device_ip)
                auth_monitor.start()
                
                # Store monitor in active devices
                self.active_devices[device_ip] = {
                    'monitor': auth_monitor,
                    'serial': device_serial,
                    'mac': device_mac
                }
                
                logging.info(f"Started monitor for device {device_ip}:{device_config['port']} with serial {device_serial}")
                
            except Exception as e:
                logging.error(f"Error initializing device {device_ip}: {e}")
        
        # Connect the signal to handle authentication events
        # We'll determine which device generated the event when handling it
        self.communicator.new_auth_event.connect(self.add_auth_event)
        
        # Test printer connections
        self.test_printer_connections()

    def setup_single_device_monitor(self):
        """Set up a single device monitor using default configuration"""
        # Clear any existing events when setting up
        self.events = []
        self.clear_grid()
        
        # Get device details
        self.device_serial, self.device_mac = getDeviceDetails(IP, PORT, USERNAME, PASSWORD)
        logging.info(f"Device details initialized: Serial={self.device_serial}, MAC={self.device_mac}")
        
        # Try to fetch printer configuration from database first
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            
            if conn:
                cursor = conn.cursor(dictionary=True)
                
                # Find a printer entry in the database
                printer_query = """
                    SELECT IP, Port, DeviceName
                    FROM configh
                    WHERE DeviceType = 'Printer' AND Enable = 'Y'
                    LIMIT 1
                """
                
                cursor.execute(printer_query)
                printer_data = cursor.fetchone()
                
                if printer_data:
                    self.printer_ip = printer_data['IP']
                    self.printer_port = printer_data['Port'] if printer_data['Port'] else 9100
                    logging.info(f"Using printer from database: {self.printer_ip}:{self.printer_port}")
                else:
                    # If no printer found in DB, fall back to app settings
                    with open('appSettings.json', 'r') as f:
                        app_settings = json.load(f)
                        printer_config = app_settings.get('PrinterConfig', {})
                        self.printer_ip = printer_config.get('IP', "192.168.0.253")
                        self.printer_port = printer_config.get('Port', 9100)
                        logging.info(f"No printer in DB, using from appSettings: {self.printer_ip}:{self.printer_port}")
                
                cursor.close()
                conn.close()
            else:
                raise Exception("Database connection failed")
                
        except Exception as e:
            # Fall back to appSettings.json if database fetch fails
            logging.error(f"Error fetching printer from database: {e}")
            try:
                with open('appSettings.json', 'r') as f:
                    app_settings = json.load(f)
                    printer_config = app_settings.get('PrinterConfig', {})
                    self.printer_ip = printer_config.get('IP', "192.168.0.253")
                    self.printer_port = printer_config.get('Port', 9100)
                    logging.info(f"Falling back to printer from appSettings: {self.printer_ip}:{self.printer_port}")
            except Exception as app_err:
                # Absolute fallback to hardcoded values
                logging.error(f"Error loading printer settings from appSettings.json: {app_err}")
                self.printer_ip = "192.168.0.253"  # Default IP
                self.printer_port = 9100  # Default port
                logging.warning(f"Using hardcoded printer settings: {self.printer_ip}:{self.printer_port}")
        
        # Test printer availability
        self.test_printer_connection()
        
        # Start authentication event monitor thread
        self.auth_monitor = AuthEventMonitor(self.communicator)
        self.communicator.new_auth_event.connect(self.add_auth_event)
        self.auth_monitor.start()
        
        # Load header/footer settings from appSettings.json if available
        try:
            with open('appSettings.json', 'r') as f:
                app_settings = json.load(f)
                printer_config = app_settings.get('PrinterConfig', {})
                self.header = printer_config.get('Header', {'enable': True, 'text': "EzeeCanteen"})
                self.footer = printer_config.get('Footer', {'enable': True, 'text': "Thank you!"})
                self.special_message = app_settings.get('CanteenMenu', {}).get('SpecialMessage', "")
        except Exception as e:
            logging.error(f"Error loading header/footer settings: {e}")
            self.header = {'enable': True, 'text': "EzeeCanteen"}
            self.footer = {'enable': True, 'text': "Thank you!"}
    
    def test_printer_connections(self):
        """Test all configured printer connections"""
        if not self.device_printers:
            # Legacy mode - test the single printer
            self.test_printer_connection()
            return
            
        # Get unique printer IPs to avoid testing the same printer multiple times
        unique_printers = {}
        for device_ip, printer in self.device_printers.items():
            printer_key = f"{printer['ip']}:{printer['port']}"
            if printer_key not in unique_printers:
                unique_printers[printer_key] = {
                    'ip': printer['ip'],
                    'port': printer['port'],
                    'devices': []
                }
            unique_printers[printer_key]['devices'].append(device_ip)
        
        # Test each unique printer
        logging.info(f"Testing {len(unique_printers)} unique printer connections")
        for printer_key, printer_info in unique_printers.items():
            try:
                # Check printer connection with short timeout
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)  # 0.5 second timeout for faster checks
                result = s.connect_ex((printer_info['ip'], printer_info['port']))
                s.close()
                
                available = (result == 0)
                
                # Update availability for all devices using this printer
                for device_ip in printer_info['devices']:
                    if device_ip in self.device_printers:
                        self.device_printers[device_ip]['available'] = available
                
                if available:
                    logging.info(f"Printer {printer_info['ip']}:{printer_info['port']} connection successful (for {len(printer_info['devices'])} devices)")
                else:
                    logging.warning(f"Printer {printer_info['ip']}:{printer_info['port']} connection failed (for {len(printer_info['devices'])} devices)")
            except Exception as e:
                # Handle socket errors gracefully
                logging.error(f"Error testing printer {printer_info['ip']}:{printer_info['port']}: {e}")
                for device_ip in printer_info['devices']:
                    if device_ip in self.device_printers:
                        self.device_printers[device_ip]['available'] = False
        else:
            # Legacy mode - test the single printer
            self.test_printer_connection()
            
    def test_printer_connection(self):
        """Legacy method to test single printer connection"""
        self.printer_available = False
        
        try:
            # Load printer settings if not already loaded
            if not hasattr(self, 'printer_ip') or not hasattr(self, 'printer_port'):
                try:
                    with open('appSettings.json', 'r') as f:
                        app_settings = json.load(f)
                        printer_config = app_settings.get('PrinterConfig', {})
                        self.printer_ip = printer_config.get('IP', "192.168.0.253")
                        self.printer_port = printer_config.get('Port', 9100)
                        self.header = printer_config.get('Header', {'enable': True, 'text': "EzeeCanteen"})
                        self.footer = printer_config.get('Footer', {'enable': True, 'text': "Thank you!"})
                        logging.info(f"Loaded printer config: IP={self.printer_ip}, Port={self.printer_port}")
                except Exception as e:
                    self.printer_ip = "192.168.0.253"
                    self.printer_port = 9100
                    self.header = {'enable': True, 'text': "EzeeCanteen"}
                    self.footer = {'enable': True, 'text': "Thank you!"}
                    logging.error(f"Error loading printer settings: {e}")
            
            # Check printer connection with timeout
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)  # 1 second timeout
            result = s.connect_ex((self.printer_ip, self.printer_port))
            s.close()
            
            if result == 0:
                self.printer_available = True
                logging.info(f"Printer connection successful ({self.printer_ip}:{self.printer_port})")
            else:
                logging.warning(f"Printer connection failed ({self.printer_ip}:{self.printer_port})")
        except Exception as e:
            logging.error(f"Error testing printer connection: {e}")
        
    def test_db_connection(self):
        """Test the database connection and set a flag if it's not available"""
        self.db_available = False
        try:
            logging.info(f"Testing database connection to {DB_HOST}:{DB_PORT}")
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            if conn.is_connected():
                self.db_available = True
                logging.info("Database connection successful")
                conn.close()
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            print("Program will continue without database functionality")
        
    def insert_to_database(self, event_data):
        print("event_data",event_data)
        """Insert authentication data into the database"""
        # if not hasattr(self, 'db_available') or not self.db_available:
        #     print("Skipping database insertion - database not available")
        #     return
            
        try:
            # Connect to the database
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            
            # Create a cursor
            cursor = conn.cursor()
            
            # Extract data from the event
            emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', ''))
            
            # Process datetime
            event_time = event_data.get('time', datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'))
            if 'T' in event_time:
                # Format: 2023-05-15T14:30:45+05:30 -> 2023-05-15 14:30:45
                punch_datetime = event_time.replace('T', ' ').split('+')[0]
            else:
                punch_datetime = event_time
            
            # Get picture URL
            punch_pic_url = event_data.get('pictureURL', '')
            
            # Get recognition mode (1=Card, 38=Fingerprint, others as face)
            minor = event_data.get('minor', 0)
            if minor == 1:
                recognition_mode = "Card"
            elif minor == 38:
                recognition_mode = "Fingerprint"
            elif minor == 75:
                recognition_mode = "Face"
            else:
                recognition_mode = "Unknown"  # This should never happen due to earlier check in add_auth_event
            
            # Determine meal type based on current time
            current_time = datetime.now().strftime('%H:%M')
            meal_type = "MEAL"  # Default value
            
            # Read meal schedule from appSettings.json
            try:
                with open('appSettings.json', 'r') as f:
                    app_settings = json.load(f)
                    meal_schedule = app_settings.get('CanteenMenu', {}).get('MealSchedule', [])
                    
                    # Check which meal time range the current time falls into
                    for meal in meal_schedule:
                        from_time = meal.get('fromTime', '')
                        to_time = meal.get('toTime', '')
                        meal_type_value = meal.get('mealType', '')
                        price = meal.get('price', '0')
                        
                        if from_time and to_time and meal_type_value and from_time <= current_time <= to_time:
                            meal_type = meal_type_value.upper()
                            total_price = price
                            break
                    else:
                        # If no meal matches, default price is 0
                        total_price = '0'
            except Exception as e:
                logging.error(f"Error determining meal type for database: {e}")
                # Use fallback logic for meal type determination
                current_hour = datetime.now().hour
                if 6 <= current_hour < 11:
                    meal_type = "BREAKFAST"
                elif 11 <= current_hour < 15:
                    meal_type = "LUNCH"
                elif 15 <= current_hour < 18:
                    meal_type = "SNACKS"
                elif 18 <= current_hour < 22:
                    meal_type = "DINNER"
                total_price = '0'  # Default price if we can't determine from settings
            
            # Get attendance status
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                attendance_status = att.get('attendanceStatus', None)
                att_in_out = att.get('labelName', None)
                
                # Update special message from app settings
                try:
                    with open('appSettings.json', 'r') as f:
                        app_settings = json.load(f)
                        self.special_message = app_settings.get('CanteenMenu', {}).get('SpecialMessage', "")
                except Exception as e:
                    print(f"Error loading special message: {e}")
                    if attendance_status:
                        self.special_message = f"Status: {attendance_status}"
            else:
                attendance_status = None
                att_in_out = None
            
            # Determine which device IP to use
            device_ip = None
            
            # Try to match based on auth_monitor IP in each monitor
            if hasattr(self, 'active_devices') and self.active_devices:
                # Try to identify which device generated this event
                for ip, device_info in self.active_devices.items():
                    monitor = device_info['monitor']
                    if monitor.ip == getattr(event_data, 'deviceIP', None):
                        device_ip = ip
                        break
                
                if not device_ip:
                    # If we couldn't determine the source, use the first active device
                    device_ip = next(iter(self.active_devices))
            else:
                # Legacy mode - use the global IP
                device_ip = IP
            
            # Prepare SQL query
            sql = f"""
                INSERT INTO {DB_TABLE} (
                    PunchCardNo, PunchDateTime, PunchPicURL, RecognitionMode, 
                    IPAddress, AttendanceStatus, DB, AttInOut, Inserted, ZK_SerialNo, LogTransferDate, CanteenMode,
                    Fooditem, totalAmount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Get device serial based on which device generated the event
            serial_no = ""
            if hasattr(self, 'active_devices') and device_ip in self.active_devices:
                serial_no = self.active_devices[device_ip]['serial']
            else:
                # Legacy mode - use the global device_serial
                serial_no = getattr(self, 'device_serial', '')
            
            if not serial_no:
                serial_no = event_data.get('serialNo', '')
            
            # Prepare values
            values = (
                int(emp_id) if emp_id.isdigit() else 0,  # PunchCardNo
                punch_datetime,                         # PunchDateTime
                punch_pic_url,                          # PunchPicURL
                recognition_mode,                       # RecognitionMode
                device_ip,                              # IPAddress - Use the actual device IP
                attendance_status,                      # AttendanceStatus
                DB_NAME,                                # DB
                att_in_out,                             # AttInOut
                'Y',                                    # Inserted
                serial_no,                              # ZK_SerialNo
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # LogTransferDate
                'timeBase',                             # CanteenMode
                meal_type,                              # Fooditem
                total_price                             # totalAmount
            )
            
            # Execute query
            cursor.execute(sql, values)
            
            # Commit the transaction
            conn.commit()
            
            print(f"Successfully inserted authentication data for employee {emp_id} with meal type {meal_type} into database")
            
        except Exception as e:
            print(f"Error inserting data into database: {e}")
            logging.error(f"Database insertion error: {e}")
            
        finally:
            # Close cursor and connection
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("EzeeCanteen")
        self.setGeometry(100, 100, 1000, 700)  # Larger window
        
        # Set background color
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1b2a;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 6px;
                border: 1px solid #1c2e4a;
            }
        """)
        
        # Apply shadow effect to header
        header_shadow = QGraphicsDropShadowEffect(header_frame)
        header_shadow.setBlurRadius(10)
        header_shadow.setColor(QColor(0, 0, 0, 70))
        header_shadow.setOffset(0, 2)
        header_frame.setGraphicsEffect(header_shadow)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Time display
        self.time_display = TimeDisplay()
        self.time_display.setMinimumWidth(150)
        
        # Title display with lock icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        lock_icon = QLabel()
        lock_icon_path = "lock.png"  # Replace with path to an actual lock icon file if available
        lock_pixmap = QPixmap(lock_icon_path) if QFile.exists(lock_icon_path) else None
        
        if lock_pixmap and not lock_pixmap.isNull():
            lock_icon.setPixmap(lock_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lock_icon.setText("")
        
        lock_icon.setStyleSheet("background: transparent;")
        
        title_label = QLabel("Live Display | EzeeCanteen")
        title_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        title_label.setFont(QFont("Arial", 20))
        title_label.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(lock_icon)
        title_layout.addWidget(title_label)
        title_layout.setAlignment(Qt.AlignCenter)
        
        # Settings button
        settings_button = QPushButton()
        settings_icon_path = "settings.png"  # Replace with path to an actual settings icon file if available
        settings_pixmap = QPixmap(settings_icon_path) if QFile.exists(settings_icon_path) else None
        
        if settings_pixmap and not settings_pixmap.isNull():
            settings_button.setIcon(QIcon(settings_pixmap))
            settings_button.setIconSize(QSize(20, 20))
        else:
            settings_button.setText("⚙")
            settings_button.setFont(QFont("Arial", 16))
        
        settings_button.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: #1c2e4a;
                border-radius: 4px;
                padding: 5px;
                border: 1px solid #253649;
            }
            QPushButton:hover {
                background-color: #253649;
            }
        """)
        settings_button.setFixedSize(36, 36)
        settings_button.clicked.connect(self.open_settings)
        
        # Add widgets to header layout
        header_layout.addWidget(self.time_display)
        header_layout.addWidget(title_container, 1)
        header_layout.addWidget(settings_button)
        
        # Create a scroll area for the grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # Always show vertical scrollbar
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent; 
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #1c2e4a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #34495e;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3498db;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Grid container with background
        grid_container = QFrame()
        grid_container.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 6px;
                border: 1px solid #1c2e4a;
            }
        """)
        
        # Apply shadow effect to grid container
        grid_shadow = QGraphicsDropShadowEffect(grid_container)
        grid_shadow.setBlurRadius(10)
        grid_shadow.setColor(QColor(0, 0, 0, 70))
        grid_shadow.setOffset(0, 2)
        grid_container.setGraphicsEffect(grid_shadow)
        
        grid_layout = QVBoxLayout(grid_container)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Align content to top-left
        
        # Grid for content
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(4)  # Reduced spacing between items
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Align grid items to top-left
        
        grid_layout.addWidget(self.grid_widget)
        
        # Add grid container to scroll area
        scroll_area.setWidget(grid_container)
        
        # Footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 6px;
                border: 1px solid #1c2e4a;
            }
        """)
        footer_frame.setMaximumHeight(40)
        
        # Apply shadow effect to footer
        footer_shadow = QGraphicsDropShadowEffect(footer_frame)
        footer_shadow.setBlurRadius(10)
        footer_shadow.setColor(QColor(0, 0, 0, 70))
        footer_shadow.setOffset(0, 2)
        footer_frame.setGraphicsEffect(footer_shadow)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(15, 5, 15, 5)
        
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        footer_label.setAlignment(Qt.AlignCenter)
        
        footer_layout.addStretch()
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        
        # Add sections to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(footer_frame)
    
    def add_auth_event(self, event_data):
        """Add a new authentication event to the grid and print a token"""
        # Check if the minor value is one of the supported authentication types
        minor = event_data.get('minor', 0)
        if minor not in [1, 38, 75]:
            print(f"Skipping event with unsupported minor value: {minor}")
            return
        
        # Add event to the list
        if(event_data.get('employeeNoString')):
            print(f"event_data{event_data}\n\n")
            self.events.insert(0, event_data)
            
            # Process disable punch logic - check if DisablePunch is enabled
            try:
                with open('appSettings.json', 'r') as f:
                    app_settings = json.load(f)
                    disable_punch = app_settings.get('CanteenMenu', {}).get('DisablePunch', False)
                    
                    if disable_punch:
                        # Get employee ID
                        emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', None))
                        emp_name = event_data.get('name', None)
                        print("THOS IOS TJHE OMNAME OF TJHE EM<PT: ", emp_name)
                        print(f"\n----------------------------------------\nemp_name: {emp_name}\nemp_id: {emp_id}\n----------------------------------------\n")
                        if emp_id and emp_name:
                            print("BOTHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
                            self.update_user_begin_time(emp_id, emp_name, app_settings)
                        elif emp_id:
                            print("SINGLEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
                            self.update_user_begin_time(emp_id, app_settings)
                        else:
                            print(f"No employee ID or name found for event data: {event_data}")

            except Exception as e:
                logging.error(f"Error processing DisablePunch feature: {e}")
            
            # Insert data into database
            self.insert_to_database(event_data)
            
            # Check if day has changed to reset token counter
            today = datetime.now().date()
            if today != self.current_date:
                self.token_counter = 0
                self.current_date = today
            
            # Generate and print token
            self.token_counter += 1
            
            # Extract data for token
            emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', 'N/A'))
            name = event_data.get('name', 'N/A')
            punch_time = event_data.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Format punch time if needed
            if 'T' in punch_time:
                punch_time = punch_time.replace('T', ' ').split('+')[0]
            
            # Determine coupon type based on current time from appSettings.json
            try:
                current_time = datetime.now().strftime('%H:%M')
                coupon_type = "MEAL"  # Default value
                
                # Read meal schedule from appSettings.json
                with open('appSettings.json', 'r') as f:
                    app_settings = json.load(f)
                    meal_schedule = app_settings.get('CanteenMenu', {}).get('MealSchedule', [])
                    self.special_message = app_settings.get('CanteenMenu', {}).get('SpecialMessage', "")
                
                # Get header and footer if not already loaded
                if not hasattr(self, 'header') or not hasattr(self, 'footer'):
                    printer_config = app_settings.get('PrinterConfig', {})
                    self.header = printer_config.get('Header', {'enable': True, 'text': "EzeeCanteen"})
                    self.footer = printer_config.get('Footer', {'enable': True, 'text': "Thank you!"})
            
                # Check which meal time range the current time falls into
                for meal in meal_schedule:
                    from_time = meal.get('fromTime', '')
                    to_time = meal.get('toTime', '')
                    meal_type = meal.get('mealType', '')
                    
                    if from_time and to_time and meal_type and from_time <= current_time <= to_time:
                        coupon_type = meal_type.upper()
                        break
            except Exception as e:
                # Fallback to hardcoded values if there's an error
                current_hour = datetime.now().hour
                if 6 <= current_hour < 11:
                    coupon_type = "BREAKFAST"
                elif 11 <= current_hour < 15:
                    coupon_type = "LUNCH"
                elif 15 <= current_hour < 18:
                    coupon_type = "SNACKS"
                elif 18 <= current_hour < 22:
                    coupon_type = "DINNER"
                else:
                    coupon_type = "MEAL"
                print(f"Error determining meal type from settings: {e}")
            
            # Get attendance status if available
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                status = att.get('attendanceStatus', '')
                if status:
                    # Update special message from app settings
                    try:
                        with open('appSettings.json', 'r') as f:
                            app_settings = json.load(f)
                            self.special_message = app_settings.get('CanteenMenu', {}).get('SpecialMessage', "")
                    except Exception as e:
                        print(f"Error loading special message: {e}")
                        self.special_message = f"Status: {status}"
            
            # Determine which device generated this event (to find the correct printer)
            source_ip = None
            printer_ip = None
            printer_port = None
            
            # First check if source_device_ip is directly available in the event data
            if 'source_device_ip' in event_data:
                source_ip = event_data['source_device_ip']
                logging.info(f"Using source device IP from event data: {source_ip}")
            # If source_device_ip is not in event data, try to determine it from deviceIP
            elif 'deviceIP' in event_data:
                device_ip = event_data['deviceIP']
                # Try to find a matching device in active_devices
                if hasattr(self, 'active_devices') and self.active_devices:
                    for active_ip, device_info in self.active_devices.items():
                        monitor = device_info['monitor']
                        if monitor.ip == device_ip:
                            source_ip = active_ip
                            logging.info(f"Matched device IP {device_ip} to active device {source_ip}")
                            break
            
            # If we still don't have a source IP but have active devices, use the first one
            if not source_ip and hasattr(self, 'active_devices') and self.active_devices:
                source_ip = next(iter(self.active_devices))
                logging.warning(f"Could not determine source device for event. Using {source_ip}")
            
            # Check if printer is available and print token
            printer_available = False
            
            # If we have a source IP and it's in our device_printers map, use that printer
            if source_ip and source_ip in self.device_printers:
                # Use the printer associated with this device
                printer = self.device_printers[source_ip]
                printer_available = printer['available']
                printer_ip = printer['ip']
                printer_port = printer['port']
                logging.info(f"Using printer {printer_ip}:{printer_port} for device {source_ip}")
            # Legacy fallback - if no device-specific printer found but we have a default printer
            elif hasattr(self, 'printer_available') and self.printer_available:
                # Legacy mode - use the single printer
                printer_available = self.printer_available
                printer_ip = self.printer_ip
                printer_port = self.printer_port
                logging.info(f"Using legacy printer {printer_ip}:{printer_port}")
            
            # Log the printer selection information
            print(f"Device source: {source_ip}")
            print(f"Selected printer: {printer_ip}:{printer_port}")
            print(f"Printer available: {printer_available}")
            
            # Attempt to print token if printer is available
            if printer_available and printer_ip and printer_port:
                try:
                    # Double-check printer is still available with short timeout
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)  # 0.5 second timeout
                    result = s.connect_ex((printer_ip, printer_port))
                    s.close()
                    
                    if result == 0:
                        # Printer is available, print the token
                        print_slip(  
                            printer_ip, 
                            printer_port, 
                            0, 
                            self.header if hasattr(self, 'header') else {'enable': True, 'text': "EzeeCanteen"}, 
                            coupon_type, 
                            emp_id, 
                            name, 
                            punch_time, 
                            self.special_message if hasattr(self, 'special_message') else "", 
                            self.footer if hasattr(self, 'footer') else {'enable': True, 'text': "Thank you!"}
                        )
                        print(f"Token {self.token_counter} printed for {name} on printer {printer_ip}:{printer_port}")
                    else:
                        print(f"Skipping print - printer not available at {printer_ip}:{printer_port}")
                        # Update printer availability status
                        if source_ip and source_ip in self.device_printers:
                            self.device_printers[source_ip]['available'] = False
                        else:
                            self.printer_available = False
                except Exception as e:
                    print(f"Error printing token: {e}")
                    # Update printer availability status
                    if source_ip and source_ip in self.device_printers:
                        self.device_printers[source_ip]['available'] = False
                    else:
                        self.printer_available = False
            else:
                print(f"Skipping print - no printer available for this device")
        
            # Only modify the grid to add the new event instead of rebuilding the entire grid
            # Check if grid_layout still exists and is valid
            if not hasattr(self, 'grid_layout') or sip.isdeleted(self.grid_layout):
                return
            
            # Determine number of columns based on window width
            window_width = self.width()
            
            # Determine columns based on window width - adjusted to fit more items
            if window_width >= 1600:
                cols = 7  # More columns for very wide windows
            elif window_width >= 1280:
                cols = 6  # 6 columns in wide window
            elif window_width >= 900:
                cols = 5  # 5 columns in medium window
            elif window_width >= 768:
                cols = 4  # 4 columns in smaller medium window
            else:
                cols = 3  # 3 columns in small window
            
            # Create new event item
            new_event_item = AuthEventItem(event_data)
            
            # Shift all existing items in the grid one position
            total_items = self.grid_layout.count()
            if total_items > 0:
                # Start from the last item and move each item one position forward
                for i in range(total_items - 1, -1, -1):
                    item = self.grid_layout.itemAt(i)
                    if item and item.widget():
                        old_row = i // cols
                        old_col = i % cols
                        new_row = (i + 1) // cols
                        new_col = (i + 1) % cols
                        
                        # If we've reached the max events limit, remove the last widget
                        if i == total_items - 1 and total_items >= self.max_events:
                            widget = self.grid_layout.itemAt(i).widget()
                            self.grid_layout.removeItem(item)
                            if widget:
                                widget.deleteLater()
                        else:
                            # Move widget to new position
                            widget = item.widget()
                            self.grid_layout.removeItem(item)
                            self.grid_layout.addWidget(widget, new_row, new_col)
                            self.grid_layout.setAlignment(widget, Qt.AlignTop | Qt.AlignLeft)
            
            # Add the new item at the first position
            self.grid_layout.addWidget(new_event_item, 0, 0)
            self.grid_layout.setAlignment(new_event_item, Qt.AlignTop | Qt.AlignLeft)
            
            # Limit the number of events
            if len(self.events) > self.max_events:
                self.events = self.events[:self.max_events]
        
            # Print to console for debugging
            print("\n========== NEW AUTHENTICATION ==========")
            print(f"Time: {event_data.get('time')}")
            print(f"Employee No: {event_data.get('employeeNoString', event_data.get('employeeNo', 'N/A'))}")
            print(f"Name: {event_data.get('name', 'N/A')}")
            print(f"FaceURL: {event_data.get('pictureURL', 'N/A')}")
            
            # Check for attendance info
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                print(f"Attendance Status: {att.get('attendanceStatus', 'N/A')}")
                print(f"Label: {att.get('labelName', 'N/A')}")
            
            print("======================================")
        else:
            # If the event doesn't have an employee number, we might still need to update the grid
            # Limit the number of events
            if len(self.events) > self.max_events:
                self.events = self.events[:self.max_events]
    
    def update_user_begin_time(self, employee_no, employee_name, app_settings):
        """Update the user's begin time to the next meal time"""
        try:
            # Get current time
            current_time = datetime.now()
            current_time_str = current_time.strftime('%H:%M')
            current_date = current_time.strftime('%Y-%m-%dT')
            
            # Get meal schedule
            meal_schedule = app_settings.get('CanteenMenu', {}).get('MealSchedule', [])
            if not meal_schedule:
                logging.warning("No meal schedule found - cannot update begin time")
                return
            
            # Sort meal schedule by time
            meal_schedule.sort(key=lambda x: x.get('fromTime', '00:00'))
            
            # Find the next meal time
            next_meal = None
            for meal in meal_schedule:
                from_time = meal.get('fromTime', '')
                if from_time and from_time > current_time_str:
                    next_meal = meal
                    break
            
            if next_meal:
                # Use today's date with the next meal time - format: YYYY-MM-DDThh:mm:ss
                next_begin_time = f"{current_date}{next_meal.get('fromTime', '00:00')}:00"
            else:
                # Use tomorrow's date with the first meal time of the day
                tomorrow = current_time + timedelta(days=1)
                tomorrow_date = tomorrow.strftime('%Y-%m-%dT')
                # Use the first meal from the schedule for tomorrow
                first_meal = meal_schedule[0]
                next_begin_time = f"{tomorrow_date}{first_meal.get('fromTime', '00:00')}:00"
            
            logging.info(f"Setting begin time for employee {employee_no} to {next_begin_time}")
            
            # Determine which device to use for updating user
            device_ip = None
            device_auth = None
            
            # If we have multiple devices configured
            if hasattr(self, 'active_devices') and self.active_devices:
                # Try to identify which device generated this event or use the first one
                device_ip = next(iter(self.active_devices))
                device_info = self.active_devices[device_ip]
                device_auth = {
                    'ip': device_info['monitor'].ip,
                    'port': device_info['monitor'].port,
                    'user': device_info['monitor'].username,
                    'password': device_info['monitor'].password
                }
            else:
                # Legacy mode - use the global values
                device_auth = {
                    'ip': IP,
                    'port': PORT,
                    'user': USERNAME,
                    'password': PASSWORD
                }
            
            # Construct base URL
            base_url = f"http://{device_auth['ip']}:{device_auth['port']}"
            
            print(f"base_url: {base_url}")
            print(f"device_auth: {device_auth}")
            print(f"employee_no: {employee_no}")
            print(f"next_begin_time: {next_begin_time}")
            # Call the API function to update the user's begin time
            result = modify_user_begin_time(
                base_url, 
                device_auth['user'], 
                device_auth['password'], 
                employee_no, 
                next_begin_time,
                employee_name
            )
            print(f"\n----------------------------------------\nTime updated result: {result}\n----------------------------------------\n")
            logging.info(f"User begin time update result: {result}")
            
        except Exception as e:
            logging.error(f"Error updating user begin time: {e}")
            
    def open_settings(self):
        """Function to handle settings button click"""
        logging.info("Settings button clicked - stopping authentication monitor")
        try:
            # Stop the authentication monitor
            if hasattr(self, 'auth_monitor'):
                self.communicator.stop_server.emit()
                
                # Give the monitor a moment to process the stop signal
                QTimer.singleShot(100, self._continue_to_settings)
            else:
                self._continue_to_settings()
        except Exception as e:
            logging.error(f"Error stopping authentication monitor: {e}")
            self._continue_to_settings()
    
    def _continue_to_settings(self):
        """Continue with opening settings after stopping monitor"""
        try:
            # Check if we're in settings mode
            if self.settings_mode and self.parent_window:
                # If we are, recreate the settings UI
                try:
                    from settings import main as settings_main
                    new_settings_widget = settings_main()
                    
                    # Set new settings widget as central widget of parent
                    self.parent_window.setCentralWidget(new_settings_widget)
                    
                    # No need to close this instance as it will be removed by setCentralWidget
                except Exception as e:
                    logging.error(f"Error recreating settings view: {e}")
                    # Fall back to closing ourselves if there's an error
                    self.close()
                    os.system("python settings.py")
                return
            
            # If not in settings mode, try to load the settings UI in the same window
            try:
                # Save current window geometry
                geometry = self.geometry()
                
                # Import the settings module and get settings window
                from settings import main as settings_main
                settings_window = settings_main()
                
                # Set settings as central widget
                self.setCentralWidget(settings_window)
                
                # Restore window geometry
                self.setGeometry(geometry)
                
            except Exception as e:
                logging.error(f"Error loading settings view: {e}")
                # If there's an error, fall back to the original approach
                self.close()
                os.system("python settings.py")
        except Exception as e:
            logging.error(f"Unexpected error opening settings: {e}")
            # Ultimate fallback
            self.close()
            os.system("python settings.py")
    
    def clear_grid(self):
        """Clear all items from the grid layout"""
        # Check if grid_layout still exists and is valid
        if not hasattr(self, 'grid_layout') or sip.isdeleted(self.grid_layout):
            return
            
        # Mark all widgets as deleted before removing them
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                if hasattr(item.widget(), 'is_deleted'):
                    item.widget().is_deleted = True
        
        # Then remove them
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    
    def populate_grid(self):
        """Populate grid with authentication events"""
        # Check if grid_layout still exists and is valid
        if not hasattr(self, 'grid_layout') or sip.isdeleted(self.grid_layout):
            return
            
        # Determine number of columns based on window width
        window_width = self.width()
        
        # Determine columns based on window width - adjusted to fit more items
        if window_width >= 1600:
            cols = 7  # More columns for very wide windows
        elif window_width >= 1280:
            cols = 6  # 6 columns in wide window
        elif window_width >= 900:
            cols = 5  # 5 columns in medium window
        elif window_width >= 768:
            cols = 4  # 4 columns in smaller medium window
        else:
            cols = 3  # 3 columns in small window
        
        # Reduce spacing for tighter layout
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Ensure top-left alignment
        
        # Populate grid
        for i, event in enumerate(self.events):
            row = i // cols
            col = i % cols
            
            event_item = AuthEventItem(event)
            self.grid_layout.addWidget(event_item, row, col)
            # Reset the alignment for each widget to ensure they fill their cells
            self.grid_layout.setAlignment(event_item, Qt.AlignTop | Qt.AlignLeft)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop monitoring authentication events
        self.communicator.stop_server.emit()
        
        # Stop all active device monitors
        if hasattr(self, 'active_devices'):
            for device_ip, device_info in self.active_devices.items():
                monitor = device_info['monitor']
                if monitor and monitor.isRunning():
                    try:
                        monitor.stop()
                        if not monitor.wait(1000):  # 1 second timeout
                            monitor.terminate()
                            monitor.wait()
                        logging.info(f"Stopped monitor for device {device_ip}")
                    except Exception as e:
                        logging.error(f"Error stopping monitor for device {device_ip}: {e}")
        
        # Stop printer check timer
        if hasattr(self, 'printer_check_timer') and self.printer_check_timer.isActive():
            self.printer_check_timer.stop()
        
        # If we're in settings mode, we should let the parent handle cleanup
        if not self.settings_mode:
            # Clean up temp directory only if not in settings mode
            try:
                if os.path.exists(TEMP_DIR):
                    shutil.rmtree(TEMP_DIR)
                    print(f"Removed temporary image directory: {TEMP_DIR}")
            except Exception as e:
                print(f"Error removing temp directory: {e}")
            
        event.accept()

    def resizeEvent(self, event):
        """Handle window resize events to refresh the grid layout"""
        super().resizeEvent(event)
        
        # Don't refresh immediately during resize to avoid performance issues
        if not self.resized:
            self.resized = True
            QTimer.singleShot(200, self.refresh_grid)

    def refresh_grid(self):
        """Refresh the grid layout when window size changes"""
        self.resized = False
        
        # Check if widget is still valid before accessing it
        if not hasattr(self, 'grid_layout') or sip.isdeleted(self.grid_layout):
            return
            
        if self.events:
            self.clear_grid()
            self.populate_grid()

def main():
    # Only create app if this is run as a standalone program
    standalone = __name__ == '__main__'
    
    # Initialize logging
    try:
        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Configure logging with rotating file handler
        log_file = os.path.join(logs_dir, 'ezecanteen.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logging.info("EzeeCanteen application starting")
    except Exception as e:
        print(f"Error initializing logging: {e}")
    
    if standalone:
        app = QApplication(sys.argv)
    
    # Create temp directory if it doesn't exist
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created temporary directory for images: {TEMP_DIR}")
        logging.info(f"Created temporary directory for images: {TEMP_DIR}")
        
    window = EzeeCanteen()
    
    if standalone:
        window.show()
        
        # Make sure to clean up temp directory even if the app crashes or is terminated
        try:
            sys.exit(app.exec_())
        finally:
            if os.path.exists(TEMP_DIR):
                try:
                    shutil.rmtree(TEMP_DIR)
                    print(f"Cleaned up temporary image directory: {TEMP_DIR}")
                    logging.info(f"Cleaned up temporary image directory: {TEMP_DIR}")
                except:
                    pass
    else:
        return window
        
if __name__ == '__main__':
    main()
        