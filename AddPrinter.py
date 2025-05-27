import sys
import json
import os
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QComboBox, QRadioButton, QTextEdit,
                            QPushButton, QMessageBox, QFrame, QButtonGroup)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QFont

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

class PrinterSetupWindow(QMainWindow):
    # Signal for when printer is saved
    printer_saved = pyqtSignal(dict)
    
    def __init__(self, edit_printer=None):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.resize(650, 700)
        
        # Store printer data if editing
        self.edit_mode = edit_printer is not None
        self.edit_printer = edit_printer or {}
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2d3748;
                color: white;
                font-family: Arial, sans-serif;
            }
            QFrame {
                background-color: #1a202c;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                padding: 5px 0;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #2d3748;
                color: white;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #4299e1;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton#backButton {
                background-color: #3182ce;
                color: white;
            }
            QPushButton#backButton:hover {
                background-color: #2b6cb0;
            }
            QPushButton#saveButton {
                background-color: #38a169;
                color: white;
            }
            QPushButton#saveButton:hover {
                background-color: #2f855a;
            }
            QRadioButton {
                color: white;
                padding: 2px;
            }
            QFrame#titleFrame {
                border-bottom: 1px solid #4a5568;
                padding-bottom: 10px;
                margin-bottom: 10px;
            }
            QLabel#footerLabel {
                color: #a0aec0;
                font-size: 16px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create main frame
        main_frame = QFrame()
        main_frame.setFrameShape(QFrame.StyledPanel)
        main_layout.addWidget(main_frame)
        frame_layout = QVBoxLayout(main_frame)
        
        # Title section
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_layout = QVBoxLayout(title_frame)
        title_text = "Edit Printer" if self.edit_mode else "Add New Printer"
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        frame_layout.addWidget(title_frame)
        
        # Form fields
        self.create_form_fields(frame_layout)
        
        # Button section
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignRight)
        
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("backButton")
        
        save_text = "Update Printer" if self.edit_mode else "Save Printer"
        save_button = QPushButton(save_text)
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self.save_printer)
        
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(save_button)
        frame_layout.addLayout(button_layout)
        
        # Footer
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)
        
        # Populate form if in edit mode
        if self.edit_mode:
            self.populate_form()
    
    def populate_form(self):
        """Populate form fields with data from the printer being edited"""
        if not self.edit_printer:
            return
            
        # Set basic fields
        self.printer_name.setText(self.edit_printer.get('name', ''))
        
        # Set printer type
        printer_type = self.edit_printer.get('type', '').capitalize()
        index = self.printer_type.findText(printer_type)
        if index >= 0:
            self.printer_type.setCurrentIndex(index)
            
        self.printer_ip.setText(self.edit_printer.get('ip', ''))
        self.printer_port.setText(str(self.edit_printer.get('port', '9100')))
        
        # Set font size
        font_size = self.edit_printer.get('fontSize', '')
        for i in range(self.font_size.count()):
            if self.font_size.itemData(i) == font_size:
                self.font_size.setCurrentIndex(i)
                break
        
        # Set header/footer if available
        header = self.edit_printer.get('header', {})
        if header.get('enable', False):
            self.enable_header.setChecked(True)
        else:
            self.disable_header.setChecked(True)
        self.token_header.setText(header.get('text', ''))
        
        footer = self.edit_printer.get('footer', {})
        if footer.get('enable', False):
            self.enable_footer.setChecked(True)
        else:
            self.disable_footer.setChecked(True)
        self.token_footer.setText(footer.get('text', ''))
    
    def create_form_fields(self, layout):
        # Printer Name
        layout.addWidget(QLabel("Printer Name"))
        self.printer_name = QLineEdit()
        self.printer_name.setPlaceholderText("CITIZEN CT-D150")
        layout.addWidget(self.printer_name)
        
        # Printer Type
        layout.addWidget(QLabel("Printer Type"))
        self.printer_type = QComboBox()
        self.printer_type.addItems(["Thermal", "Inkjet", "Laser"])
        layout.addWidget(self.printer_type)
             
        # Printer IP
        layout.addWidget(QLabel("Printer IP"))
        self.printer_ip = QLineEdit()
        self.printer_ip.setPlaceholderText("192.168.100.100")
        layout.addWidget(self.printer_ip)
        
        # Printer Port
        layout.addWidget(QLabel("Printer Port"))
        self.printer_port = QLineEdit()
        self.printer_port.setPlaceholderText("9100")
        layout.addWidget(self.printer_port)
        
        # Font Size
        layout.addWidget(QLabel("Font Size"))
        self.font_size = QComboBox()
        self.font_size.addItem("Select font size", "")
        self.font_size.addItem("Large", "A")
        self.font_size.addItem("Medium (Recommended)", "B")
        self.font_size.addItem("Small", "C")
        layout.addWidget(self.font_size)
        
        # Token Header
        layout.addWidget(QLabel("Token Header"))
        header_radio_layout = QHBoxLayout()
        self.header_group = QButtonGroup()
        
        self.enable_header = QRadioButton("Enable")
        self.disable_header = QRadioButton("Disable")
        self.header_group.addButton(self.enable_header)
        self.header_group.addButton(self.disable_header)
        
        header_radio_layout.addWidget(self.enable_header)
        header_radio_layout.addWidget(self.disable_header)
        header_radio_layout.addStretch()
        layout.addLayout(header_radio_layout)
        
        self.token_header = QTextEdit()
        self.token_header.setPlaceholderText("Enter header text here...")
        self.token_header.setMaximumHeight(80)
        layout.addWidget(self.token_header)
        
        # Token Footer
        layout.addWidget(QLabel("Token Footer"))
        footer_radio_layout = QHBoxLayout()
        self.footer_group = QButtonGroup()
        
        self.enable_footer = QRadioButton("Enable")
        self.disable_footer = QRadioButton("Disable")
        self.footer_group.addButton(self.enable_footer)
        self.footer_group.addButton(self.disable_footer)
        
        footer_radio_layout.addWidget(self.enable_footer)
        footer_radio_layout.addWidget(self.disable_footer)
        footer_radio_layout.addStretch()
        layout.addLayout(footer_radio_layout)
        
        self.token_footer = QTextEdit()
        self.token_footer.setPlaceholderText("Enter footer text here...")
        self.token_footer.setMaximumHeight(80)
        layout.addWidget(self.token_footer)
    
    def validate_form(self):
        if not self.printer_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a printer name")
            return False
        
        if not self.printer_ip.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a printer IP address")
            return False
        
        if not self.printer_port.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a printer port")
            return False
        
        if self.font_size.currentData() == "":
            QMessageBox.warning(self, "Validation Error", "Please select a font size")
            return False
            
        return True
    
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
    
    def save_printer(self):
        if not self.validate_form():
            return
            
        # Get form data
        printer_name = self.printer_name.text().strip()
        printer_ip = self.printer_ip.text().strip()
        printer_port = self.printer_port.text().strip()
        printer_type = self.printer_type.currentText().lower()
        font_size = self.font_size.currentData()
        
        header = {
            "enable": self.enable_header.isChecked(),
            "disable": self.disable_header.isChecked(),
            "text": self.token_header.toPlainText()
        }
        
        footer = {
            "enable": self.enable_footer.isChecked(),
            "disable": self.disable_footer.isChecked(),
            "text": self.token_footer.toPlainText()
        }
        
        try:
            # Connect to database
            conn = self.db_connect()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Convert header/footer to location text
            location = f"FontSize:{font_size}"
            if header["enable"]:
                location += f"|Header:{header['text']}"
            if footer["enable"]:
                location += f"|Footer:{footer['text']}"
            
            # Set enable value - Enable by default
            enable_value = 'Y'
            
            if self.edit_mode:
                # Update existing printer
                device_number = self.edit_printer.get('deviceNumber', 1)
                
                # Prepare SQL statement for update
                sql = """
                UPDATE configh SET
                    IP = %s,
                    Port = %s,
                    DeviceLocation = %s,
                    Enable = %s
                WHERE DeviceType = %s AND DeviceNumber = %s
                """
                
                # Execute SQL with values
                values = (
                    printer_ip,
                    printer_port,
                    location,
                    enable_value,
                    printer_name,  # Use name as DeviceType
                    device_number
                )
                
                cursor.execute(sql, values)
                conn.commit()
                
                QMessageBox.information(self, "Success", "Printer updated successfully!")
            else:
                # Get next device number for new printer
                device_number = self.get_next_device_number(cursor, printer_name)
                
                # Current timestamp
                now = datetime.now()
                formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
                
                # Default username/password for printers
                username = "admin"
                password = "admin"
                
                # Prepare SQL statement for insert
                sql = """
                INSERT INTO configh (
                    DeviceType, DeviceNumber, IP, Port, ComUser, 
                    comKey, Enable, CreatedDateTime, DevicePrinterIP
                ) VALUES (
                     %s, %s, %s, %s, %s, 
                    AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                    %s, %s, %s
                )
                """
                
                # Execute SQL with values
                values = (
                    printer_name,  # DeviceType
                    device_number,
                    printer_ip,    # IP
                    printer_port,
                    username,
                    password,
                    formatted_now,  # Pass timestamp for encryption
                    enable_value,
                    formatted_now,  # CreatedDateTime field
                    ""  # DevicePrinterIP - empty for printers
                )
                
                cursor.execute(sql, values)
                conn.commit()
                
                QMessageBox.information(self, "Success", "Printer saved successfully to database!")
            
            # Prepare printer data for JSON and signal
            saved_printer = {
                "name": printer_name,
                "type": printer_type,
                "ip": printer_ip,
                "port": printer_port,
                "deviceNumber": device_number,
                "enable": enable_value, 
                "fontSize": font_size,
                "header": header,
                "footer": footer,
                "location": location
            }
            
            # Also save to JSON for compatibility
            self.save_to_json(saved_printer)
            
            # Emit signal with saved printer data
            self.printer_saved.emit(saved_printer)
            
            # Clear form fields if not editing
            if not self.edit_mode:
                self.printer_name.clear()
                self.printer_ip.clear()
                self.printer_port.clear()
                self.font_size.setCurrentIndex(0)
                self.token_header.clear()
                self.token_footer.clear()
            
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Failed to save printer: {str(err)}")
        finally:
            if conn:
                conn.close()
    
    def load_settings(self):
        try:
            settings_file = os.path.join(os.path.expanduser("~"), ".ezeecanteen", "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
            return {"printers": [], "devices": []}
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {"printers": [], "devices": []}
    
    def save_settings(self, settings):
        try:
            # Ensure directory exists
            settings_dir = os.path.join(os.path.expanduser("~"), ".ezeecanteen")
            os.makedirs(settings_dir, exist_ok=True)
            
            # Save settings
            settings_file = os.path.join(settings_dir, "settings.json")
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
            
    def save_to_json(self, printer_data):
        """Save the printer information to JSON file for compatibility"""
        # Load current settings
        settings = self.load_settings()
        
        if self.edit_mode:
            # Update existing printer in JSON
            if "printers" in settings:
                for i, printer in enumerate(settings["printers"]):
                    if (printer.get('name') == self.edit_printer.get('name') and 
                        printer.get('ip') == self.edit_printer.get('ip')):
                        settings["printers"][i] = printer_data
                        break
        else:
            # Add new printer
            if "printers" not in settings:
                settings["printers"] = []
            settings["printers"].append(printer_data)
        
        # Save settings
        self.save_settings(settings)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PrinterSetupWindow()
    window.show()
    sys.exit(app.exec_())