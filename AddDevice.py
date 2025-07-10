import sys
import json
import os
import mysql.connector
from datetime import datetime   
import requests
from requests.auth import HTTPDigestAuth
import re
import socket
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QRadioButton, QButtonGroup, QMessageBox,
                             QFrame, QListWidget, QListWidgetItem, QDialog,
                             QProgressBar, QTextEdit, QGroupBox, QCheckBox,
                             QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon
from licenseManager import LicenseManager


# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"


class DeviceScannerThread(QThread):
    """Thread for scanning network devices"""
    device_found = pyqtSignal(dict)
    scan_progress = pyqtSignal(str)
    scan_complete = pyqtSignal(list)
    
    def __init__(self, username="admin", password="a1234@4321", subnet=None):
        super().__init__()
        self.username = username
        self.password = password
        self.subnet = subnet
        self.found_devices = []
        
    def get_subnet(self):
        """Get current subnet automatically"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return '.'.join(ip.split('.')[:-1])
        except:
            return "192.168.1"
    
    def check_device(self, ip):
        """Check if IP is a Hikvision device"""
        try:
            # Quick port check first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            if sock.connect_ex((ip, 80)) != 0:
                sock.close()
                return None
            sock.close()
            
            # Try to get device info
            r = requests.get(f"http://{ip}/ISAPI/System/deviceinfo", 
                           auth=HTTPDigestAuth(self.username, self.password), 
                           timeout=2)
            
            if r.status_code == 200 and 'DeviceInfo' in r.text:
                model = re.search(r'<model>(.*?)</model>', r.text)
                name = re.search(r'<deviceName>(.*?)</deviceName>', r.text)
                serial = re.search(r'<serialNumber>(.*?)</serialNumber>', r.text)
                
                device_info = {
                    'ip': ip,
                    'model': model.group(1) if model else 'Unknown',
                    'name': name.group(1) if name else 'Unknown',
                    'serial': serial.group(1) if serial else 'Unknown',
                    'port': '80',
                    'username': self.username,
                    'password': self.password
                }
                
                self.device_found.emit(device_info)
                return device_info
        except Exception as e:
            pass
        return None
    
    def run(self):
        """Run the network scan"""
        if not self.subnet:
            self.subnet = self.get_subnet()
        
        self.scan_progress.emit(f"Scanning network: {self.subnet}.0/24")
        
        # Generate IPs to scan
        ips = [f"{self.subnet}.{i}" for i in range(1, 255)]
        
        # Parallel scan with thread pool
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(self.check_device, ip) for ip in ips]
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    self.found_devices.append(result)
                
                # Update progress
                progress = f"Scanned {i+1}/254 addresses... Found {len(self.found_devices)} devices"
                self.scan_progress.emit(progress)
        
        self.scan_complete.emit(self.found_devices)


class DeviceSelectionDialog(QDialog):
    """Dialog for selecting detected devices"""
    devices_selected = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detected_devices = []
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Auto-Detect Devices')
        self.setGeometry(200, 200, 850, 650)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #1e293b; color: white;")
           
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        # Title
        title_label = QLabel("Network Device Detection")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("""
            margin-bottom: 12px; 
            padding: 12px; 
            border-bottom: 2px solid #4b5563;
            color: #f8fafc;
        """)
        layout.addWidget(title_label)

        # Credential input section
        cred_group = QGroupBox("Device Credentials")
        cred_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                padding-top: 10px;
                margin-top: 8px;
                color: #e2e8f0;
                border: 1px solid #374151;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: #1e293b;
            }
        """)
        cred_layout = QVBoxLayout(cred_group)
        cred_layout.setSpacing(8)  # Reduced spacing
        cred_layout.setContentsMargins(15, 18, 15, 15)  # Reduced margins

        # Helper function for consistent field styling
        def create_credential_field(label_text, widget, placeholder="", is_password=False):
            # Label
            label = QLabel(label_text)
            label.setStyleSheet("""
                font-size: 13px; 
                font-weight: 500;
                color: #e2e8f0;
                margin-bottom: 2px;
                margin-top: 4px;
            """)
            cred_layout.addWidget(label)
            
            # Widget styling
            widget.setMinimumHeight(38)  # Slightly reduced height
            if placeholder:
                widget.setPlaceholderText(placeholder)
            if is_password:
                widget.setEchoMode(QLineEdit.Password)
            
            widget.setStyleSheet("""
                QLineEdit {
                    background-color: #0f172a;
                    border: 1px solid #374151;
                    padding: 8px 12px;
                    border-radius: 6px;
                    margin-bottom: 6px;
                    font-size: 13px;
                    color: #f1f5f9;
                }
                QLineEdit:focus {
                    border: 2px solid #3b82f6;
                    background-color: #0f172a;
                }
                QLineEdit::placeholder {
                    color: #94a3b8;
                }
            """)
            cred_layout.addWidget(widget)

        # Username input
        self.username_input = QLineEdit("admin")
        create_credential_field("Username:", self.username_input)

        # Password input
        self.password_input = QLineEdit("a1234@4321")
        create_credential_field("Password:", self.password_input, is_password=True)

        # Subnet input (optional)
        self.subnet_input = QLineEdit()
        create_credential_field("Subnet (optional - auto-detected if empty):", self.subnet_input, "192.168.1 (leave empty for auto-detection)")

        # Add small spacing before button
        cred_layout.addSpacing(8)

        # Scan button
        self.scan_button = QPushButton("Start Network Scan")
        self.scan_button.setMinimumHeight(42)  # Slightly reduced height
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                margin: 8px 0;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #6b7280;
                color: #9ca3af;
            }
        """)
        self.scan_button.clicked.connect(self.start_scan)
        cred_layout.addWidget(self.scan_button)

        layout.addWidget(cred_group)

        
        # Progress section
        self.progress_label = QLabel("Ready to scan...")
        self.progress_label.setStyleSheet("color: #9ca3af; margin: 15px 0; font-size: 13px;")
        layout.addWidget(self.progress_label)
        
        # Device list section
        device_group = QGroupBox("Detected Devices")
        device_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                padding-top: 15px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        device_layout = QVBoxLayout(device_group)
        device_layout.setContentsMargins(20, 25, 20, 20)
        
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget {
                background-color: #0f172a;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px;
                margin: 3px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
            }
            QListWidget::item:hover {
                background-color: #1e40af;
            }
        """)
        self.device_list.setSelectionMode(QListWidget.MultiSelection)
        device_layout.addWidget(self.device_list)
        
        layout.addWidget(device_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        self.add_selected_button = QPushButton("Add Selected Devices")
        self.add_selected_button.setMinimumHeight(40)
        self.add_selected_button.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        self.add_selected_button.clicked.connect(self.add_selected_devices)
        self.add_selected_button.setEnabled(False)
        
        self.close_button = QPushButton("Close")
        self.close_button.setMinimumHeight(40)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.add_selected_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def start_scan(self):
        """Start the network scanning process"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        subnet = self.subnet_input.text().strip() or None
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter username and password")
            return
        
        # Clear previous results
        self.device_list.clear()
        self.detected_devices.clear()
        
        # Disable scan button and enable progress updates
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")
        self.add_selected_button.setEnabled(False)
        
        # Start scanning thread
        self.scanner_thread = DeviceScannerThread(username, password, subnet)
        self.scanner_thread.device_found.connect(self.on_device_found)
        self.scanner_thread.scan_progress.connect(self.on_scan_progress)
        self.scanner_thread.scan_complete.connect(self.on_scan_complete)
        self.scanner_thread.start()
    
    def on_device_found(self, device_info):
        """Handle when a device is found"""
        self.detected_devices.append(device_info)
        
        # Add to list widget
        item_text = f"📱 {device_info['ip']} - {device_info['model']} ({device_info['name']})"
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, device_info)
        self.device_list.addItem(item)
    
    def on_scan_progress(self, progress_text):
        """Update progress label"""
        self.progress_label.setText(progress_text)
    
    def on_scan_complete(self, found_devices):
        """Handle scan completion"""
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Start Network Scan")
        
        if found_devices:
            self.add_selected_button.setEnabled(True)
            self.progress_label.setText(f"Scan complete! Found {len(found_devices)} devices.")
        else:
            self.progress_label.setText("Scan complete. No devices found.")
    
    def add_selected_devices(self):
        """Add selected devices and close dialog"""
        selected_devices = []
        for item in self.device_list.selectedItems():
            device_info = item.data(Qt.UserRole)
            selected_devices.append(device_info)
        
        if not selected_devices:
            QMessageBox.warning(self, "Selection Error", "Please select at least one device")
            return
        
        self.devices_selected.emit(selected_devices)
        self.accept()


class EzeeCanteenDeviceForm(QMainWindow):
    # Signal to emit when a device is saved
    device_saved = pyqtSignal(dict)
    
    def __init__(self, device_type="Device", edit_device=None):
        super().__init__()
        self.device_type = device_type
        self.edit_mode = edit_device is not None
        self.edit_device = edit_device or {}
        self.license_key = self.get_license_key()
        self.initUI()

    def get_license_key(self):
        """Get license key from LicenseManager"""
        try:
            # We need to run the async method in a synchronous context
            def get_license_data():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    license_manager = LicenseManager()
                    license_data = loop.run_until_complete(license_manager.get_license_db())
                    return license_data
                finally:
                    loop.close()
            
            # Get license data and extract the key
            license_data = get_license_data()
            if license_data and 'LicenseKey' in license_data:
                return license_data['LicenseKey']
        except Exception as e:
            print(f"Error getting license key: {str(e)}")
        return None

    def initUI(self):
        from PyQt5.QtWidgets import QScrollArea
        # Set window properties
        self.setWindowTitle('EzeeCanteen')
        self.setGeometry(100, 100, 750, 750)
        self.setMinimumSize(700, 650)  # Reduced minimum height
        self.setStyleSheet("background-color: #1e293b; color: white;")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 15)  # Reduced margins
        main_layout.setSpacing(10)  # Reduced spacing
        
        # Create scroll area to handle overflow
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #374151;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #6b7280;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9ca3af;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 10, 0)  # Small right margin for scrollbar
        scroll_layout.setSpacing(10)
        
        # Create form container with dark background
        form_container = QFrame()
        form_container.setFrameShape(QFrame.StyledPanel)
        form_container.setStyleSheet("background-color: #0f172a; border-radius: 10px; padding: 20px;")
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(8)  # Further reduced spacing
        
        # Title
        title_text = f"Edit {self.device_type}" if self.edit_mode else f"Add {self.device_type}"
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("""
            margin-bottom: 8px; 
            padding-bottom: 8px; 
            border-bottom: 2px solid #4b5563;
            color: #f8fafc;
        """)
        form_layout.addWidget(title_label)
        
        # Auto-detect button section (only show when not in edit mode)
        if not self.edit_mode:
            detect_layout = QHBoxLayout()
            detect_layout.setSpacing(15)
            self.auto_detect_button = QPushButton("🔍 Auto-Detect Devices")
            self.auto_detect_button.setMinimumHeight(42)
            self.auto_detect_button.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: white;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 11px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
                QPushButton:pressed {
                    background-color: #b45309;
                }
            """)
            self.auto_detect_button.clicked.connect(self.open_auto_detect_dialog)
            detect_layout.addWidget(self.auto_detect_button)
            detect_layout.addStretch()
            form_layout.addLayout(detect_layout)
        
        # Helper function to create form fields
        def create_form_field(label_text, widget, placeholder="", is_password=False):
            # Label
            label = QLabel(label_text)
            label.setStyleSheet("""
                font-size: 13px; 
                font-weight: 500;
                color: #e2e8f0;
                margin-bottom: 2px;
                margin-top: 4px;
            """)
            form_layout.addWidget(label)
            
            # Widget styling
            if isinstance(widget, QLineEdit):
                widget.setMinimumHeight(38)
                if placeholder:
                    widget.setPlaceholderText(placeholder)
                if is_password:
                    widget.setEchoMode(QLineEdit.Password)
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #1e293b;
                        border: 1px solid #374151;
                        padding: 8px 12px;
                        border-radius: 6px;
                        margin-bottom: 6px;
                        font-size: 13px;
                        color: #f1f5f9;
                    }
                    QLineEdit:focus {
                        border: 2px solid #3b82f6;
                        background-color: #1e293b;
                    }
                    QLineEdit::placeholder {
                        color: #94a3b8;
                    }
                """)
            elif isinstance(widget, QComboBox):
                widget.setMinimumHeight(38)
                widget.setStyleSheet("""
                    QComboBox {
                        background-color: #1e293b;
                        border: 1px solid #374151;
                        padding: 8px 12px;
                        border-radius: 6px;
                        margin-bottom: 6px;
                        font-size: 13px;
                        color: #f1f5f9;
                    }
                    QComboBox:focus {
                        border: 2px solid #3b82f6;
                    }
                    QComboBox::drop-down {
                        width: 30px;
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: none;
                        border-left: 5px solid transparent;
                        border-right: 5px solid transparent;
                        border-top: 5px solid #94a3b8;
                        margin-right: 5px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #1e293b;
                        border: 1px solid #4b5563;
                        selection-background-color: #3b82f6;
                        font-size: 13px;
                        color: #f1f5f9;
                        outline: none;
                    }
                """)
            
            form_layout.addWidget(widget)
        
        # IP Address field
        self.ip_address = QLineEdit()
        create_form_field("IP Address", self.ip_address, "192.168.100.100")
        
        # Port field
        self.port = QLineEdit()
        create_form_field("Port", self.port, "80")
        
        # Username field
        self.username = QLineEdit()
        create_form_field("Username", self.username, "admin")
        
        # Password field
        self.password = QLineEdit()
        create_form_field("Password", self.password, "password", True)
        
        # Select Printer field
        self.printer_combo = QComboBox()
        self.printer_combo.addItem("Select a printer")
        create_form_field("Select Printer", self.printer_combo)
        
        # Fetch printers from database and populate the dropdown
        self.fetch_printers_from_db()
        
        # Enable Device field
        enable_label = QLabel("Enable Device")
        enable_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 500;
            color: #e2e8f0;
            margin-bottom: 3px;
            margin-top: 4px;
        """)
        form_layout.addWidget(enable_label)
        
        live_layout = QHBoxLayout()
        live_layout.setSpacing(25)
        live_layout.setContentsMargins(0, 0, 0, 6)
        
        self.enable_radio = QRadioButton("Enable")
        self.enable_radio.setStyleSheet("""
            QRadioButton {
                font-size: 13px;
                color: #f1f5f9;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #6b7280;
                border-radius: 8px;
                background-color: transparent;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #22c55e;
                border-radius: 8px;
                background-color: #22c55e;
            }
        """)
        
        self.disable_radio = QRadioButton("Disable")
        self.disable_radio.setStyleSheet("""
            QRadioButton {
                font-size: 13px;
                color: #f1f5f9;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #6b7280;
                border-radius: 8px;
                background-color: transparent;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #ef4444;
                border-radius: 8px;
                background-color: #ef4444;
            }
        """)
        
        self.enable_radio.setChecked(True)
        
        live_group = QButtonGroup(self)
        live_group.addButton(self.enable_radio)
        live_group.addButton(self.disable_radio)
        
        live_layout.addWidget(self.enable_radio)
        live_layout.addWidget(self.disable_radio)
        live_layout.addStretch()
        form_layout.addLayout(live_layout)
        
        # Location field
        self.location = QLineEdit()
        create_form_field("Location", self.location, "Room 101 Front Desk")
        
        # Add some spacing before buttons
        form_layout.addSpacing(10)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        self.back_button = QPushButton("Back")
        self.back_button.setMinimumHeight(42)
        self.back_button.setMinimumWidth(100)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        self.back_button.clicked.connect(self.back_clicked)
        
        save_text = "Update Device" if self.edit_mode else "Save Device"
        self.save_button = QPushButton(save_text)
        self.save_button.setMinimumHeight(42)
        self.save_button.setMinimumWidth(120)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:pressed {
                background-color: #15803d;
            }
        """)
        self.save_button.clicked.connect(self.save_device)
        
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.save_button)
        form_layout.addLayout(button_layout)
        
        # Add form container to scroll layout
        scroll_layout.addWidget(form_container)
        scroll_layout.addStretch()  # Add stretch to push content to top
        
        # Set scroll widget and add to scroll area
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Footer
        footer = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #94a3b8; 
            margin-top: 10px; 
            margin-bottom: 5px;
            font-size: 11px;
            font-weight: 500;
        """)
        main_layout.addWidget(footer)
        
        # If in edit mode, populate form with device data
        if self.edit_mode and self.edit_device:
            self.populate_form()

    def fetch_printers_from_db(self):
        """Fetch printers from the database and populate the dropdown"""
        try:
            conn = self.db_connect()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            # Query to fetch printers from the database
            sql = """
            SELECT SrNo, DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser,
                   Enable, DevicePrinterIP 
            FROM configh 
            WHERE LicenseKey = %s AND DeviceType != 'Device'
            ORDER BY DeviceType, DeviceNumber
            """
            
            cursor.execute(sql, (self.license_key,))
            printers = cursor.fetchall()
            
            # Clear existing items
            self.printer_combo.clear()
            self.printer_combo.addItem("Select a printer")
            
            # Add printers to the dropdown
            for printer in printers:
                device_type = printer[1]
                device_number = printer[2]
                ip = printer[3]
                location = printer[5]
                
                # Create display name
                display_name = f"{device_type} {device_number} - {ip}"
                if location:
                    display_name += f" ({location})"
                
                # Create printer data
                printer_data = {
                    'name': f"{device_type} {device_number}",
                    'ip': ip,
                    'deviceType': device_type,
                    'deviceNumber': device_number,
                    'location': location
                }
                
                # Add to dropdown
                self.printer_combo.addItem(display_name)
                self.printer_combo.setItemData(self.printer_combo.count() - 1, printer_data, Qt.UserRole)
            
            # If in edit mode, select the current printer
            if self.edit_mode and self.edit_device:
                self.select_current_printer()
                
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Database Warning", f"Failed to fetch printers: {str(err)}")
        finally:
            if conn:
                conn.close()
    
    def select_current_printer(self):
        """Select the current printer in the dropdown if in edit mode"""
        if not self.edit_device:
            return
            
        printer_ip = self.edit_device.get('printerIP')
        if not printer_ip:
            return
            
        # Try to find the printer by IP
        for i in range(1, self.printer_combo.count()):
            printer_data = self.printer_combo.itemData(i, Qt.UserRole)
            if printer_data and printer_data.get('ip') == printer_ip:
                self.printer_combo.setCurrentIndex(i)
                return

    def populate_form(self):
        """Populate form fields with data from the device being edited"""
        # Set basic fields
        self.ip_address.setText(self.edit_device.get('ip', ''))
        self.port.setText(str(self.edit_device.get('port', '')))
        self.username.setText(self.edit_device.get('username', ''))
        # Note: We don't populate the password field as it's encrypted in DB
        self.location.setText(self.edit_device.get('location', ''))
        
        # Set enable status
        if self.edit_device.get('enable') == 'Y':
            self.enable_radio.setChecked(True)
        else:
            self.disable_radio.setChecked(True)
        
        # We'll need to set the printer in the populate_printers method

    def open_auto_detect_dialog(self):
        """Open the auto-detect devices dialog"""
        dialog = DeviceSelectionDialog(self)
        dialog.devices_selected.connect(self.handle_detected_devices)
        dialog.exec_()
    
    def handle_detected_devices(self, selected_devices):
        """Handle the selected devices from auto-detection"""
        if not selected_devices:
            return
        
        if len(selected_devices) == 1:
            # If only one device selected, populate the form
            device = selected_devices[0]
            self.populate_form_from_device(device)
        else:
            # If multiple devices, ask user if they want to save all
            reply = QMessageBox.question(
                self, "Multiple Devices", 
                f"You selected {len(selected_devices)} devices. Do you want to save all of them automatically?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.save_multiple_devices(selected_devices)
            else:
                # Just populate form with first device
                self.populate_form_from_device(selected_devices[0])
    
    def populate_form_from_device(self, device):
        """Populate form fields from detected device"""
        self.ip_address.setText(device['ip'])
        self.port.setText(device['port'])
        self.username.setText(device['username'])
        self.password.setText(device['password'])
        
        # Set location based on device info
        location = f"{device['model']} - {device['name']}"
        if len(location) > 20:
            location = device['model']
        self.location.setText(location)
        
        QMessageBox.information(self, "Device Loaded", 
                              f"Device {device['ip']} loaded into form. You can modify details before saving.")
    
    def save_multiple_devices(self, devices):
        """Save multiple devices automatically"""
        saved_count = 0
        errors = []
        
        for device in devices:
            try:
                device_data = {
                    'ip': device['ip'],
                    'port': device['port'],
                    'username': device['username'],
                    'password': device['password'],
                    'location': f"{device['model']} - {device['name']}",
                    'enable': 'Y'
                }
                
                if self.save_device_to_database(device_data):
                    saved_count += 1
                else:
                    errors.append(f"Failed to save {device['ip']}")
                    
            except Exception as e:
                errors.append(f"Error saving {device['ip']}: {str(e)}")
        
        # Show results
        message = f"Successfully saved {saved_count} out of {len(devices)} devices."
        if errors:
            message += f"\n\nErrors:\n" + "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more errors"
        
        QMessageBox.information(self, "Batch Save Results", message)
    
    def save_device_to_database(self, device_data):
        """Save a single device to database (helper method)"""
        try:
            conn = self.db_connect()
            if not conn:
                return False
                
            cursor = conn.cursor()
            device_number = self.get_next_device_number(cursor, self.device_type)
            now = datetime.now()
            formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
            
            sql = """
            INSERT INTO configh (
                DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                comKey, Enable, CreatedDateTime, DevicePrinterIP, LicenseKey
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 
                AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                %s, %s, %s, %s
            )
            """
            
            values = (
                self.device_type, 
                device_number,
                device_data['ip'],
                device_data['port'],
                device_data['location'],
                device_data['username'],
                device_data['password'],
                formatted_now,
                device_data['enable'],
                formatted_now,
                None,
                self.license_key
            )
            
            cursor.execute(sql, values)
            conn.commit()
            
            # Emit signal for each saved device
            new_device = {
                "deviceType": self.device_type,
                "deviceNumber": device_number,
                "ip": device_data['ip'],
                "port": device_data['port'],
                "username": device_data['username'],
                "location": device_data['location'],
                "printerIP": None,
                "enable": device_data['enable'],
                "printerName": None,
                "licenseKey": self.license_key
            }
            self.device_saved.emit(new_device)
            
            return True
            
        except Exception as e:
            return False
        finally:
            if conn:
                conn.close()
    
    def populate_printers(self, printers):
        """Populate printer dropdown with available printers (legacy method)"""
        # This method is kept for backward compatibility
        # The fetch_printers_from_db method is now used to populate the dropdown
        pass
    
    def db_connect(self):
        """Connect to MySQL database"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                port=DB_PORT,
                password=DB_PASS,
                database=DB_NAME
            )
            return conn
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(err)}")
            return None
    
    def get_next_device_number(self, cursor, device_type):
        """Get the next available device number"""
        try:
            cursor.execute("SELECT MAX(DeviceNumber) FROM configh WHERE DeviceType = %s", (device_type,))
            result = cursor.fetchone()
            max_num = result[0] if result[0] is not None else 0
            return max_num + 1
        except mysql.connector.Error as err:
            return 1
    
    def get_printer_ip(self, printer_name):
        """Get printer IP address from selected printer in dropdown"""
        if not printer_name or printer_name == "Select a printer":
            return None
            
        # Get selected index
        selected_index = self.printer_combo.currentIndex()
        if selected_index <= 0:  # No printer selected
            return None
            
        # Get printer data from the dropdown
        printer_data = self.printer_combo.itemData(selected_index, Qt.UserRole)
        if printer_data and 'ip' in printer_data:
            return printer_data['ip']
            
        return None
    
    def save_device(self):
        """Save the device information to the database and emit signal"""
        device_type = self.device_type
        device_ip = self.ip_address.text().strip()
        device_port = self.port.text().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        location = self.location.text().strip()
        
        # Validation
        if not device_ip or not device_port:
            QMessageBox.warning(self, "Input Error", "Please fill in IP Address and Port")
            return
            
        if not username and not self.edit_mode:
            QMessageBox.warning(self, "Input Error", "Please fill in Username")
            return
        
        if not password and not self.edit_mode:
            QMessageBox.warning(self, "Input Error", "Please fill in Password")
            return
        
        # Get selected printer
        selected_printer = None
        printer_ip = None
        selected_index = self.printer_combo.currentIndex()
        if selected_index > 0:
            selected_printer = self.printer_combo.currentText()
            printer_data = self.printer_combo.itemData(selected_index, Qt.UserRole)
            if printer_data and 'ip' in printer_data:
                printer_ip = printer_data['ip']
                # Use the printer name from the data
                selected_printer = printer_data.get('name', selected_printer)
        
        try:
            conn = self.db_connect()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            # Set enable value
            enable_value = 'Y' if self.enable_radio.isChecked() else 'N'
            
            if self.edit_mode:
                # Get device number from edit_device
                device_number = self.edit_device.get('deviceNumber', 0)
                
                if not device_number:
                    QMessageBox.warning(self, "Edit Error", "Could not determine device number for update")
                    return
                
                # If password is empty in edit mode, don't update it
                if password:
                    # First get the original CreatedDateTime for proper encryption
                    get_created_datetime_sql = """
                    SELECT CreatedDateTime FROM configh 
                    WHERE DeviceType = %s AND DeviceNumber = %s
                    """
                    cursor.execute(get_created_datetime_sql, (device_type, device_number))
                    result = cursor.fetchone()
                    
                    if not result or not result[0]:
                        # Fallback to current time if original time not found
                        creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        # Use original creation time for encryption
                        creation_time = result[0].strftime('%Y-%m-%d %H:%M:%S') if hasattr(result[0], 'strftime') else str(result[0])
                    
                    # Update with password
                    sql = """
                    UPDATE configh SET
                        IP = %s,
                        Port = %s,
                        DeviceLocation = %s,
                        ComUser = %s,
                        comKey = AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)),
                        Enable = %s,
                        DevicePrinterIP = %s,
                        LicenseKey = %s
                    WHERE DeviceType = %s AND DeviceNumber = %s
                    """
                    
                    values = (
                        device_ip,
                        device_port,
                        location,
                        username,
                        password,
                        creation_time,  # Use original creation time for encryption
                        enable_value,
                        printer_ip,
                        self.license_key,
                        device_type,
                        device_number
                    )
                else:
                    # Update without password
                    sql = """
                    UPDATE configh SET
                        IP = %s,
                        Port = %s,
                        DeviceLocation = %s, 
                        ComUser = %s,
                        Enable = %s,
                        DevicePrinterIP = %s,
                        LicenseKey = %s
                    WHERE DeviceType = %s AND DeviceNumber = %s
                    """
                    
                    values = (
                        device_ip,
                        device_port,
                        location,
                        username,
                        enable_value,
                        printer_ip,
                        self.license_key,
                        device_type,
                        device_number
                    )
                
                cursor.execute(sql, values)
                conn.commit()
                
                message = f"{device_type} updated successfully!"
                QMessageBox.information(self, "Success", message)
            else:
                # Create new device
                device_number = self.get_next_device_number(cursor, device_type)
                now = datetime.now()
                formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
                
                # Prepare SQL statement for insert
                sql = """
                INSERT INTO configh (
                    DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                    comKey, Enable, CreatedDateTime, DevicePrinterIP, LicenseKey
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 
                    AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                    %s, %s, %s, %s
                )
                """
                
                # Execute SQL with values
                values = (
                    device_type, 
                    device_number,
                    device_ip,
                    device_port,
                    location,
                    username,
                    password,
                    formatted_now,  # Pass timestamp for encryption
                    enable_value,
                    formatted_now,  # CreatedDateTime field
                    printer_ip,     # This will be None if no printer selected
                    self.license_key # Add license key
                )
                
                cursor.execute(sql, values)
                conn.commit()
                
                message = f"{device_type} saved successfully to database!"
                QMessageBox.information(self, "Success", message)
            
            # Prepare device info for signal
            new_device = {
                "deviceType": device_type,
                "deviceNumber": device_number,
                "ip": device_ip,
                "port": device_port,
                "username": username,
                "location": location,
                "printerIP": printer_ip,
                "enable": enable_value,
                "printerName": selected_printer,
                "licenseKey": self.license_key,
                # For backward compatibility, set name for Printer type
                "name": f"{device_type} {device_number}" if device_type == "Printer" else None
            }
            
            # Also save to JSON file for compatibility
            self.save_to_json(new_device)
            
            # Emit the device_saved signal with the new device data
            self.device_saved.emit(new_device)
            
            # Clear form fields if not in edit mode
            if not self.edit_mode:
                self.ip_address.clear()
                self.port.clear()
                self.username.clear()
                self.password.clear()
                self.location.clear()
                self.enable_radio.setChecked(True)
                self.printer_combo.setCurrentIndex(0)
            
        except mysql.connector.Error as err:
            action = "updating" if self.edit_mode else "saving"
            QMessageBox.critical(self, "Database Error", f"Failed to {action} {device_type.lower()}: {str(err)}")
        finally:
            if conn:
                conn.close()
                
    def save_to_json(self, new_device):
        """Save the device information to JSON file for compatibility"""
        try:
            # Load existing configuration
            config_path = 'appSettings.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"devices": [], "printers": []}
            
            # Add new device to appropriate configuration section
            device_type = new_device["deviceType"]
            
            json_device = {
                "ip": new_device["ip"],
                "port": new_device["port"],
                "username": new_device["username"],
                "location": new_device["location"],
                "printerName": new_device["printerName"],
                "printerIP": new_device["printerIP"],
                "showLiveE": new_device["enable"] == "Y",
                "showLiveD": new_device["enable"] != "Y",
                "deviceType": device_type,
                "deviceNumber": new_device["deviceNumber"],
                "licenseKey": new_device.get("licenseKey")
            }
            
            # Handle edit mode - find and update existing device
            if self.edit_mode:
                device_updated = False
                
                # If it's a printer, update in printers list
                if device_type == "Printer":
                    if "printers" in config:
                        for i, printer in enumerate(config["printers"]):
                            if (printer.get('ip') == self.edit_device.get('ip') or
                                printer.get('deviceNumber') == self.edit_device.get('deviceNumber')):
                                json_device["name"] = new_device["name"]
                                config["printers"][i] = json_device
                                device_updated = True
                                break
                    
                # Otherwise update in devices list
                else:
                    if "devices" in config:
                        for i, device in enumerate(config["devices"]):
                            if (device.get('ip') == self.edit_device.get('ip') or
                                device.get('deviceNumber') == self.edit_device.get('deviceNumber')):
                                config["devices"][i] = json_device
                                device_updated = True
                                break
                
                # If device wasn't found to update, add as new
                if not device_updated:
                    if device_type == "Printer":
                        json_device["name"] = new_device["name"]
                        if "printers" not in config:
                            config["printers"] = []
                        config["printers"].append(json_device)
                    else:
                        if "devices" not in config:
                            config["devices"] = []
                        config["devices"].append(json_device)
            else:
                # If it's a printer, add name field and add to printers list
                if device_type == "Printer":
                    json_device["name"] = new_device["name"]
                    if "printers" not in config:
                        config["printers"] = []
                    config["printers"].append(json_device)
                else:
                    # Add to devices list
                    if "devices" not in config:
                        config["devices"] = []
                    config["devices"].append(json_device)
            
            # Save updated configuration
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save {device_type.lower()} to JSON: {str(e)}")
    
    def back_clicked(self):
        """Handle back button click"""
        reply = QMessageBox.question(self, "Confirmation", 
                                    "Do you want to save the device?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.save_device()
        # Parent class will handle the navigation back
        
    def update_hikvision_passwords(self, password):
        """Update passwords for all Hikvision devices using proper encryption"""
        try:
            conn = self.db_connect()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Update Hikvision device passwords
            sql = """
            UPDATE configh 
            SET comKey = AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) 
            WHERE LCASE(DeviceType) = 'hikvision'
            """
            
            cursor.execute(sql, (password,))
            rows_affected = cursor.rowcount
            conn.commit()
            
            QMessageBox.information(self, "Password Update", 
                f"Updated passwords for {rows_affected} Hikvision devices.")
            
            return True
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Failed to update Hikvision passwords: {str(err)}")
            return False
        finally:
            if conn:
                conn.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EzeeCanteenDeviceForm()
    window.show()
    sys.exit(app.exec_())