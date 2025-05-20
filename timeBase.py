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
IP = "192.168.0.872"
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

# Function to fetch device configuration from the database
def fetch_device_config():
    """Fetch device configuration from the database"""
    global IP, PORT, USERNAME, PASSWORD
    
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
        
        # Fetch the default device configuration with password decryption
        # Using the decryption method specified
        query = """
            SELECT IP, Port, DeviceLocation, ComUser, 
                   AES_DECRYPT(comKey, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) as Pwd
            FROM configh
            WHERE DeviceType != 'Printer' AND Enable = 'Y'
            ORDER BY DeviceNumber
            LIMIT 1
        """
        
        cursor.execute(query)
        device = cursor.fetchone()
        
        if device:
            # Update global variables with values from database
            IP = device['IP']
            PORT = device['Port'] if device['Port'] else 80  # Default to 80 if null
            USERNAME = device['ComUser'] if device['ComUser'] else "admin"  # Default values if null
            
            # Handle the decrypted password - it might be bytes or None
            if device['Pwd'] is not None:
                try:
                    # Convert bytes to string if needed
                    if isinstance(device['Pwd'], bytes):
                        PASSWORD = device['Pwd'].decode('utf-8')
                    else:
                        PASSWORD = str(device['Pwd'])
                except Exception as e:
                    logging.error(f"Error decoding password: {e}")
                    # Keep default password if decoding fails
            
            logging.info(f"Loaded device configuration from database: {IP}:{PORT}")
            print(f"Device configuration loaded from database: {IP}:{PORT}")
        else:
            logging.warning("No enabled device found in database, using default values")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        print(f"Error fetching device configuration: {err}")
        print("Using default device configuration")
    except Exception as e:
        logging.error(f"Unexpected error loading device configuration: {e}")
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
    print(f"Device Server: {IP}:{PORT}")
    print(f"Database Server: {DB_HOST}:{DB_PORT}")
    
    # Try to get printer IP from appSettings.json
    try:
        with open('appSettings.json', 'r') as f:
            app_settings = json.load(f)
            printer_config = app_settings.get('PrinterConfig', {})
            printer_ip = printer_config.get('IP', "192.168.0.251")
            printer_port = printer_config.get('Port', 9100)
            print(f"Printer Server: {printer_ip}:{printer_port}")
    except Exception as e:
        print(f"Printer Server: Unknown (Error: {e})")
    
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
        logging.info(f"Getting device details for {ip}:{port} with user: {user}, password length: {len(psw)}")
       
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
    def __init__(self, communicator):
        super().__init__()
        self.communicator = communicator
        self.running = True
        self.communicator.stop_server.connect(self.stop)
        
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
        
        # Use the global configuration
        self.ip = IP
        self.port = PORT
        self.username = USERNAME
        self.password = PASSWORD
        
        # URL for access control events
        self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
        logging.info(f"AuthEventMonitor initialized with endpoint: {self.url}")
        
        # Keep track of processed events
        self.processed_events = set()
    
    def check_time_range(self):
        """Check if current time is within the specified meal time range"""
        if not self.from_time_str or not self.to_time_str:
            return True  # If no time range specified, always proceed
            
        current_time = datetime.now().strftime('%H:%M')
        return self.from_time_str <= current_time <= self.to_time_str
    
    def run(self):
        """Main monitoring loop"""
        logging.info("Auth event monitoring started")
        while self.running:
            if not self.check_time_range():
                # Sleep for a minute before checking the time range again
                time.sleep(60)
                continue
                
            try:
                # Set time range (last 30 seconds)
                end_time = datetime.now() 
                start_time = end_time - timedelta(seconds=30)
                
                # Format times with timezone
                end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                
                # Create payload for authentication events
                payload = {
                    "AcsEventCond": {
                        "searchID": "1",
                        "searchResultPosition": 0,
                        "maxResults": 10,
                        "major": 5,  # Access Control
                        "minor": 0,  # Authentication passed
                        "startTime": start_time_str,
                        "endTime": end_time_str
                    }
                }
                
                # Make the request
                response = requests.post(
                    self.url,
                    json=payload,
                    auth=HTTPDigestAuth(self.username, self.password),
                    timeout=15,
                    headers={'Content-Type': 'application/json'}
                )
                
                # Process successful responses
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Extract event information if available
                        if "AcsEvent" in data:
                            info_list = data["AcsEvent"].get("InfoList", [])
                            
                            # Process each event
                            for event in info_list:
                                event_time = event.get('time')
                                event_id = f"{event.get('employeeNoString', event.get('employeeNo', 'N/A'))}-{event_time}"
                                
                                # Check if this is a new event we haven't processed yet
                                if event_id not in self.processed_events:
                                    self.processed_events.add(event_id)
                                    
                                    # Log the new authentication event
                                    emp_id = event.get('employeeNoString', event.get('employeeNo', 'N/A'))
                                    name = event.get('name', 'N/A')
                                    logging.info(f"New authentication event: Employee ID={emp_id}, Name={name}, Time={event_time}")
                                    
                                    # Emit signal with event data
                                    self.communicator.new_auth_event.emit(event)
                            
                            # Limit the size of processed_events to avoid memory issues
                            if len(self.processed_events) > 1000:
                                # Keep only the most recent 500 events
                                self.processed_events = set(list(self.processed_events)[-500:])
                                logging.info("Pruned processed events cache to 500 entries")
                    
                    except json.JSONDecodeError:
                        logging.error("Response is not valid JSON")
                        
            except requests.exceptions.Timeout:
                logging.error(f"Timeout connecting to {self.ip}:{self.port}")
            except requests.exceptions.ConnectionError:
                logging.error(f"Connection error for {self.ip}:{self.port}. Device may be offline or unreachable.")
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
            
            # Sleep for a short period before the next check
            time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread"""
        logging.info("Auth event monitoring stopped")
        self.running = False
        self.quit()
        self.wait()

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
            
            # Use requests with digest authentication instead of urllib
            response = requests.get(
                url,
                auth=HTTPDigestAuth(USERNAME, PASSWORD),
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
        self.init_ui()
        
        # Get device details
        self.device_serial, self.device_mac = getDeviceDetails(IP, PORT, USERNAME, PASSWORD)
        logging.info(f"Device details initialized: Serial={self.device_serial}, MAC={self.device_mac}")
        
        # Test database connection
        self.test_db_connection()
        
        # Test printer availability
        self.test_printer_connection()
        
        # Connect resize event to refresh grid
        self.resized = False
        
        # Start authentication event monitor thread
        self.auth_monitor = AuthEventMonitor(self.communicator)
        self.communicator.new_auth_event.connect(self.add_auth_event)
        self.auth_monitor.start()
        
        # Load printer settings from appSettings.json if available
        try:
            with open('appSettings.json', 'r') as f:
                app_settings = json.load(f)
                printer_config = app_settings.get('PrinterConfig', {})
                self.printer_ip = printer_config.get('IP', "192.168.0.251")
                self.printer_port = printer_config.get('Port', 9100)
                self.header = printer_config.get('Header', {'enable': True, 'text': "EzeeCanteen"})
                self.footer = printer_config.get('Footer', {'enable': True, 'text': "Thank you!"})
                self.special_message = printer_config.get('SpecialMessage', "")
        except Exception as e:
            print(f"Error loading printer settings: {e}")

        
        # Set up timer to periodically check printer connection
        self.printer_check_timer = QTimer(self)
        self.printer_check_timer.timeout.connect(self.test_printer_connection)
        self.printer_check_timer.start(60000)  # Check every 60 seconds
    
    def test_printer_connection(self):
        """Test printer connection and set a flag if it's not available"""
        self.printer_available = False
        
        try:
            # Load printer settings if not already loaded
            if not hasattr(self, 'printer_ip') or not hasattr(self, 'printer_port'):
                try:
                    with open('appSettings.json', 'r') as f:
                        app_settings = json.load(f)
                        printer_config = app_settings.get('PrinterConfig', {})
                        self.printer_ip = printer_config.get('IP', "192.168.0.251")
                        self.printer_port = printer_config.get('Port', 9100)
                        logging.info(f"Loaded printer config: IP={self.printer_ip}, Port={self.printer_port}")
                except Exception as e:
                    self.printer_ip = "192.168.0.251"
                    self.printer_port = 9100
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
            else:
                recognition_mode = "Face"
            
            # Get attendance status
            attendance_status = None
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                attendance_status = att.get('attendanceStatus', None)
                att_in_out = att.get('labelName', None)
            else:
                att_in_out = None
            
            # Prepare SQL query
            sql = f"""
                INSERT INTO {DB_TABLE} (
                    PunchCardNo, PunchDateTime, PunchPicURL, RecognitionMode, 
                    IPAddress, AttendanceStatus, DB, AttInOut, Inserted, ZK_SerialNo, LogTransferDate, CanteenMode
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Use device serial if available, otherwise use event serial
            device_serial = getattr(self, 'device_serial', '')
            serial_no = device_serial if device_serial else event_data.get('serialNo', '')
            
            # Prepare values
            values = (
                int(emp_id) if emp_id.isdigit() else 0,  # PunchCardNo
                punch_datetime,                         # PunchDateTime
                punch_pic_url,                          # PunchPicURL
                recognition_mode,                       # RecognitionMode
                IP,                                     # IPAddress
                attendance_status,                      # AttendanceStatus
                DB_NAME,                                # DB
                att_in_out,                             # AttInOut
                'Y',                                    # Inserted
                serial_no,                              # ZK_SerialNo
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'timeBase' #CanteenMode
            )
            
            # Execute query
            cursor.execute(sql, values)
            
            # Commit the transaction
            conn.commit()
            
            print(f"Successfully inserted authentication data for employee {emp_id} into database")
            
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
        # Add event to the list
        if(event_data.get('employeeNoString')):
            print(f"event_data{event_data}\n\n")
            self.events.insert(0, event_data)
            
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
            
            # Determine coupon type based on current time
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
            
            # Get attendance status if available
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                status = att.get('attendanceStatus', '')
                if status:
                    self.special_message = f"Status: {status}"
            
            # Print token slip only if printer is available
            if hasattr(self, 'printer_available') and self.printer_available:
                try:
                    # Check if printer is still available with short timeout
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)  # 0.5 second timeout
                    result = s.connect_ex((self.printer_ip, self.printer_port))
                    s.close()
                    
                    if result == 0:
                        # Printer is available, print the token
                        print_slip(
                            self.printer_ip, 
                            self.printer_port, 
                            0, 
                            self.header, 
                            coupon_type, 
                            emp_id, 
                            name, 
                            punch_time, 
                            self.special_message, 
                            self.footer
                        )
                        print(f"Token {self.token_counter} printed for {name}")
                    else:
                        print(f"Skipping print - printer not available at {self.printer_ip}:{self.printer_port}")
                        self.printer_available = False
                except Exception as e:
                    print(f"Error printing token: {e}")
                    self.printer_available = False
            else:
                print(f"Skipping print - printer not configured or not available")
        
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
    
    def open_settings(self):
        """Function to handle settings button click"""
        # Stop the authentication monitor
        self.communicator.stop_server.emit()
        
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
                print(f"Error recreating settings view: {e}")
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
            print(f"Error loading settings view: {e}")
            # If there's an error, fall back to the original approach
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
            cols = 4  # 5 columns in medium window
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
        