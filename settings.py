import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QLineEdit, QFrame, QScrollArea, QDialog, QProgressBar, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QColor
import os
import mysql.connector  # Added for database connection
from PyQt5 import sip
import json

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

# Import the EzeeCanteen class from timeBase.py
try:
    from timeBase import EzeeCanteen
except ImportError:
    print("Could not import EzeeCanteen from timeBase.py")

# Import the EzeeCanteenApp class from CanteenSettings.py
try:
    from CanteenSettings import EzeeCanteenApp
except ImportError:
    print("Could not import EzeeCanteenApp from CanteenSettings.py")

class LoadingOverlay(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: rgba(0, 0, 0, 0.5);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Spinner container
        spinner_frame = QFrame()
        spinner_frame.setFixedSize(80, 80)
        spinner_frame.setStyleSheet("""
            QFrame {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Create spinner animation
        self.spinner_animation = QPropertyAnimation(spinner_frame, b"geometry")
        self.spinner_animation.setDuration(1000)
        self.spinner_animation.setStartValue(QRect(0, 0, 80, 80))
        self.spinner_animation.setEndValue(QRect(0, 0, 80, 80))
        self.spinner_animation.setLoopCount(-1)  # Infinite loop
        
        # Add custom paintEvent to spinner_frame
        def paint_spinner(obj, event):
            from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
            from PyQt5.QtCore import QRect, Qt
            import math
            
            painter = QPainter(obj)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Define spinner properties
            center_x = obj.width() / 2
            center_y = obj.height() / 2
            outer_radius = min(center_x, center_y) - 5
            
            # Draw first arc (blue)
            painter.setPen(QPen(QColor("#5e90fa"), 6, Qt.SolidLine, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)
            rect = QRect(center_x - outer_radius, center_y - outer_radius, outer_radius * 2, outer_radius * 2)
            # Rotate based on animation time
            rotation = int((self.spinner_animation.currentTime() / self.spinner_animation.duration()) * 360) % 360
            painter.drawArc(rect, rotation * 16, 180 * 16)
            
            # Draw second arc (green)
            painter.setPen(QPen(QColor("#53ff29"), 6, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(rect, (rotation + 180) * 16, 180 * 16)
        
        spinner_frame.paintEvent = lambda event, obj=spinner_frame: paint_spinner(obj, event)
        self.spinner_animation.start()
        
        layout.addWidget(spinner_frame, alignment=Qt.AlignCenter)
        
        # Loading text with animated dots
        text_container = QWidget()
        text_layout = QHBoxLayout(text_container)
        
        self.loading_label = QLabel("Clearing Cache")
        self.loading_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        text_layout.addWidget(self.loading_label)
        
        # Animated dots
        self.dots_label = QLabel()
        self.dots_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        text_layout.addWidget(self.dots_label)
        
        layout.addWidget(text_container, alignment=Qt.AlignCenter)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_clear_cache)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
        
        # Animate dots
        self.dot_count = 0
        self.dot_timer = QTimer(self)
        self.dot_timer.timeout.connect(self.update_dots)
        self.dot_timer.start(400)
    
    def update_dots(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.dots_label.setText(dots)
    
    def cancel_clear_cache(self):
        self.hide()
        # Placeholder for cancel_clear_cache functionality
        print("Cancel clear cache triggered")

class EzeeCanteenWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.setGeometry(100, 100, 800, 600)
        self.printers = []
        self.devices = []
        self.port_number = ""
        self.init_ui()
        
        # Ensure the load_settings function runs
        print("Setting up async loading tasks...")
        import asyncio
        self.loop = asyncio.get_event_loop()
        
        # Create the tasks but also ensure they start running
        load_settings_task = self.loop.create_task(self.load_settings())
        toggle_state_task = self.loop.create_task(self.initialize_toggle_state())
        
        # Add callbacks to track completion
        load_settings_task.add_done_callback(lambda t: print(f"Load settings task completed: {t.exception() or 'Success'}"))
        toggle_state_task.add_done_callback(lambda t: print(f"Toggle state task completed: {t.exception() or 'Success'}"))
        
        # Force the event loop to run until tasks complete
        try:
            asyncio.ensure_future(load_settings_task)
            asyncio.ensure_future(toggle_state_task)
        except Exception as e:
            print(f"Error setting up async tasks: {e}")
        
        # Call manual load method after a short delay to ensure UI is shown first
        QTimer.singleShot(500, self.manually_run_load_settings)
    
    def manually_run_load_settings(self):
        """Manual backup method to load settings if the async method fails"""
        print("\n===== MANUAL SETTINGS LOADER =====")
        try:
            # Use a direct approach without asyncio
            # Test database connection
            conn = self.db_connect()
            if not conn:
                print("❌ Manual loader: Database connection failed")
                # Instead of hardcoded values, try an alternative connection
                try:
                    print("Attempting alternative database connection...")
                    alt_conn = mysql.connector.connect(
                        host=DB_HOST,
                        user=DB_USER,
                        port=DB_PORT,
                        password=DB_PASS,
                        database=DB_NAME
                    )
                    
                    if alt_conn:
                        print("✅ Alternative connection successful, fetching data")
                        alt_cursor = alt_conn.cursor(dictionary=True)
                        
                        # Fetch printers
                        alt_cursor.execute("""
                            SELECT DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser,
                                   Enable, DevicePrinterIP 
                            FROM configh 
                            WHERE DeviceType = 'Printer' OR DeviceType != 'Device'
                        """)
                        printer_data = alt_cursor.fetchall()
                        
                        # Fetch devices
                        alt_cursor.execute("""
                            SELECT DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser,
                                   Enable, DevicePrinterIP 
                            FROM configh 
                            WHERE DeviceType = 'Device'
                        """)
                        device_data = alt_cursor.fetchall()
                        
                        self.printers = []
                        for printer in printer_data:
                            self.printers.append({
                                'name': 'CITIZEN',
                                'ip': printer['IP'],
                                'deviceNumber': printer.get('DeviceNumber'),
                                'type': 'thermal',
                                'location': printer.get('DeviceLocation', ''),
                                'enable': printer.get('Enable', 'N'),
                                'username': printer.get('ComUser', '')
                            })
                        
                        self.devices = []
                        for device in device_data:
                            self.devices.append({
                                'deviceType': device['DeviceType'],
                                'deviceNumber': device.get('DeviceNumber'),
                                'ip': device['IP'],
                                'port': device.get('Port', ''),
                                'location': device.get('DeviceLocation', ''),
                                'username': device.get('ComUser', ''),
                                'printerIP': device.get('DevicePrinterIP', ''),
                                'enable': device.get('Enable', 'N')
                            })
                        
                        alt_conn.close()
                        print(f"Loaded {len(self.printers)} printers and {len(self.devices)} devices from alternative connection")
                    else:
                        # Only use mock data as last resort
                        print("❌ Alternative connection failed, using mock data")
                        self.printers = [
                            {'name': 'CITIZEN', 'ip': '192.168.0.251', 'type': 'thermal', 'enable': 'Y'}
                        ]
                        self.devices = [
                            {'deviceType': 'Device', 'ip': '192.168.0.90', 'location': 'Room101', 
                             'printerIP': '192.168.0.251', 'enable': 'Y'}
                        ]
                except Exception as alt_err:
                    print(f"❌ Alternative connection error: {alt_err}")
                    # Final fallback to mock data
                    self.printers = [
                        {'name': 'CITIZEN', 'ip': '192.168.0.251', 'type': 'thermal', 'enable': 'Y'}
                    ]
                    self.devices = [
                        {'deviceType': 'Device', 'ip': '192.168.0.90', 'location': 'Room101', 
                         'printerIP': '192.168.0.251', 'enable': 'Y'}
                    ]
            else:
                print("✅ Manual loader: Database connection successful")
                cursor = conn.cursor(dictionary=True)
                
                # Fetch devices
                sql = """
                SELECT SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser,
                       Enable, DevicePrinterIP 
                FROM configh
                ORDER BY DeviceType, DeviceNumber
                """
                cursor.execute(sql)
                devices_data = cursor.fetchall()
                
                print(f"Manual loader: Found {len(devices_data)} devices in database")
                
                self.printers = []
                self.devices = []
                
                # Process devices
                for device in devices_data:
                    print(f"Manual loader processing: {device}")
                    if device.get('DeviceType') == 'Printer' or device.get('DeviceType') != 'Device':
                        self.printers.append({
                            'name': 'CITIZEN',
                            'ip': device['IP'],
                            'deviceNumber': device.get('DeviceNumber'),
                            'type': 'thermal',
                            'location': device.get('DeviceLocation', ''),
                            'enable': device.get('Enable', 'N'),
                            'username': device.get('ComUser', '')
                        })
                    else:
                        self.devices.append({
                            'deviceType': device['DeviceType'],
                            'deviceNumber': device.get('DeviceNumber'),
                            'ip': device['IP'],
                            'port': device.get('Port', ''),
                            'location': device.get('DeviceLocation', ''),
                            'username': device.get('ComUser', ''),
                            'printerIP': device.get('DevicePrinterIP', ''),
                            'enable': device.get('Enable', 'N')
                        })
                
                # If no printers found but device has printer IP, create virtual printer
                if not self.printers:
                    unique_printer_ips = set()
                    for device in self.devices:
                        printer_ip = device.get('printerIP')
                        if printer_ip and printer_ip not in unique_printer_ips:
                            unique_printer_ips.add(printer_ip)
                            self.printers.append({
                                'name': 'CITIZEN',
                                'ip': printer_ip,
                                'deviceNumber': len(self.printers) + 1,
                                'type': 'thermal',
                                'enable': 'Y',
                                'virtual': True
                            })
                            print(f"Manual loader: Created virtual printer for IP {printer_ip}")
                
                conn.close()
            
            # Update UI
            print(f"Manual loader: Populating UI with {len(self.printers)} printers and {len(self.devices)} devices")
            
            # Ensure we're clearing out existing widgets
            for i in reversed(range(self.printers_layout.count())):
                widget = self.printers_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            for i in reversed(range(self.devices_layout.count())):
                widget = self.devices_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            # Force UI update
            QApplication.processEvents()
            
            # Rebuild UI with new data
            self.populate_printers()
            self.populate_devices()
            
            # Force UI update again
            QApplication.processEvents()
            
            print("✅ Manual loader: UI updated successfully")
        except Exception as e:
            print(f"❌ Manual loader error: {e}")
            import traceback
            traceback.print_exc()
        print("===== MANUAL LOADER FINISHED =====\n")
    
    def db_connect(self):
        """Connect to MySQL database"""
        try:
            print(f"Attempting to connect to database: {DB_HOST}:{DB_PORT}")
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            print("Database connection successful")
            return conn
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(err)}")
            return None
            
    async def fetch_devices_from_db(self):
        """Fetch all devices from the database"""
        print("\n========== STARTING DATABASE FETCH ==========")
        try:
            print("Attempting to connect to database...")
            # Connect to database
            conn = self.db_connect()
            if not conn:
                print("❌ Database connection failed")
                return [], []
                
            print("✅ Database connection successful")
            cursor = conn.cursor(dictionary=True)
            
            # Query to fetch all devices from configh table
            # Explicitly select the column names to avoid any case sensitivity issues
            sql = """
            SELECT 
                SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                Enable, DevicePrinterIP, DeviceName
            FROM configh
            ORDER BY DeviceType, DeviceNumber
            """
            
            print(f"Executing query: {sql.strip()}")
            cursor.execute(sql)
            results = cursor.fetchall()
            print(f"Query returned {len(results)} total rows")
            
            if len(results) == 0:
                print("⚠️ No devices found in database")
                return [], []
            
            printers = []
            devices = []
            
            # Create a dictionary to map printer IPs to their index in the printers list
            printer_ip_map = {}
            
            # First pass: collect all printers and any non-"Device" types
            for device in results:
                if device.get('DeviceType') == 'Printer' or device.get('DeviceType') != 'Device':
                    print(f"Found printer or non-device type: {device}")
                    
                    printer_data = {
                        "deviceType": device["DeviceType"],
                        "deviceNumber": device.get("DeviceNumber", 0),
                        "ip": device["IP"],
                        "port": device.get("Port", ""),
                        "username": device.get("ComUser", ""),
                        "location": device.get("DeviceLocation", ""),
                        "enable": device.get("Enable", "N"),
                        "name": device.get("DeviceName", "CITIZEN"),  # Use DeviceName if available
                        "type": "thermal"  # Default printer type
                    }
                    
                    printers.append(printer_data)
                    # Map this printer's IP to its position in the printers array
                    printer_ip_map[device["IP"]] = len(printers) - 1
                    print(f"Added printer with IP {device['IP']} at index {len(printers) - 1}")
            
            # Second pass: collect only "Device" type devices
            for device in results:
                if device.get('DeviceType') == 'Device':
                    print(f"Processing device: {device}")
                    
                    # Check if all required fields exist
                    if not all(k in device for k in ['DeviceType', 'IP']):
                        print(f"Skipping device, missing required fields: {device}")
                        continue
                        
                    device_data = {
                        "deviceType": device["DeviceType"],
                        "deviceNumber": device.get("DeviceNumber", 0),
                        "ip": device["IP"],
                        "port": device.get("Port", ""),
                        "username": device.get("ComUser", ""),
                        "location": device.get("DeviceLocation", ""),
                        "printerIP": device.get("DevicePrinterIP", ""),
                        "enable": device.get("Enable", "N"),
                    }
                    
                    # If this device has a printer IP, find the associated printer
                    printer_ip = device.get("DevicePrinterIP")
                    if printer_ip and printer_ip in printer_ip_map:
                        printer_index = printer_ip_map[printer_ip]
                        printer = printers[printer_index]
                        device_data["printerName"] = printer.get("name", "Unknown Printer")
                        print(f"Linked device to printer {device_data['printerName']} with IP {printer_ip}")
                    
                    devices.append(device_data)
                    print(f"Added device: {device_data}")
            
            # If no printers were found in the database, but we have device printer IPs,
            # create virtual printer entries for display
            if not printers:
                print("No printers found in database, checking for virtual printers...")
                unique_printer_ips = set()
                for device in devices:
                    printer_ip = device.get("printerIP")
                    if printer_ip and printer_ip not in unique_printer_ips:
                        unique_printer_ips.add(printer_ip)
                        
                        # Create a virtual printer entry
                        printer_data = {
                            "deviceType": "Printer",
                            "deviceNumber": len(printers) + 1,
                            "ip": printer_ip,
                            "name": "CITIZEN",  # Default name
                            "type": "thermal",  # Default type
                            "enable": "Y",      # Assume enabled
                            "virtual": True     # Mark as virtual (not actually in database)
                        }
                        printers.append(printer_data)
                        print(f"Created virtual printer for IP {printer_ip}")
            
            print(f"✅ Successfully loaded {len(printers)} printers and {len(devices)} devices from database")
            print("========== FINISHED DATABASE FETCH ==========\n")
            return printers, devices
            
        except mysql.connector.Error as err:
            print(f"❌ Database error in fetch_devices_from_db: {err}")
            QMessageBox.critical(self, "Database Error", f"Failed to fetch devices: {str(err)}")
            return [], []
        except Exception as e:
            print(f"❌ Unexpected error in fetch_devices_from_db: {e}")
            import traceback
            traceback.print_exc()
            return [], []
        finally:
            if conn:
                conn.close()
    
    def init_ui(self):
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #111827; border-radius: 8px; padding: 16px;")
        header_layout = QHBoxLayout(header)
        
        title_label = QLabel("EzeeCanteen Settings")
        title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #8896d8;  border-bottom: 2px solid #8896d8; border-left: 2px solid #8896d8; border-right: 2px solid #8896d8; border-top: 2px solid #8896d8;")
        header_layout.addWidget(title_label)
        
        button_group = QWidget()
        button_layout = QHBoxLayout(button_group)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        
        display_button = QPushButton("Display")
        display_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        display_button.clicked.connect(self.display_settings)
        button_layout.addWidget(display_button)
        
        meal_button = QPushButton("Canteen")
        meal_button.setStyleSheet("""
            QPushButton {
                background-color: #ca8a04;
                color: white;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a16207;
            }
        """)
        meal_button.clicked.connect(self.meal_settings)
        button_layout.addWidget(meal_button)
        
        clear_cache_button = QPushButton("Clear Cache")
        clear_cache_button.setStyleSheet("""
            QPushButton {
                background-color: #1e8188;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #136066;
            }
        """)
        clear_cache_button.clicked.connect(self.clear_cache)
        button_layout.addWidget(clear_cache_button)
        
        button_group.setLayout(button_layout)
        header_layout.addWidget(button_group, alignment=Qt.AlignRight)
        self.main_layout.addWidget(header)
        
        
        # Printer Settings
        printer_frame = QFrame()
        printer_frame.setStyleSheet("background-color: #111827; border-radius: 8px; padding: 12px; margin-top: 10px;")
        printer_layout = QVBoxLayout(printer_frame)
        printer_layout.setSpacing(2)  # Further reduced spacing
        printer_layout.setContentsMargins(10, 8, 10, 8)  # Reduced margins
        
        printer_title = QLabel("🖨️ Printer Settings")
        printer_title.setStyleSheet("font-size: 24px; font-weight: bold; border-bottom: 1px solid #374151; padding-bottom: 8px; margin-bottom: 6px;")
        printer_layout.addWidget(printer_title)
        
        # Scrollable area for printers - full width
        printers_scroll = QScrollArea()
        printers_scroll.setWidgetResizable(True)
        printers_scroll.setStyleSheet("border: none; background-color: transparent;")
        printers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        printers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.printers_list = QWidget()
        self.printers_list.setStyleSheet("background-color: transparent;")
        self.printers_layout = QVBoxLayout(self.printers_list)
        self.printers_layout.setContentsMargins(0, 0, 0, 0)
        self.printers_layout.setSpacing(2)  # Minimal spacing between printers
        self.printers_layout.setAlignment(Qt.AlignTop)  # Align to top
        printers_scroll.setWidget(self.printers_list)
        printer_layout.addWidget(printers_scroll)
        
        add_printer_button = QPushButton("Add Printer")
        add_printer_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        add_printer_button.clicked.connect(self.add_printer)
        add_printer_layout = QHBoxLayout()
        add_printer_layout.addStretch()
        add_printer_layout.addWidget(add_printer_button)
        printer_layout.addLayout(add_printer_layout)
        
        self.main_layout.addWidget(printer_frame)
        
        # Device Settings
        device_frame = QFrame()
        device_frame.setStyleSheet("background-color: #111827; border-radius: 8px; padding: 12px; margin-top: 10px;")
        device_layout = QVBoxLayout(device_frame)
        device_layout.setSpacing(2)  # Further reduced spacing
        device_layout.setContentsMargins(10, 8, 10, 8)  # Reduced margins
        
        device_title = QLabel("📱 Device Settings")
        device_title.setStyleSheet("font-size: 22px; font-weight: bold; border-bottom: 1px solid #374151; padding-bottom: 8px; margin-bottom: 6px;")
        device_layout.addWidget(device_title)
        
        # Scrollable area for devices - full width
        devices_scroll = QScrollArea()
        devices_scroll.setWidgetResizable(True)
        devices_scroll.setStyleSheet("border: none; background-color: transparent;")
        devices_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        devices_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.devices_list = QWidget()
        self.devices_list.setStyleSheet("background-color: transparent;")
        self.devices_layout = QVBoxLayout(self.devices_list)
        self.devices_layout.setContentsMargins(0, 0, 0, 0)
        self.devices_layout.setSpacing(2)  # Minimal spacing between devices
        self.devices_layout.setAlignment(Qt.AlignTop)  # Align to top
        devices_scroll.setWidget(self.devices_list)
        device_layout.addWidget(devices_scroll)
        
        add_device_button = QPushButton("Add Device")
        add_device_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        add_device_button.clicked.connect(self.add_device)
        add_device_layout = QHBoxLayout()
        add_device_layout.addStretch()
        add_device_layout.addWidget(add_device_button)
        device_layout.addLayout(add_device_layout)
        
        self.main_layout.addWidget(device_frame)
        
        # Footer
        footer = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #9ca3af; font-size: 16px; margin-top: 40px;")
        self.main_layout.addWidget(footer)
        
        # Status check timers
        self.device_status_timer = QTimer(self)
        self.device_status_timer.timeout.connect(self.check_device_status_and_update_ui)
        self.device_status_timer.start(1000)
        
        self.printer_status_timer = QTimer(self)
        self.printer_status_timer.timeout.connect(self.check_printer_status_and_update_ui)
        self.printer_status_timer.start(1000)
    
    async def initialize_toggle_state(self):
        try:
            app_settings = await self.load_settings_mock()
            server_setting = app_settings.get('ServerSetting', {'DPToggle': 'YES', 'Port': ''})
            self.toggle.setChecked(server_setting['DPToggle'] == 'YES')
            self.port_number_input.setText(server_setting['Port'])
            self.port_number = server_setting['Port']
            self.port_input_widget.setVisible(not self.toggle.isChecked())
        except Exception as e:
            print(f"Toggle Error loading settings: {e}")
    
    def toggle_dynamic_port(self):
        is_checked = self.toggle.isChecked()
        self.port_input_widget.setVisible(not is_checked)
        if is_checked:
            loop = asyncio.get_event_loop()
            loop.create_task(self.save_server_settings())
    
    async def save_server_settings(self):
        app_settings = await self.load_settings_mock()
        self.port_number = self.port_number_input.text()
        server_settings = {
            'Port': self.port_number,
            'DPToggle': 'YES' if self.toggle.isChecked() else 'NO'
        }
        app_settings['ServerSetting'] = server_settings
        try:
            await self.save_settings_mock(app_settings)
            print("Server settings saved successfully!")
        except Exception as e:
            print(f"Error saving server settings: {e}")
    
    async def check_device_status(self, device):
        # Placeholder: Implement actual device status check
        return "online" if device.get('ip') else "offline"
    
    async def check_printer_status(self, printer):
        # Placeholder: Implement actual printer status check
        return "online" if printer.get('ip') else "offline"
    
    def check_device_status_and_update_ui(self):
        # Guard against window closing or widgets being destroyed
        if not hasattr(self, 'devices_list') or self.devices_list is None:
            return
            
        # Convert this to a synchronous method to avoid asyncio warnings
        for index, device in enumerate(self.devices):
            try:
                # Use a synchronous status check instead
                is_enabled = device.get('enable') == 'Y'
                has_ip = bool(device.get('ip'))
                
                # Device is online if it has IP and is enabled
                status = "online" if is_enabled and has_ip else "offline"
                
                device_widget = self.devices_list.findChild(QFrame, f"device-{index}")
                if device_widget and not sip.isdeleted(device_widget):
                    if status == "online":
                        device_widget.setStyleSheet("background-color: #15803d; border-radius: 6px; padding: 2px 4px; margin-bottom: 2px;")
                    else:
                        device_widget.setStyleSheet("background-color: #b91c1c; border-radius: 6px; padding: 2px 4px; margin-bottom: 2px;")
                    
                    edit_button = device_widget.findChild(QPushButton, f"editDButton-{index}")  
                    if edit_button and not sip.isdeleted(edit_button):
                        if status == "online":
                            edit_button.setStyleSheet("""
                                QPushButton {
                                    background-color: #ca8a04;
                                    color: white;
                                    padding: 1px 4px;
                                    border-radius: 3px;
                                    font-weight: bold;
                                    font-size: 11px;
                                }
                                QPushButton:hover {
                                    background-color: #a16207;
                                }
                            """)
                        else:
                            edit_button.setStyleSheet("""
                                QPushButton {
                                    background-color: #4b5563;
                                    color: white;
                                    padding: 1px 4px;
                                    border-radius: 3px;
                                    font-weight: bold;
                                    font-size: 11px;
                                }
                                QPushButton:hover {
                                    background-color: #6b7280;
                                }
                            """)

            except Exception as e:
                pass  # Silently handle errors to prevent console spam
    
    def check_printer_status_and_update_ui(self):
        # Guard against window closing or widgets being destroyed
        if not hasattr(self, 'printers_list') or self.printers_list is None:
            return
            
        # Convert this to a synchronous method to avoid asyncio warnings
        for index, printer in enumerate(self.printers):
            try:
                # Use a synchronous status check instead
                is_enabled = printer.get('enable') == 'Y'
                has_ip = bool(printer.get('ip'))
                
                # Printer is online if it has IP and is enabled
                status = "online" if is_enabled and has_ip else "offline"
                
                printer_widget = self.printers_list.findChild(QFrame, f"printer-{index}")
                if printer_widget and not sip.isdeleted(printer_widget):
                    if status == "online":
                        printer_widget.setStyleSheet("background-color: #15803d; border-radius: 4px; padding: 2px 4px; margin-bottom: 2px;")
                    else:
                        printer_widget.setStyleSheet("background-color: #b91c1c; border-radius: 4px; padding: 2px 4px; margin-bottom: 2px;")
                    
                    edit_button = printer_widget.findChild(QPushButton, f"editPButton-{index}")
                    if edit_button and not sip.isdeleted(edit_button):
                        if status == "online":
                            edit_button.setStyleSheet("""
                                QPushButton {
                                    background-color: #ca8a04;
                                    color: white;
                                    padding: 1px 4px;
                                    border-radius: 3px;
                                    font-weight: bold;
                                    font-size: 11px;
                                }
                                QPushButton:hover {
                                    background-color: #a16207;
                                }
                            """)
                        else:
                            edit_button.setStyleSheet("""
                                QPushButton {
                                    background-color: #4b5563;
                                    color: white;
                                    padding: 1px 4px;
                                    border-radius: 3px;
                                    font-weight: bold;
                                    font-size: 11px;
                                }
                                QPushButton:hover {
                                    background-color: #6b7280;
                                }
                            """)
            except Exception as e:
                pass  # Silently handle errors to prevent console spam

    async def load_settings(self):
        print("\n========== STARTING LOAD SETTINGS ==========")
        try:
            print("Starting settings load process...")
            # First try to fetch from database
            print("Calling fetch_devices_from_db...")
            db_printers, db_devices = await self.fetch_devices_from_db()
            print(f"fetch_devices_from_db returned {len(db_printers)} printers and {len(db_devices)} devices")
            
            # If no data was fetched from database, fall back to mock data
            if not db_printers and not db_devices:
                print("No devices found in database, falling back to mock data")
                app_settings = await self.load_settings_mock()
                self.printers = app_settings.get('printers', [])
                self.devices = app_settings.get('devices', [])
                print(f"Loaded mock data: {len(self.printers)} printers and {len(self.devices)} devices")
            else:
                print("Using database devices")
                self.printers = db_printers
                self.devices = db_devices
            
            print(f"Before populate UI: {len(self.printers)} printers and {len(self.devices)} devices")


            # Populate the UI
            print("Populating printers in UI...")
            self.populate_printers()
            print("Populating devices in UI...")
            self.populate_devices()
            print("✅ UI population complete")
            print("========== FINISHED LOAD SETTINGS ==========\n")
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            import traceback
            traceback.print_exc()
            # Fall back to mock data on error
            try:
                print("Attempting to load mock data after error...")
                app_settings = await self.load_settings_mock()
                self.printers = app_settings.get('printers', [])
                self.devices = app_settings.get('devices', [])
                self.populate_printers()
                self.populate_devices()
                print("✅ Successfully loaded mock data after error")
            except Exception as err:
                print(f"❌❌ Fatal error loading settings: {err}")
                traceback.print_exc()
    
    def populate_printers(self):
        # Clear existing widgets
        for i in reversed(range(self.printers_layout.count())):
            widget = self.printers_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for index, printer in enumerate(self.printers):
            printer_widget = QFrame()
            printer_widget.setObjectName(f"printer-{index}")
            printer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Expand horizontally, fixed height
            
            # Set background color based on enable status
            if printer.get('enable') == 'Y':
                printer_widget.setStyleSheet("background-color: #15803d; border-radius: 4px; padding: 2px 4px; margin-bottom: 2px;")
            else:
                printer_widget.setStyleSheet("background-color: #b91c1c; border-radius: 4px; padding: 2px 4px; margin-bottom: 2px;")
            
            printer_layout = QHBoxLayout(printer_widget)
            printer_layout.setContentsMargins(2, 1, 2, 1)  # Further reduced margins
            printer_layout.setSpacing(4)  # Reduced spacing between info and button
            
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(0)  # No spacing between rows
            # Ensure layout doesn't stretch vertically
            info_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                     
            # Use printer number if name is not available
            printer_name = printer.get('name', f"Printer {printer.get('deviceNumber', 'Unknown')}")
            name_label = QLabel(f"<strong>Name:</strong> {printer_name}")
            name_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
            name_label.setFixedHeight(18)  # Fixed height for consistent spacing
            
            ip_label = QLabel(f"<strong>IP:</strong> {printer.get('ip', 'Unknown')}")
            ip_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
            ip_label.setFixedHeight(18)  # Fixed height for consistent spacing
            
            # Show device type
            type_label = QLabel(f"<strong>Type:</strong> {printer.get('type', 'thermal')}")
            type_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
            type_label.setFixedHeight(18)  # Fixed height for consistent spacing
            
            info_layout.addWidget(name_label)
            info_layout.addWidget(ip_label)
            info_layout.addWidget(type_label)
            info_layout.addStretch(0)  # Prevent stretching
            
            printer_layout.addWidget(info_widget, 1)  # Give info widget stretch factor
            
            edit_button = QPushButton("Edit")
            edit_button.setObjectName(f"editPButton-{index}")
            edit_button.setFixedSize(70, 34)  # Smaller button
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #ca8a04;
                    color: white;
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #a16207;
                }
            """)
            edit_button.clicked.connect(lambda _, idx=index: self.edit_printer(idx))
            printer_layout.addWidget(edit_button, 0, Qt.AlignRight | Qt.AlignVCenter)  # No stretch, aligned right
            
            self.printers_layout.addWidget(printer_widget)
    
    def populate_devices(self):
        print(f"populate_devices called with {len(self.devices)} devices")
        # Clear existing widgets
        for i in reversed(range(self.devices_layout.count())):
            widget = self.devices_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for index, device in enumerate(self.devices):
            print(f"Creating widget for device {index}: {device}")
            device_widget = QFrame()
            device_widget.setObjectName(f"device-{index}")
            device_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Expand horizontally, fixed height
            
            # Set background color based on enable status
            if device.get('enable') == 'Y':
                device_widget.setStyleSheet("background-color: #15803d; border-radius: 6px; padding: 2px 4px; margin-bottom: 2px;")
            else:
                device_widget.setStyleSheet("background-color: #b91c1c; border-radius: 6px; padding: 2px 4px; margin-bottom: 2px;")
            
            device_layout = QHBoxLayout(device_widget)
            device_layout.setContentsMargins(2, 1, 2, 1)  # Further reduced margins
            device_layout.setSpacing(4)  # Reduced spacing between info and button
            

            # Create info widget to display device details
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(0)  # No spacing between rows
            # Ensure layout doesn't stretch vertically
            info_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            
            # IP Address label - always shown
            ip_label = QLabel(f"<strong>Device IP:</strong> {device.get('ip', 'Unknown')}")
            ip_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
            ip_label.setFixedHeight(18)  # Fixed height for consistent spacing
            info_layout.addWidget(ip_label)
            
            # Show location if available
            location = device.get('location', '')
            if location:
                location_label = QLabel(f"<strong>Location:</strong> {location}")
                location_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
                location_label.setFixedHeight(18)  # Fixed height for consistent spacing
                info_layout.addWidget(location_label)
            else:
                # Add empty location label to maintain consistent height
                location_label = QLabel("<strong>Location:</strong> -")
                location_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
                location_label.setFixedHeight(18)  # Fixed height for consistent spacing
                info_layout.addWidget(location_label)
            
            # Show assigned printer - either from printerName or find printer by IP
            printer_name = device.get('printerName', '')
            if not printer_name and device.get('printerIP'):
                # Try to find printer name by IP
                for printer in self.printers:
                    if printer.get('ip') == device.get('printerIP'):
                        printer_name = printer.get('name', 'CITIZEN')
                        break
            
            if not printer_name:
                printer_name = '-'
                
            printer_label = QLabel(f"<strong>Assigned Printer:</strong> {printer_name}")
            printer_label.setStyleSheet("color: white; margin: 0; padding: 0; font-size: 14px;")
            printer_label.setFixedHeight(18)  # Fixed height for consistent spacing
            info_layout.addWidget(printer_label)
            info_layout.addStretch(0)  # Prevent stretching
            
            device_layout.addWidget(info_widget, 1)  # Give info widget stretch factor
            
            edit_button = QPushButton("Edit")
            edit_button.setObjectName(f"editDButton-{index}")
            edit_button.setFixedSize(70, 34)  # Smaller button
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #ca8a04;
                    color: white;
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #a16207;
                }
            """)
            edit_button.clicked.connect(lambda _, idx=index: self.edit_device(idx))
            device_layout.addWidget(edit_button, 0, Qt.AlignRight | Qt.AlignVCenter)  # No stretch, aligned right
            
            self.devices_layout.addWidget(device_widget)
        print("populate_devices complete")
    
    def edit_printer(self, index):
        print(f"Edit printer at index {index}")
        # Implement navigation or dialog for editing printer
    
    def edit_device(self, index):
        print(f"Edit device at index {index}")
        # Implement navigation or dialog for editing device
    
    def add_printer(self):
        try:
            # Import the PrinterSetupWindow from AddPrinter
            from AddPrinter import PrinterSetupWindow
            
            # Create the PrinterSetupWindow instance
            self.printer_form = PrinterSetupWindow()
            
            # Find the buttons in the UI using their object names
            back_button = self.printer_form.findChild(QPushButton, "backButton")
            save_button = self.printer_form.findChild(QPushButton, "saveButton")
            
            # Connect back button signal to return to settings
            back_button.clicked.connect(self.return_from_printer_form)
            
            # Connect save button signal to handle saving
            save_button.clicked.connect(self.on_printer_form_save)
            
            # Save current window geometry
            self.saved_geometry = self.geometry()
            
            # Store old central widget
            self.old_central_widget = self.centralWidget()
            
            # Set the printer form as the central widget
            self.setCentralWidget(self.printer_form)
            
        except Exception as e:
            print(f"Error opening printer form: {e}")
            import traceback
            traceback.print_exc()
            
    def return_from_printer_form(self):
        # Remove the printer form
        if hasattr(self, 'printer_form'):
            self.printer_form.setParent(None)
            self.printer_form = None
        
        # Recreate the central widget and UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
        
        # Re-initialize the UI
        self.init_ui()
        
        # Restore original geometry
        if hasattr(self, 'saved_geometry'):
            self.setGeometry(self.saved_geometry)
        
        # Explicitly repopulate the printers and devices with existing data
        self.populate_printers()
        self.populate_devices()
    
    def on_printer_form_save(self):
        try:
            # Validate the form first
            if not self.printer_form.validate_form():
                return
                
            # Get printer data from the form
            printer_data = {
                'name': self.printer_form.printer_name.text().strip(),
                'ip': self.printer_form.printer_ip.text().strip(),
                'type': self.printer_form.printer_type.currentText().lower(),
                'port': self.printer_form.printer_port.text().strip(),
                'enable': 'Y',  # Default to enabled
                'deviceNumber': len(self.printers) + 1,
                'fontSize': self.printer_form.font_size.currentData()
            }
            
            # Add the new printer to the printers list
            self.printers.append(printer_data)
            
            # Save settings using the event loop
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(self.save_settings_mock({'printers': self.printers, 'devices': self.devices}))
            
            # Try to update the database if possible
            self.update_printer_in_database(printer_data)
            
            # Show success message
            QMessageBox.information(self, "Success", "Printer added successfully")
            
            # Return to the settings screen
            self.return_from_printer_form()
            
            # Update the UI - this is now handled in return_from_printer_form
        except Exception as e:
            print(f"Error saving printer: {e}")
            import traceback
            traceback.print_exc()
    
    def update_printer_in_database(self, printer_data):
        try:
            # Connect to the database
            conn = self.db_connect()
            if conn:
                cursor = conn.cursor()
                
                # Check if the printer already exists by IP
                cursor.execute("SELECT COUNT(*) FROM configh WHERE IP = %s AND DeviceType = 'Printer'", 
                              (printer_data['ip'],))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    # Update existing printer
                    cursor.execute("""
                        UPDATE configh 
                        SET DeviceType = 'Printer',
                            DeviceNumber = %s,
                            DeviceLocation = %s,
                            Enable = %s
                        WHERE IP = %s AND DeviceType = 'Printer'
                    """, (printer_data.get('deviceNumber', 1), 
                          printer_data.get('location', ''), 
                          printer_data.get('enable', 'Y'),
                          printer_data['ip']))
                else:
                    # Insert new printer
                    cursor.execute("""
                        INSERT INTO configh 
                        (DeviceType, DeviceNumber, IP, Port, DeviceLocation, Enable, DeviceName) 
                        VALUES ('Printer', %s, %s, %s, %s, %s, %s)
                    """, (printer_data.get('deviceNumber', 1), 
                          printer_data['ip'],
                          printer_data.get('port', '9100'),
                          printer_data.get('location', ''),
                          printer_data.get('enable', 'Y'),
                          printer_data.get('name', 'CITIZEN')))
                
                conn.commit()
                conn.close()
                print(f"Printer saved to database: {printer_data['name']}")
                return True
            return False
        except Exception as e:
            print(f"Error updating printer in database: {e}")
            return False
    
    def add_device(self):
        try:
            # Import the AddDevice module
            from AddDevice import EzeeCanteenDeviceForm
            
            # Create the device form with device_type set to "Device"
            self.device_form = EzeeCanteenDeviceForm(device_type="Device")
            
            # Pass existing printers to the form
            self.device_form.populate_printers(self.printers)
            
            # Connect back button signal to return to settings
            self.device_form.back_button.clicked.disconnect()
            self.device_form.back_button.clicked.connect(self.return_from_device_form)
            
            # Connect device saved signal
            self.device_form.device_saved.connect(self.on_device_saved)
            
            # Save current window geometry
            self.saved_geometry = self.geometry()
            
            # Store old central widget
            self.old_central_widget = self.centralWidget()
            
            # Set the device form as the central widget
            self.setCentralWidget(self.device_form)
            
        except Exception as e:
            print(f"Error opening device form: {e}")
    
    def return_from_device_form(self):
        # Remove the device form
        if hasattr(self, 'device_form'):
            self.device_form.setParent(None)
            self.device_form = None
        
        # Recreate the central widget and UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
        
        # Re-initialize the UI
        self.init_ui()
        
        # Restore original geometry
        if hasattr(self, 'saved_geometry'):
            self.setGeometry(self.saved_geometry)
        
        # Explicitly repopulate the printers and devices with existing data
        self.populate_printers()
        self.populate_devices()
    
    def on_device_saved(self, device_data):
        # Add the new device to the devices list
        self.devices.append(device_data)
        
        # Save the settings using the event loop (for backward compatibility with JSON)
        loop = asyncio.get_event_loop()
        loop.create_task(self.save_settings_mock({'printers': self.printers, 'devices': self.devices}))
        
        # Return to the settings screen
        self.return_from_device_form()
    
    def display_settings(self):
        # Save current window geometry
        self.saved_geometry = self.geometry()
        
        # Create EzeeCanteen widget
        try:
            # Import the timeBase module and get EzeeCanteen window
            from timeBase import main as timebase_main
            ezee_canteen = timebase_main()
            
            # Set up navigating back to settings
            ezee_canteen.settings_mode = True
            ezee_canteen.parent_window = self
            
            # Store old central widget
            self.old_central_widget = self.centralWidget()
            
            # Set EzeeCanteen as central widget
            self.setCentralWidget(ezee_canteen)
            
            # Add back button if EzeeCanteen has a settings button
            if hasattr(ezee_canteen, 'settings_button'):
                ezee_canteen.settings_button.clicked.connect(self.return_from_display)
            
        except Exception as e:
            print(f"Error loading EzeeCanteen view: {e}")
            # If there's an error, fall back to the original approach
            self.close()
            os.system("python timeBase.py")
    
    def return_from_display(self):
        # Remove the display view
        display_view = self.centralWidget()
        if display_view:
            display_view.setParent(None)
        
        # Recreate the central widget and UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
        
        # Re-initialize the UI
        self.init_ui()
        
        # Restore original geometry
        if hasattr(self, 'saved_geometry'):
            self.setGeometry(self.saved_geometry)
        
        # Explicitly repopulate the printers and devices with existing data
        self.populate_printers()    
        self.populate_devices()
    
    def meal_settings(self):
        print("Navigating to canteen settings")
        
        # Save current window geometry
        self.saved_geometry = self.geometry()
        
        try:
            # Create the EzeeCanteenApp instance
            canteen_app = EzeeCanteenApp()
            
            # IMPORTANT: Disconnect the default "go_back" slot and connect our custom function
            # Find the back button in the UI
            back_buttons = canteen_app.findChildren(QPushButton)
            for btn in back_buttons:
                if btn.text() == "Back":
                    print("Found Back button in CanteenSettings, reconnecting...")
                    # Disconnect any existing connections
                    try:
                        btn.clicked.disconnect()
                    except Exception:
                        pass
                    # Connect directly to our return function
                    btn.clicked.connect(self.return_from_canteen_settings)
            
            # Store old central widget
            self.old_central_widget = self.centralWidget()
            
            # Set canteen app as central widget
            self.setCentralWidget(canteen_app)
            
        except Exception as e:
            print(f"Error loading Canteen Settings view: {e}")
            import traceback
            traceback.print_exc()

    def return_from_canteen_settings(self):
        # Remove the canteen settings view
        canteen_view = self.centralWidget()
        if canteen_view:
            canteen_view.setParent(None)
        
        # Recreate the central widget and UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
        
        # Re-initialize the UI
        self.init_ui()
        
        # Restore original geometry
        if hasattr(self, 'saved_geometry'):
            self.setGeometry(self.saved_geometry)
        
        # Explicitly repopulate the printers and devices with existing data
        self.populate_printers()    
        self.populate_devices()
    
    async def clear_cache(self):
        self.loading_overlay = LoadingOverlay(self)
        
        # Disable main window interaction
        self.central_widget.setEnabled(False)
        self.central_widget.setStyleSheet("""
            background-color: #1f2937; 
            color: white; 
            font-family: Arial, sans-serif;
            opacity: 0.5;
        """)
        
        self.loading_overlay.show()
        try:
            # Placeholder for clear cache logic
            await asyncio.sleep(2)
            self.loading_overlay.loading_label.setText("Cache Cleared")
            self.loading_overlay.dots_label.setText("")
            self.loading_overlay.dot_timer.stop()
            
            # Hide overlay after a short delay
            await asyncio.sleep(0.5)
            self.loading_overlay.hide()
            
            # Re-enable main window
            self.central_widget.setEnabled(True)
            self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
            
            print("Cache cleared successfully!")
        except Exception as e:
            print(f"Error clearing cache: {e}")
            self.loading_overlay.hide()
            
            # Re-enable main window
            self.central_widget.setEnabled(True)
            self.central_widget.setStyleSheet("background-color: #1f2937; color: white; font-family: Arial, sans-serif;")
            
            print("Failed to clear cache!")
    
    async def load_settings_mock(self):
        # Load settings from appSettings.json
        import json
        import os
        
        file_path = 'appSettings.json'
        settings = {
            'ServerSetting': {'DPToggle': 'YES', 'Port': '8080'},
            'printers': [],
            'devices': []
        }
        
        # Load from file if it exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    file_settings = json.load(file)
                    
                    # Update settings with values from file
                    if 'ServerSetting' in file_settings:
                        settings['ServerSetting'] = file_settings['ServerSetting']
                    
                    if 'printers' in file_settings:
                        settings['printers'] = file_settings['printers']
                    
                    if 'devices' in file_settings:
                        settings['devices'] = file_settings['devices']
                        
                print(f"Settings loaded from {file_path}")
            except Exception as e:
                print(f"Error loading settings from {file_path}: {e}")
                # Use default mock data if file read fails
                settings = {
                    'ServerSetting': {'DPToggle': 'YES', 'Port': '8080'},
                    'printers': [
                        {'name': 'Printer1', 'ip': '192.168.1.100', 'type': 'Laser', 'enable': 'Y'},
                        {'name': 'Printer2', 'ip': '192.168.1.101', 'type': 'Inkjet', 'enable': 'Y'}
                    ],
                    'devices': [
                        {'deviceType': 'Device', 'ip': '192.168.1.200', 'location': 'Kitchen', 'printerName': 'Printer1', 'enable': 'Y'},
                        {'deviceType': 'Device', 'ip': '192.168.1.201', 'location': 'Counter', 'printerName': 'Printer2', 'enable': 'Y'}
                    ]
                }
        else:
            print(f"Settings file {file_path} not found, using default values")
            # If file doesn't exist, use default mock data
            settings = {
                'ServerSetting': {'DPToggle': 'YES', 'Port': '8080'},
                'printers': [
                    {'name': 'Printer1', 'ip': '192.168.1.100', 'type': 'Laser', 'enable': 'Y'},
                    {'name': 'Printer2', 'ip': '192.168.1.101', 'type': 'Inkjet', 'enable': 'Y'}
                ],
                'devices': [
                    {'deviceType': 'Device', 'ip': '192.168.1.200', 'location': 'Kitchen', 'printerName': 'Printer1', 'enable': 'Y'},
                    {'deviceType': 'Device', 'ip': '192.168.1.201', 'location': 'Counter', 'printerName': 'Printer2', 'enable': 'Y'}
                ]
            }
            
        return settings
    
    async def save_settings_mock(self, settings):
        # Load existing settings from appSettings.json
        import json
        import os
        
        file_path = 'appSettings.json'
        existing_settings = {}
        
        # Load existing settings if file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    existing_settings = json.load(file)
            except Exception as e:
                print(f"Error reading existing settings: {e}")
        
        # Update with new settings while preserving existing ones
        if 'printers' in settings:
            existing_settings['printers'] = settings['printers']
        
        if 'devices' in settings:
            existing_settings['devices'] = settings['devices']
        
        if 'ServerSetting' in settings:
            existing_settings['ServerSetting'] = settings['ServerSetting']
        
        # Save updated settings back to file
        try:
            with open(file_path, 'w') as file:
                json.dump(existing_settings, file, indent=4)
            print(f"Settings saved to {file_path}: {existing_settings}")
        except Exception as e:
            print(f"Error saving settings to {file_path}: {e}")

    def test_connection(self):
        """Test database connection and show results in a message box"""
        try:
            print(f"Testing connection to {DB_HOST}:{DB_PORT}...")
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            print("Connection successful!")
            
            # Get database version
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            version_info = f"Database version: {version[0]}"
            print(version_info)
            
            # Check table structure using information_schema for accurate column names
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'configh'
                ORDER BY ORDINAL_POSITION
            """, (DB_NAME,))
            
            columns = cursor.fetchall()
            column_info = "\nConfigh table structure:\n"
            for col in columns:
                column_info += f"- {col[0]} ({col[1]}, {col[2]}, {col[3]})\n"
                print(f"- {col[0]} ({col[1]}, {col[2]}, {col[3]})")
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM configh")
            count = cursor.fetchone()
            count_info = f"\nTotal rows in configh table: {count[0]}"
            print(count_info)
            
            # Get sample data
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT DeviceType, DeviceNumber, IP, Enable FROM configh LIMIT 3")
            rows = cursor.fetchall()
            
            sample_data = "\nSample data:\n"
            for i, row in enumerate(rows):
                sample_data += f"Row {i+1}: {row['DeviceType']}, #{row['DeviceNumber']}, IP: {row['IP']}, Enable: {row['Enable']}\n"
            print(sample_data)
            
            # Show results in a message box
            QMessageBox.information(self, "Database Connection", 
                                    f"Connection successful!\n{version_info}\n{count_info}\n{sample_data}")
            
            conn.close()
            return True
        except mysql.connector.Error as err:
            error_msg = f"Database connection error: {err}"
            print(error_msg)
            QMessageBox.critical(self, "Database Error", error_msg)
            return False

    async def test_fetch_devices(self):
        """Manual test function to fetch devices and update UI"""
        try:
            QMessageBox.information(self, "Testing Database Fetch", "Fetching devices from database...")
            
            # Perform the database fetch
            printers, devices = await self.fetch_devices_from_db()
            
            # If we got results, update the UI
            if printers or devices:
                self.printers = printers
                self.devices = devices
                self.populate_printers()
                self.populate_devices()
                
                # Show results
                QMessageBox.information(self, "Fetch Complete", 
                                       f"Successfully loaded {len(printers)} printers and {len(devices)} devices.")
            else:
                QMessageBox.warning(self, "No Devices Found", 
                                  "No devices were found in the database. Check the database connection and table contents.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch devices: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set up asyncio event loop
    import nest_asyncio
    nest_asyncio.apply()
    
    window = EzeeCanteenWindow()
    
    # Check if test_connection command line argument is provided
    if len(sys.argv) > 1 and sys.argv[1] == 'test_db':
        print("Testing database connection...")
        window.test_connection()
    
    window.show()
    sys.exit(app.exec_())
else:
    # If imported, the main function will just create the window instance
    def main():
        return EzeeCanteenWindow()