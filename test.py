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
                             QScrollArea, QProgressBar, QSpinBox, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QThread, QFile
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QBrush, QPalette
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy
import urllib.request
from io import BytesIO
# from print import print_slip  # Import print_slip function
from print import print_custom_slip, print_custom_slip_wide  # Import custom print functions
from PyQt5 import sip
from licenseManager import LicenseManager
import asyncio

# Configuration constants (copied from main file to avoid import issues)
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

# Dictionary to store device configurations
DEVICES = {}

# Global flag to track if configs have been refreshed
CONFIG_REFRESHED = False

# Create temp directory for images
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'ezecanteen_images')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def fetch_device_config(force_refresh=False):
    """Fetch device configurations from the database"""
    global DEVICES, IP, PORT, USERNAME, PASSWORD, CONFIG_REFRESHED
    
    if CONFIG_REFRESHED and not force_refresh:
        logging.info("Using cached device configurations")
        return
    
    if force_refresh and DEVICES:
        DEVICES.clear()
    
    try:
        # Get the current license key
        license_key = ""
        try:
            license_manager = LicenseManager()
            
            def get_license_data():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    license_data = loop.run_until_complete(license_manager.get_license_db())
                    return license_data
                finally:
                    loop.close()
            
            license_data = get_license_data()
            if license_data and 'LicenseKey' in license_data:
                license_key = license_data['LicenseKey']
            else:
                logging.warning("Could not retrieve license key for device filtering")
        except Exception as e:
            logging.error(f"Error getting license key: {e}")
        
        # Connect to the database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            port=DB_PORT,
            password=DB_PASS,
            database=DB_NAME
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # Query to fetch devices
        sql = """
        SELECT 
            SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
            Enable, DevicePrinterIP, DeviceName,
            AES_DECRYPT(comKey, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) as Pwd
        FROM configh
        WHERE Enable = 'Y' AND LicenseKey = %s
        ORDER BY DeviceType, DeviceNumber
        """
        
        fallback_sql = """
        SELECT 
            SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
            Enable, DevicePrinterIP, DeviceName,
            AES_DECRYPT(comKey, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) as Pwd
        FROM configh
        WHERE Enable = 'Y'
        ORDER BY DeviceType, DeviceNumber
        LIMIT 5
        """
        
        try:
            cursor.execute(sql, (license_key,))
            results = cursor.fetchall()
            if not results:
                cursor.execute(fallback_sql)
                results = cursor.fetchall()
        except Exception:
            cursor.execute(fallback_sql)
            results = cursor.fetchall()
        
        if not results:
            logging.warning("No enabled devices found in database, using default values")
            CONFIG_REFRESHED = True
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
                        if isinstance(device['Pwd'], (bytes, bytearray)):
                            device_pwd = device['Pwd'].decode('utf-8')
                        else:
                            device_pwd = str(device['Pwd'])
                    except Exception as e:
                        logging.error(f"Error decoding password for device {device_ip}: {e}")
                        device_pwd = PASSWORD
                else:
                    device_pwd = PASSWORD
                
                # Find associated printer from DevicePrinterIP
                printer_ip = device.get('DevicePrinterIP', '')
                
                # If printer IP is not in our map, create a virtual printer entry
                if printer_ip and printer_ip not in printer_ip_map:
                    printer_ip_map[printer_ip] = {
                        'ip': printer_ip,
                        'port': 9100,
                        'name': 'CITIZEN',
                        'virtual': True
                    }
                
                # Get printer details if available
                printer_config = {
                    'ip': printer_ip,
                    'port': 9100
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
        
        # Set default device to the first one for backward compatibility
        if DEVICES:
            first_device = next(iter(DEVICES.values()))
            IP = first_device['device']['ip']
            PORT = first_device['device']['port']
            USERNAME = first_device['device']['user']
            PASSWORD = first_device['device']['password']
        
        cursor.close()
        conn.close()
        
        CONFIG_REFRESHED = True
        logging.info(f"Device configurations refreshed successfully - {len(DEVICES)} devices loaded")
        
    except mysql.connector.Error as err:
        logging.error(f"Database error while fetching device configurations: {err}")
        print(f"Error fetching device configurations: {err}")
        print("Using default device configuration")
    except Exception as e:
        logging.error(f"Unexpected error loading device configurations: {e}")
        print(f"Unexpected error: {e}")
        print("Using default device configuration")

def getDeviceDetails(ip, port, user, psw):
    """Get device details like serial number and MAC address"""
    url = f"http://{ip}:{port}/ISAPI/System/deviceinfo"
    payload = {}
    headers = {}
    response = None
    deviceSerial = ""
    model = ""
    MacAddress = ""
 
    try:
        response = requests.get(url, auth=HTTPDigestAuth(
            user, psw), headers=headers, data=payload, timeout=5)
           
        if response.status_code == 401:
            logging.error(f"Authentication failed (401 Unauthorized) for {ip}:{port} with user: {user}")
            return deviceSerial, MacAddress
        elif response.status_code != 200:
            logging.error(f"Failed to get device details, received status code {response.status_code}")
            return deviceSerial, MacAddress
           
        if response.status_code == 200:
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
            except Exception as parse_err:
                logging.error(f"Error parsing device details XML: {parse_err}")
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

class Communicator(QObject):
    """Signal communicator for threading"""
    stop_server = pyqtSignal()
    new_auth_event = pyqtSignal(dict)

class TimeDisplay(QLabel):
    """Widget to display current time and date"""
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

class CustomAuthEventMonitor(QThread):
    """Custom authentication event monitor for custom mode"""
    
    def __init__(self, communicator, device_ip=None, parent_display=None):
        super().__init__()
        self.communicator = communicator
        self.parent_display = parent_display
        self.running = True
        self.communicator.stop_server.connect(self.stop)
        self.start_time = datetime.now()
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.last_successful_fetch = datetime.now()
        
        # Device configuration
        self.device_ip = device_ip
        self._setup_device_configuration()
        
        # URL for access control events
        self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
        
        # Keep track of processed events
        self.processed_events = set()
        
        # Watchdog timer
        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self.check_watchdog)
        self.watchdog_timer.start(60000)
    
    def _setup_device_configuration(self):
        """Setup device configuration"""
        try:
            if self.device_ip and self.device_ip in DEVICES:
                device_config = DEVICES[self.device_ip]['device']
                self.ip = device_config['ip']
                self.port = device_config['port']
                self.username = device_config['user']
                self.password = device_config['password']
                logging.info(f"CustomAuthEventMonitor using device: {self.ip}:{self.port}")
            else:
                self.ip = IP
                self.port = PORT
                self.username = USERNAME
                self.password = PASSWORD
                logging.info(f"CustomAuthEventMonitor using default device: {self.ip}:{self.port}")
                
            if not all([self.ip, self.port, self.username, self.password]):
                logging.error("Incomplete device configuration")
                
        except Exception as e:
            logging.error(f"Error setting up device configuration: {str(e)}")
    
    def check_watchdog(self):
        """Check if we haven't received events for too long"""
        if not self.running:
            return
        
        time_since_last_fetch = (datetime.now() - self.last_successful_fetch).total_seconds()
        if time_since_last_fetch > 600:  # 10 minutes
            logging.warning(f"No events received for {time_since_last_fetch} seconds. Resetting connection.")
            self.start_time = datetime.now()
            self.consecutive_errors = 0
            self.last_successful_fetch = datetime.now()
    
    def run(self):
        """Main monitoring loop for custom mode"""
        logging.info("Custom auth event monitoring started")
        
        while self.running:
            try:
                # Set time range (from start time to now)
                end_time = datetime.now() 
                end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                start_time_str = self.start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                
                # Initialize pagination variables
                search_position = 0
                total_matches = None
                num_matches = 0
                has_more_pages = True
                processed_ids = set()
                
                # Fetch all pages of results
                while has_more_pages and self.running:
                    payload = {
                        "AcsEventCond": {
                            "searchID": "1",
                            "searchResultPosition": search_position,
                            "maxResults": 5,
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
                        timeout=30,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    # Process successful responses
                    if response.status_code == 200:
                        self.consecutive_errors = 0
                        self.last_successful_fetch = datetime.now()
                        
                        try:
                            data = response.json()
                            
                            if total_matches is None and "AcsEvent" in data and "totalMatches" in data["AcsEvent"]:
                                total_matches = int(data["AcsEvent"]["totalMatches"])
                            
                            if "AcsEvent" in data:
                                info_list = data["AcsEvent"].get("InfoList", [])
                                page_events = len(info_list)
                                
                                if page_events == 0:
                                    has_more_pages = False
                                    break
                                
                                for event in info_list:
                                    event_time = event.get('time')
                                    event_id = f"{event.get('employeeNoString', event.get('employeeNo', 'N/A'))}-{event_time}"
                                    
                                    if event_id in processed_ids:
                                        continue
                                        
                                    processed_ids.add(event_id)
                                    
                                    if event_id not in self.processed_events:
                                        self.processed_events.add(event_id)
                                        
                                        emp_id = event.get('employeeNoString', event.get('employeeNo', 'N/A'))
                                        name = event.get('name', 'N/A')
                                        logging.info(f"New authentication event: Employee ID={emp_id}, Name={name}, Time={event_time}")
                                        
                                        event['source_device_ip'] = self.device_ip
                                        event['deviceIP'] = self.ip
                                        
                                        self.communicator.new_auth_event.emit(event)
                                
                                num_matches += page_events
                                search_position += page_events
                                
                                if (total_matches is not None and num_matches >= total_matches) or num_matches >= 300:
                                    has_more_pages = False
                                    break
                            else:
                                has_more_pages = False
                        
                        except json.JSONDecodeError as json_err:
                            logging.error(f"Response is not valid JSON: {json_err}")
                            self.consecutive_errors += 1
                            has_more_pages = False
                    else:
                        logging.error(f"API request failed with status code: {response.status_code}")
                        self.consecutive_errors += 1
                        has_more_pages = False
                
                # Limit the size of processed_events to avoid memory issues
                if len(self.processed_events) > 1000:
                    self.processed_events = set(list(self.processed_events)[-500:])
                
            except requests.exceptions.Timeout:
                logging.error(f"Timeout connecting to {self.ip}:{self.port}")
                self.consecutive_errors += 1
                time.sleep(2)
            except requests.exceptions.ConnectionError:
                logging.error(f"Connection error for {self.ip}:{self.port}. Device may be offline.")
                self.consecutive_errors += 1
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                self.consecutive_errors += 1
            
            # Check if we've had too many consecutive errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logging.warning(f"Reached {self.consecutive_errors} consecutive errors. Resetting connection...")
                self.consecutive_errors = 0
                self.start_time = datetime.now()
                time.sleep(10)
            
            # Sleep for a short period before the next check
            time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread"""
        logging.info("Custom auth event monitoring stopping...")
        self.running = False
        
        if self.watchdog_timer.isActive():
            self.watchdog_timer.stop()
        
        if self.isRunning():
            if not self.wait(3000):
                logging.warning("Custom auth event monitor did not stop gracefully")
                self.terminate()
                self.wait()
        
        logging.info("Custom auth event monitoring stopped")

class FoodItemCard(QFrame):
    """Card widget for displaying food items with quantity selector"""
    
    def __init__(self, item_data, parent_display):
        super().__init__()
        self.item_data = item_data
        self.parent_display = parent_display
        self.quantity = 0
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 8px;
                border: 2px solid #34495e;
            }
            QFrame:hover {
                border-color: #3498db;
            }
        """)
        
        self.setFixedSize(250, 300)
        
        # Apply shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Food item image placeholder
        image_frame = QFrame()
        image_frame.setStyleSheet("""
            QFrame {
                background-color: #1e2b38;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        image_frame.setFixedHeight(120)
        
        image_layout = QVBoxLayout(image_frame)
        image_label = QLabel("🍽️")  # Food emoji as placeholder
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("font-size: 48px; border: none; background: transparent;")
        image_layout.addWidget(image_label)
        
        # Food item name
        name_label = QLabel(self.item_data.get('name', 'Food Item'))
        name_label.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 16px;
            background: transparent;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        
        # Price
        price = self.item_data.get('price', '0')
        price_label = QLabel(f"₹{price}")
        price_label.setStyleSheet("""
            color: #2ecc71;
            font-weight: bold;
            font-size: 18px;
            background: transparent;
        """)
        price_label.setAlignment(Qt.AlignCenter)
        
        # Description
        description = self.item_data.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                color: #bdc3c7;
                font-size: 12px;
                background: transparent;
            """)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(40)
        
        # Quantity controls
        quantity_frame = QFrame()
        quantity_frame.setStyleSheet("background: transparent; border: none;")
        quantity_layout = QHBoxLayout(quantity_frame)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        
        # Minus button
        minus_btn = QPushButton("-")
        minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        minus_btn.setFixedSize(30, 30)
        minus_btn.clicked.connect(self.decrease_quantity)
        
        # Quantity display
        self.quantity_label = QLabel("0")
        self.quantity_label.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 16px;
            background: transparent;
        """)
        self.quantity_label.setAlignment(Qt.AlignCenter)
        self.quantity_label.setMinimumWidth(40)
        
        # Plus button
        plus_btn = QPushButton("+")
        plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        plus_btn.setFixedSize(30, 30)
        plus_btn.clicked.connect(self.increase_quantity)
        
        quantity_layout.addWidget(minus_btn)
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(plus_btn)
        quantity_layout.setAlignment(Qt.AlignCenter)
        
        # Add to cart button
        cart_btn = QPushButton("Add to Cart")
        cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #bdc3c7;
            }
        """)
        cart_btn.clicked.connect(self.add_to_cart)
        cart_btn.setEnabled(False)  # Initially disabled
        self.cart_btn = cart_btn
        
        # Add widgets to layout
        layout.addWidget(image_frame)
        layout.addWidget(name_label)
        layout.addWidget(price_label)
        if description:
            layout.addWidget(desc_label)
        layout.addWidget(quantity_frame)
        layout.addWidget(cart_btn)
        layout.addStretch()
    
    def increase_quantity(self):
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        self.cart_btn.setEnabled(self.quantity > 0)
        self.parent_display.update_cart_display()
    
    def decrease_quantity(self):
        if self.quantity > 0:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            self.cart_btn.setEnabled(self.quantity > 0)
            self.parent_display.update_cart_display()
    
    def add_to_cart(self):
        if self.quantity > 0:
            self.parent_display.add_item_to_cart(self.item_data, self.quantity)
            # Reset quantity after adding to cart
            self.quantity = 0
            self.quantity_label.setText("0")
            self.cart_btn.setEnabled(False)

