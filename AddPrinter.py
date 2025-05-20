import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QComboBox, QRadioButton, QTextEdit,
                            QPushButton, QMessageBox, QFrame, QButtonGroup)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

class PrinterSetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.resize(650, 700)
        
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
        title_label = QLabel("Add New Printer")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        frame_layout.addWidget(title_frame)
        
        # Form fields
        self.create_form_fields(frame_layout)
        
        # Button section
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignRight)
        
        back_button = QPushButton("Back")
        back_button.setObjectName("backButton")
        
        save_button = QPushButton("Save Printer")
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self.save_printer)
        
        button_layout.addWidget(back_button)
        button_layout.addWidget(save_button)
        frame_layout.addLayout(button_layout)
        
        # Footer
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)
    
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
    
    def save_printer(self):
        if not self.validate_form():
            return
            
        # Get form data
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
        
        new_printer = {
            "name": self.printer_name.text().strip(),
            "type": self.printer_type.currentText().lower(),
            "ip": self.printer_ip.text().strip(),
            "port": self.printer_port.text().strip(),
            "fontSize": self.font_size.currentData(),
            "header": header,
            "footer": footer
        }
        
        # Load current settings
        settings = self.load_settings()
        
        # Add new printer
        if "printers" not in settings:
            settings["printers"] = []
        settings["printers"].append(new_printer)
        
        # Save settings
        if self.save_settings(settings):
            QMessageBox.information(self, "Success", "Printer added successfully")
        else:
            QMessageBox.critical(self, "Error", "Failed to save printer settings")
    
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
    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PrinterSetupWindow()
    window.show()
    sys.exit(app.exec_())