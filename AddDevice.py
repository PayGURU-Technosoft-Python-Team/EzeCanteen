import sys
import json
import os
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QRadioButton, QButtonGroup, QMessageBox,
                             QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"


class EzeeCanteenDeviceForm(QMainWindow):
    # Signal to emit when a device is saved
    device_saved = pyqtSignal(dict)
    
    def __init__(self, device_type="Device"):
        super().__init__()
        self.device_type = device_type  # Store the device type based on which button was clicked
        self.initUI()
        
    def initUI(self):
        # Set window properties
        self.setWindowTitle('EzeeCanteen')
        self.setGeometry(100, 100, 600, 500)
        self.setStyleSheet("background-color: #1e293b; color: white;")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create form container with dark background
        form_container = QFrame()
        form_container.setFrameShape(QFrame.StyledPanel)
        form_container.setStyleSheet("background-color: #0f172a; border-radius: 8px; padding: 15px;")
        form_layout = QVBoxLayout(form_container)
        
        # Title
        title_label = QLabel(f"Add {self.device_type}")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #4b5563;")
        form_layout.addWidget(title_label)
        
        # IP Address field
        form_layout.addWidget(QLabel("IP Address"))
        self.ip_address = QLineEdit()
        self.ip_address.setPlaceholderText("192.168.100.100")
        self.ip_address.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.ip_address)
        
        # Port field
        form_layout.addWidget(QLabel("Port"))
        self.port = QLineEdit()
        self.port.setPlaceholderText("80")
        self.port.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.port)
        
        # Username field
        form_layout.addWidget(QLabel("Username"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("admin")
        self.username.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.username)
        
        # Password field
        form_layout.addWidget(QLabel("Password"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("password")
        self.password.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.password)
        
        # Select Printer field
        form_layout.addWidget(QLabel("Select Printer"))
        self.printer_combo = QComboBox()
        self.printer_combo.addItem("Select a printer")
        self.printer_combo.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.printer_combo)
        
        # Printer IP field
        form_layout.addWidget(QLabel("Printer IP"))
        self.printer_ip = QLineEdit()
        self.printer_ip.setPlaceholderText("192.168.100.101")
        self.printer_ip.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.printer_ip)
        
        # Show on Live field
        live_label = QLabel("Enable Device")
        form_layout.addWidget(live_label)
        
        live_layout = QHBoxLayout()
        self.enable_radio = QRadioButton("Enable")
        self.disable_radio = QRadioButton("Disable")
        self.enable_radio.setChecked(True)
        
        live_group = QButtonGroup(self)
        live_group.addButton(self.enable_radio)
        live_group.addButton(self.disable_radio)
        
        live_layout.addWidget(self.enable_radio)
        live_layout.addWidget(self.disable_radio)
        live_layout.addStretch()
        form_layout.addLayout(live_layout)
        
        # Location field
        form_layout.addWidget(QLabel("Location"))
        self.location = QLineEdit()
        self.location.setPlaceholderText("Room 101 Front Desk")
        self.location.setStyleSheet("background-color: #1e293b; padding: 8px; border-radius: 4px; margin-bottom: 10px;")
        form_layout.addWidget(self.location)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.back_button = QPushButton("Back")
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.back_button.clicked.connect(self.back_clicked)
        
        self.save_button = QPushButton("Save Device")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.save_button.clicked.connect(self.save_device)
        
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.save_button)
        form_layout.addLayout(button_layout)
        
        # Add form container to main layout
        main_layout.addWidget(form_container)
        
        # Footer
        footer = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #9ca3af; margin-top: 20px;")
        main_layout.addWidget(footer)
    
    def populate_printers(self, printers):
        """Populate printer dropdown with available printers"""
        self.printer_combo.clear()
        self.printer_combo.addItem("Select a printer")
        
        for printer in printers:
            printer_name = printer.get('name', 'Unknown')
            self.printer_combo.addItem(printer_name)
    
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
            return 1  # Default to 1 if error
    
    def save_device(self):
        """Save the device information to the database and emit signal"""
        device_type = self.device_type  # Use the stored device type instead of reading from a field
        device_ip = self.ip_address.text().strip()
        device_port = self.port.text().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        location = self.location.text().strip()
        printer_ip = self.printer_ip.text().strip()
        
        # Validation
        if not device_ip or not device_port:
            QMessageBox.warning(self, "Input Error", "Please fill in IP Address and Port")
            return
            
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in Username and Password")
            return
        
        # Get selected printer
        selected_printer = None
        if self.printer_combo.currentIndex() > 0:
            selected_printer = self.printer_combo.currentText()
        
        try:
            # Connect to database
            conn = self.db_connect()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            # Get next device number
            device_number = self.get_next_device_number(cursor, device_type)
            
            # Current timestamp for encryption
            now = datetime.now()
            formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare SQL statement
            sql = """
            INSERT INTO configh (
                DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                comKey, Enable, CreatedDateTime, DevicePrinterIP
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 
                AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                %s, %s, %s
            )
            """
            
            # Set enable value
            enable_value = 'Y' if self.enable_radio.isChecked() else 'N'
            
            # Execute SQL with values
            values = (
                device_type, 
                device_number,
                device_ip,
                device_port,
                location,
                username,
                password,
                formatted_now,  # Pass the same timestamp for both encryption and storage
                enable_value,
                formatted_now,  # CreatedDateTime field
                printer_ip
            )
            
            cursor.execute(sql, values)
            conn.commit()
            
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
                # For backward compatibility, set name for Printer type
                "name": f"{device_type} {device_number}" if device_type == "Printer" else None
            }
            
            # Also save to JSON file for compatibility
            self.save_to_json(new_device)
            
            # Emit the device_saved signal with the new device data
            self.device_saved.emit(new_device)
            QMessageBox.information(self, "Success", f"{device_type} saved successfully to database!")
            
            # Clear form fields
            self.ip_address.clear()
            self.port.clear()
            self.username.clear()
            self.password.clear()
            self.location.clear()
            self.printer_ip.clear()
            self.enable_radio.setChecked(True)
            
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Failed to save {device_type.lower()}: {str(err)}")
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
                "showLiveE": new_device["enable"] == "Y",
                "showLiveD": new_device["enable"] != "Y",
                "deviceType": device_type
            }
            
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EzeeCanteenDeviceForm()
    window.show()
    sys.exit(app.exec_())