class CartDisplay(QFrame):
    """Widget to display current cart contents"""
    
    def __init__(self, parent_display):
        super().__init__()
        self.parent_display = parent_display
        
        self.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 8px;
                border: 2px solid #1c2e4a;
            }
        """)
        
        self.setMaximumHeight(300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Cart title
        title_label = QLabel("🛒 Current Cart")
        title_label.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 18px;
            background: transparent;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # Cart items scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #0d1b2a;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #152238;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2c3e50;
                min-height: 20px;
                border-radius: 4px;
            }
        """)
        
        # Cart widget
        self.cart_widget = QWidget()
        self.cart_widget.setStyleSheet("""
            QWidget {
                background-color: #0d1b2a;
            }
        """)
        self.cart_layout = QVBoxLayout(self.cart_widget)
        self.cart_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.cart_widget)
        
        # Total display
        self.total_label = QLabel("Total: ₹0")
        self.total_label.setStyleSheet("""
            color: #2ecc71;
            font-weight: bold;
            font-size: 16px;
            background: transparent;
            padding: 10px;
            border-top: 1px solid #34495e;
        """)
        self.total_label.setAlignment(Qt.AlignCenter)
        
        # Clear cart button
        clear_btn = QPushButton("Clear Cart")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        clear_btn.clicked.connect(self.parent_display.clear_cart)
        
        layout.addWidget(title_label)
        layout.addWidget(self.scroll_area, 1)
        layout.addWidget(self.total_label)
        layout.addWidget(clear_btn)
    
    def update_cart(self, cart_items, total):
        # Clear existing items
        while self.cart_layout.count():
            child = self.cart_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add current cart items
        for item_name, item_data in cart_items.items():
            item_frame = QFrame()
            item_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e2b38;
                    border-radius: 4px;
                    border: 1px solid #34495e;
                    margin: 2px;
                }
            """)
            
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)
            
            # Item info
            info_label = QLabel(f"{item_name}")
            info_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
            
            # Quantity and price
            qty_price_label = QLabel(f"x{item_data['quantity']} = ₹{item_data['total']}")
            qty_price_label.setStyleSheet("color: #bdc3c7; background: transparent;")
            
            item_layout.addWidget(info_label)
            item_layout.addStretch()
            item_layout.addWidget(qty_price_label)
            
            self.cart_layout.addWidget(item_frame)
        
        # Update total
        self.total_label.setText(f"Total: ₹{total}")
        
        if not cart_items:
            empty_label = QLabel("Cart is empty")
            empty_label.setStyleSheet("color: #7f8c8d; font-style: italic; background: transparent;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.cart_layout.addWidget(empty_label)

class CustomLiveDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cart_items = {}  # {item_name: {quantity: int, price: float, total: float}}
        self.cart_total = 0
        self.pending_employee = None  # Store employee data for next authentication
        self.food_items = []
        
        # Initialize communicator and other attributes
        self.communicator = Communicator()
        self.active_devices = {}
        self.device_printers = {}
        
        # Load application settings
        self.load_app_settings()
        
        # Initialize UI
        self.init_ui()
        
        # Initialize devices and authentication monitoring
        QTimer.singleShot(100, self.delayed_initialization)
    
    def load_app_settings(self):
        """Load application settings from appSettings.json"""
        try:
            with open('appSettings.json', 'r', encoding='utf-8') as f:
                self.app_settings = json.load(f)
            
            # Get food items from custom mode
            custom_config = self.app_settings.get('CanteenMenu', {}).get('custom', {})
            self.food_items = custom_config.get('FoodItems', [])
            self.special_message = custom_config.get('SpecialMessage', '')
            
            # Get printer configuration
            printer_config = self.app_settings.get('PrinterConfig', {})
            self.printer_ip = printer_config.get('IP', "192.168.0.253")
            self.printer_port = printer_config.get('Port', 9100)
            self.header = printer_config.get('Header', {'enable': True, 'text': "EzeeCanteen"})
            self.footer = printer_config.get('Footer', {'enable': True, 'text': "Thank you!"})
            
            logging.info(f"Loaded {len(self.food_items)} food items for custom mode")
            
        except Exception as e:
            logging.error(f"Error loading app settings: {e}")
            self.food_items = []
            self.special_message = ""
            self.printer_ip = "192.168.0.253"
            self.printer_port = 9100
            self.header = {'enable': True, 'text': "EzeeCanteen"}
            self.footer = {'enable': True, 'text': "Thank you!"}
    
    def delayed_initialization(self):
        """Initialize devices and start monitoring after UI is ready"""
        # Test database and printer connections
        self.test_connections()
        
        # Initialize device monitoring
        self.initialize_devices()
    
    def test_connections(self):
        """Test database and printer connections"""
        # Test database connection
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME,
                connection_timeout=5
            )
            if conn.is_connected():
                self.db_available = True
                logging.info("Database connection successful")
                conn.close()
        except Exception as e:
            self.db_available = False
            logging.error(f"Database connection error: {e}")
        
        # Test printer connection
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((self.printer_ip, self.printer_port))
            s.close()
            self.printer_available = (result == 0)
            if self.printer_available:
                logging.info(f"Printer connection successful ({self.printer_ip}:{self.printer_port})")
            else:
                logging.warning(f"Printer connection failed ({self.printer_ip}:{self.printer_port})")
        except Exception as e:
            self.printer_available = False
            logging.error(f"Error testing printer connection: {e}")
    
    def initialize_devices(self):
        """Initialize authentication devices for custom mode"""
        if not DEVICES:
            # Use default device configuration
            self.setup_single_device_monitor()
            return
        
        # Connect authentication events
        self.communicator.new_auth_event.connect(self.handle_auth_event)
        
        # Initialize device monitors
        for device_ip, config in DEVICES.items():
            device_config = config['device']
            printer_config = config['printer']
            
            # Store printer configuration
            self.device_printers[device_ip] = {
                'ip': printer_config['ip'],
                'port': printer_config.get('port', 9100),
                'name': printer_config.get('name', 'CITIZEN'),
                'available': False
            }
            
            # Start authentication monitor for this device
            auth_monitor = CustomAuthEventMonitor(self.communicator, device_ip, self)
            auth_monitor.start()
            
            # Store monitor
            self.active_devices[device_ip] = {
                'monitor': auth_monitor,
                'config': device_config
            }
            
            logging.info(f"Started custom monitor for device {device_ip}")
        
        # Test printer connections after a delay
        QTimer.singleShot(2000, self.test_printer_connections)
    
    def test_printer_connections(self):
        """Test all configured printer connections"""
        if not self.device_printers:
            return
        
        for device_ip, printer in self.device_printers.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex((printer['ip'], printer['port']))
                s.close()
                
                printer['available'] = (result == 0)
                if printer['available']:
                    logging.info(f"Printer {printer['ip']}:{printer['port']} for device {device_ip} is available")
                else:
                    logging.warning(f"Printer {printer['ip']}:{printer['port']} for device {device_ip} is not available")
            except Exception as e:
                printer['available'] = False
                logging.error(f"Error testing printer {printer['ip']}:{printer['port']}: {e}")
    
    def setup_single_device_monitor(self):
        """Setup single device monitor for legacy mode"""
        # Start authentication event monitor
        self.auth_monitor = CustomAuthEventMonitor(self.communicator, None, self)
        self.communicator.new_auth_event.connect(self.handle_auth_event)
        self.auth_monitor.start()
        
        logging.info("Started custom monitor for default device")
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("EzeeCanteen - Custom Mode")
        self.setGeometry(100, 100, 1400, 800)
        
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
        
        # Header
        self.create_header(main_layout)
        
        # Content area with menu and cart
        content_layout = QHBoxLayout()
        
        # Menu area (left side)
        self.create_menu_area(content_layout)
        
        # Cart area (right side)
        self.create_cart_area(content_layout)
        
        main_layout.addLayout(content_layout, 1)
        
        # Footer
        self.create_footer(main_layout)
    
    def create_header(self, main_layout):
        """Create header with title and time"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 6px;
                border: 1px solid #1c2e4a;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Time display
        self.time_display = TimeDisplay()
        
        # Title
        title_label = QLabel("EzeeCanteen - Custom Mode")
        title_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        title_label.setFont(QFont("Arial", 20))
        title_label.setAlignment(Qt.AlignCenter)
        
        # Settings button
        settings_button = QPushButton("⚙")
        settings_button.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: #1c2e4a;
                border-radius: 4px;
                padding: 5px;
                border: 1px solid #253649;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #253649;
            }
        """)
        settings_button.setFixedSize(36, 36)
        settings_button.clicked.connect(self.open_settings)
        
        header_layout.addWidget(self.time_display)
        header_layout.addWidget(title_label, 1)
        header_layout.addWidget(settings_button)
        
        main_layout.addWidget(header_frame)
        
    def create_menu_area(self, content_layout):
        """Create menu area with food item cards"""
        menu_frame = QFrame()
        menu_frame.setStyleSheet("""
            QFrame {
                background-color: #0d1b2a;
                border-radius: 8px;
                border: 1px solid #1e2b38;
            }
        """)
        
        menu_layout = QVBoxLayout(menu_frame)
        menu_layout.setContentsMargins(15, 15, 15, 15)
        
        # Menu title
        menu_title = QLabel("🍽️ Menu")
        menu_title.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 18px;
            background: transparent;
        """)
        menu_title.setAlignment(Qt.AlignCenter)
        
        # Scroll area for menu items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #0d1b2a;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #152238;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2c3e50;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        # Grid for food items
        grid_widget = QWidget()
        grid_widget.setStyleSheet("""
            QWidget {
                background-color: #0d1b2a;
            }
        """)
        self.menu_grid = QGridLayout(grid_widget)
        self.menu_grid.setSpacing(15)
        self.menu_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Populate menu with food items
        self.populate_menu()
        
        scroll_area.setWidget(grid_widget)
        
        menu_layout.addWidget(menu_title)
        menu_layout.addWidget(scroll_area, 1)
        
        content_layout.addWidget(menu_frame, 2)  # 2/3 of the width
    def create_cart_area(self, content_layout):
        """Create cart area"""
        self.cart_display = CartDisplay(self)
        content_layout.addWidget(self.cart_display, 1)  # 1/3 of the width
    
    def create_footer(self, main_layout):
        """Create footer"""
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border-radius: 6px;
                border: 1px solid #1c2e4a;
            }
        """)
        footer_frame.setMaximumHeight(40)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(15, 5, 15, 5)
        
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        footer_label.setAlignment(Qt.AlignCenter)
        
        footer_layout.addStretch()
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        
        main_layout.addWidget(footer_frame)
    
    def populate_menu(self):
        """Populate menu grid with food item cards"""
        # Clear existing items
        while self.menu_grid.count():
            item = self.menu_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.food_items:
            # Show message if no food items configured
            no_items_label = QLabel("No food items configured.\nPlease add items in settings.")
            no_items_label.setStyleSheet("""
                color: #7f8c8d;
                font-size: 16px;
                font-style: italic;
                background: transparent;
            """)
            no_items_label.setAlignment(Qt.AlignCenter)
            self.menu_grid.addWidget(no_items_label, 0, 0)
            return
        
        # Add food item cards
        cols = 3  # Number of columns
        for i, item in enumerate(self.food_items):
            row = i // cols
            col = i % cols
            
            food_card = FoodItemCard(item, self)
            self.menu_grid.addWidget(food_card, row, col)
    
    def add_item_to_cart(self, item_data, quantity):
        """Add item to cart"""
        item_name = item_data.get('name', 'Unknown Item')
        item_price = float(item_data.get('price', 0))
        
        if item_name in self.cart_items:
            # Update existing item
            self.cart_items[item_name]['quantity'] += quantity
            self.cart_items[item_name]['total'] = self.cart_items[item_name]['quantity'] * item_price
        else:
            # Add new item
            self.cart_items[item_name] = {
                'quantity': quantity,
                'price': item_price,
                'total': quantity * item_price,
                'data': item_data
            }
        
        self.update_cart_display()
        
        # Show confirmation
        QMessageBox.information(self, "Added to Cart", f"Added {quantity}x {item_name} to cart!")
    
    def update_cart_display(self):
        """Update cart display and total"""
        self.cart_total = sum(item['total'] for item in self.cart_items.values())
        self.cart_display.update_cart(self.cart_items, self.cart_total)
    
    def clear_cart(self):
        """Clear all items from cart"""
        if self.cart_items:
            reply = QMessageBox.question(self, "Clear Cart", "Are you sure you want to clear the cart?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cart_items.clear()
                self.cart_total = 0
                self.update_cart_display()
    
    def handle_auth_event(self, event_data):
        """Handle authentication event in custom mode"""
        try:
            # Extract employee info
            emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', ''))
            emp_name = event_data.get('name', 'N/A')
            
            if not emp_id:
                return
            
            logging.info(f"Authentication event: Employee {emp_id} ({emp_name})")
            
            # Check if there are items in cart
            if not self.cart_items:
                # Show message that cart is empty
                QMessageBox.warning(self, "Empty Cart", f"Welcome {emp_name}!\nPlease add items to cart before authentication.")
                return
            
            # Process the order
            self.process_order(event_data)
            
        except Exception as e:
            logging.error(f"Error handling auth event: {e}")
            QMessageBox.critical(self, "Error", f"Error processing authentication: {e}")
    
    def process_order(self, event_data):
        """Process order and print receipt"""
        try:
            emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', ''))
            emp_name = event_data.get('name', 'N/A')
            
            # Create order summary
            order_summary = []
            for item_name, item_data in self.cart_items.items():
                order_summary.append(f"{item_name} x{item_data['quantity']} = ₹{item_data['total']}")
            
            order_text = ", ".join(order_summary)
            
            # Insert to database
            self.insert_order_to_database(event_data, order_text, self.cart_total)
            
            # Print receipt
            punch_time = event_data.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            if 'T' in punch_time:
                punch_time = punch_time.replace('T', ' ').split('+')[0]
            
            # Determine which printer to use
            source_device_ip = event_data.get('source_device_ip')
            printer_used = False
            
            # Try device-specific printer first
            if source_device_ip and source_device_ip in self.device_printers:
                printer = self.device_printers[source_device_ip]
                if printer['available']:
                    try:
                        # Use custom print function for better formatting
                        print_custom_slip(
                            printer['ip'],
                            printer['port'],
                            self.header,
                            self.cart_items,  # Pass cart items instead of order text
                            emp_id,
                            emp_name,
                            punch_time,
                            self.special_message,
                            self.footer
                        )
                        printer_used = True
                        logging.info(f"Custom receipt printed for {emp_name} on printer {printer['ip']}:{printer['port']} - Total: ₹{self.cart_total}")
                    except Exception as e:
                        logging.error(f"Error printing custom receipt on device printer: {e}")
            
            # Fallback to default printer if device printer failed or not available
            if not printer_used and self.printer_available:
                try:
                    # Use custom print function for better formatting
                    print_custom_slip_wide(
                        self.printer_ip,
                        self.printer_port,
                        self.header,
                        self.cart_items,  # Pass cart items instead of order text
                        emp_id,
                        emp_name,
                        punch_time,
                        self.special_message,
                        self.footer
                    )
                    printer_used = True
                    logging.info(f"Custom receipt printed for {emp_name} on default printer {self.printer_ip}:{self.printer_port} - Total: ₹{self.cart_total}")
                except Exception as e:
                    logging.error(f"Error printing custom receipt on default printer: {e}")
            
            if not printer_used:
                QMessageBox.warning(self, "Print Error", "Could not print receipt - no printer available")
            
            # Show success message
            QMessageBox.information(self, "Order Processed", 
                                   f"Order processed for {emp_name}!\n"
                                   f"Total: ₹{self.cart_total}\n"
                                   f"Items: {len(self.cart_items)}")
            
            # Clear cart after successful order
            self.cart_items.clear()
            self.cart_total = 0
            self.update_cart_display()
            
        except Exception as e:
            logging.error(f"Error processing order: {e}")
            QMessageBox.critical(self, "Order Error", f"Error processing order: {e}")
    
    def insert_order_to_database(self, event_data, order_text, total_amount):
        """Insert order data to database"""
        if not hasattr(self, 'db_available') or not self.db_available:
            logging.warning("Database not available, skipping insertion")
            return
        
        try:
            # Connect to database
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            
            cursor = conn.cursor()
            
            # Extract data from event
            emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', ''))
            punch_time = event_data.get('time', datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'))
            
            if 'T' in punch_time:
                punch_datetime = punch_time.replace('T', ' ').split('+')[0]
            else:
                punch_datetime = punch_time
            
            # Get picture URL
            punch_pic_url = event_data.get('pictureURL', '')
            
            # Get recognition mode
            minor = event_data.get('minor', 0)
            if minor == 1:
                recognition_mode = "Card"
            elif minor == 38:
                recognition_mode = "Fingerprint"
            elif minor == 75:
                recognition_mode = "Face"
            else:
                recognition_mode = "Unknown"
            
            # Get attendance info
            attendance_status = None
            att_in_out = None
            if "AttendanceInfo" in event_data:
                att = event_data["AttendanceInfo"]
                attendance_status = att.get('attendanceStatus', None)
                att_in_out = att.get('labelName', None)
            
            # Get device IP
            device_ip = event_data.get('deviceIP', IP)
            
            # Get license key
            license_key = ""
            try:
                license_manager = LicenseManager()
                
                def get_license_data():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        license_data = loop.run_until_complete(license_manager.get_license_db())
                        return license_data
                    finally:
                        loop.close()
                
                license_data = get_license_data()
                if license_data and 'LicenseKey' in license_data:
                    license_key = license_data['LicenseKey']
            except Exception as e:
                logging.error(f"Error getting license key: {e}")
            
            # Get device serial
            serial_no = ""
            if hasattr(self, 'active_devices') and device_ip in self.active_devices:
                # For multi-device setup, you'd need to store serial numbers
                serial_no = getattr(self, 'device_serial', '')
            else:
                serial_no = getattr(self, 'device_serial', '')
            
            # Prepare SQL query
            sql = f"""
                INSERT INTO {DB_TABLE} (
                    PunchCardNo, PunchDateTime, PunchPicURL, RecognitionMode, 
                    IPAddress, AttendanceStatus, DB, AttInOut, Inserted, ZK_SerialNo, 
                    LogTransferDate, CanteenMode, Fooditem, totalAmount, LicenseKey
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                int(emp_id) if emp_id.isdigit() else 0,
                punch_datetime,
                punch_pic_url,
                recognition_mode,
                device_ip,
                attendance_status,
                DB_NAME,
                att_in_out,
                'Y',
                serial_no,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'custom',
                order_text,
                total_amount,
                license_key
            )
            
            cursor.execute(sql, values)
            conn.commit()
            
            logging.info(f"Order data inserted to database for employee {emp_id}")
            
        except Exception as e:
            logging.error(f"Error inserting order to database: {e}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()
    
    def open_settings(self):
        """Open settings (placeholder for now)"""
        QMessageBox.information(self, "Settings", "Settings functionality will be implemented soon!")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Stop all active device monitors
            if hasattr(self, 'active_devices'):
                for device_ip, device_info in self.active_devices.items():
                    monitor = device_info['monitor']
                    if monitor and monitor.isRunning():
                        try:
                            monitor.stop()
                            if not monitor.wait(1000):
                                monitor.terminate()
                                monitor.wait()
                            logging.info(f"Stopped monitor for device {device_ip}")
                        except Exception as e:
                            logging.error(f"Error stopping monitor for device {device_ip}: {e}")
            
            # Stop legacy auth monitor if it exists
            if hasattr(self, 'auth_monitor'):
                self.communicator.stop_server.emit()
                if self.auth_monitor.isRunning():
                    if not self.auth_monitor.wait(1000):
                        self.auth_monitor.terminate()
                        self.auth_monitor.wait()
                logging.info("Stopped legacy auth monitor")
            
            # Clean up temp directory
            try:
                if os.path.exists(TEMP_DIR):
                    shutil.rmtree(TEMP_DIR)
                    logging.info(f"Cleaned up temporary directory: {TEMP_DIR}")
            except Exception as e:
                logging.error(f"Error cleaning up temp directory: {e}")
                
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        
        event.accept()

def main():
    """Main function to run the custom live display"""
    # Only create app if this is run as a standalone program
    standalone = __name__ == '__main__'
    
    # Initialize logging
    try:
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        log_file = os.path.join(logs_dir, 'custom_ezecanteen.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logging.info("CustomLiveDisplay application starting")
    except Exception as e:
        print(f"Error initializing logging: {e}")
    
    if standalone:
        app = QApplication(sys.argv)
    
    # Refresh device configurations
    logging.info("Refreshing device configurations for custom mode...")
    fetch_device_config(force_refresh=True)
    
    # Create temp directory if it doesn't exist
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logging.info(f"Created temporary directory: {TEMP_DIR}")
    
    # Create and show the custom live display window
    window = CustomLiveDisplay()
    
    if standalone:
        window.show()
        
        try:
            sys.exit(app.exec_())
        finally:
            # Clean up temp directory
            if os.path.exists(TEMP_DIR):
                try:
                    shutil.rmtree(TEMP_DIR)
                    logging.info(f"Cleaned up temporary directory: {TEMP_DIR}")
                except:
                    pass
    else:
        return window

if __name__ == '__main__':
    main()