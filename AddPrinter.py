import sys
import json
import os
import mysql.connector
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QComboBox, QRadioButton, QTextEdit,
                            QPushButton, QMessageBox, QFrame, QButtonGroup, QDialog,
                            QListWidget, QListWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QThread
from PyQt5.QtGui import QFont

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

class PrinterScannerThread(QThread):
    """Thread for scanning network for printers"""
    printer_found = pyqtSignal(dict)
    scan_progress = pyqtSignal(str)
    scan_complete = pyqtSignal(list)
    
    def __init__(self, subnet=None):
        super().__init__()
        self.subnet = subnet
        self.found_printers = []
        
    def get_subnet(self):
        """Get current subnet automatically"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return '.'.join(ip.split('.')[:-1])
        except:
            return "192.168.1"  # Default fallback subnet
    
    def check_printer(self, ip):
        """Check if IP is a printer by trying printer-specific ports"""
        try:
            # Check printer-specific ports
            printer_ports = [9100, 515, 631]  # Raw, LPD, IPP
            for port in printer_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                if sock.connect_ex((ip, port)) == 0:
                    sock.close()
                    # Create a more descriptive printer name based on port type
                    port_types = {9100: "RAW", 515: "LPD", 631: "IPP"}
                    port_type = port_types.get(port, "Unknown")
                    printer_info = {
                        'ip': ip,
                        'port': str(port),
                        'name': f"Thermal Printer ({ip} - {port_type})",
                        'model': "Thermal"  # Default type
                    }
                    self.printer_found.emit(printer_info)
                    return printer_info
                sock.close()
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
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.check_printer, ip) for ip in ips]
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    self.found_printers.append(result)
                
                # Update progress
                progress = f"Scanned {i+1}/254 addresses... Found {len(self.found_printers)} printers"
                self.scan_progress.emit(progress)
        
        self.scan_complete.emit(self.found_printers)


class PrinterSelectionDialog(QDialog):
    """Dialog for selecting detected printers"""
    printers_selected = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detected_printers = []
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Auto-Detect Printers')
        self.setGeometry(200, 200, 850, 650)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #1e293b; color: white;")
           
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title_label = QLabel("Network Printer Detection")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("""
            margin-bottom: 12px; 
            padding: 12px; 
            border-bottom: 2px solid #4b5563;
            color: #f8fafc;
        """)
        layout.addWidget(title_label)

        # Subnet input section
        subnet_group = QGroupBox("Network Settings")
        subnet_group.setStyleSheet("""
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
        subnet_layout = QVBoxLayout(subnet_group)
        subnet_layout.setSpacing(8)
        subnet_layout.setContentsMargins(15, 18, 15, 15)

        # Helper function for consistent field styling
        def create_subnet_field(label_text, widget, placeholder=""):
            # Label
            label = QLabel(label_text)
            label.setStyleSheet("""
                font-size: 13px; 
                font-weight: 500;
                color: #e2e8f0;
                margin-bottom: 2px;
                margin-top: 4px;
            """)
            subnet_layout.addWidget(label)
            
            # Widget styling
            widget.setMinimumHeight(38)
            if placeholder:
                widget.setPlaceholderText(placeholder)
            
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
            subnet_layout.addWidget(widget)

        # Subnet input
        self.subnet_input = QLineEdit()
        create_subnet_field("Subnet (optional - auto-detected if empty):", self.subnet_input, "192.168.1 (leave empty for auto-detection)")

        # Add small spacing before button
        subnet_layout.addSpacing(8)

        # Scan button
        self.scan_button = QPushButton("Start Network Scan")
        self.scan_button.setMinimumHeight(42)
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
        subnet_layout.addWidget(self.scan_button)

        layout.addWidget(subnet_group)
        
        # Progress section
        self.progress_label = QLabel("Ready to scan...")
        self.progress_label.setStyleSheet("color: #9ca3af; margin: 15px 0; font-size: 13px;")
        layout.addWidget(self.progress_label)
        
        # Printer list section
        printer_group = QGroupBox("Detected Printers")
        printer_group.setStyleSheet("""
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
        printer_layout = QVBoxLayout(printer_group)
        printer_layout.setContentsMargins(20, 25, 20, 20)
        
        self.printer_list = QListWidget()
        self.printer_list.setStyleSheet("""
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
        self.printer_list.setSelectionMode(QListWidget.MultiSelection)
        printer_layout.addWidget(self.printer_list)
        
        layout.addWidget(printer_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        self.add_selected_button = QPushButton("Add Selected Printers")
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
            QPushButton:disabled {
                background-color: #6b7280;
                color: #9ca3af;
            }
        """)
        self.add_selected_button.clicked.connect(self.add_selected_printers)
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
        
        # Connect the printer list selection changed signal
        self.printer_list.itemSelectionChanged.connect(self.update_button_states)
        
    def update_button_states(self):
        """Update button states based on selection"""
        has_selection = len(self.printer_list.selectedItems()) > 0
        self.add_selected_button.setEnabled(has_selection)
    
    def start_scan(self):
        """Start the network scanning process"""
        subnet = self.subnet_input.text().strip() or None
        
        # Clear previous results
        self.printer_list.clear()
        self.detected_printers = []
        
        # Disable scan button and enable progress updates
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")
        self.add_selected_button.setEnabled(False)
        
        # Start scanning thread
        self.scanner_thread = PrinterScannerThread(subnet)
        self.scanner_thread.printer_found.connect(self.on_printer_found)
        self.scanner_thread.scan_progress.connect(self.on_scan_progress)
        self.scanner_thread.scan_complete.connect(self.on_scan_complete)
        self.scanner_thread.start()
    
    def on_printer_found(self, printer_info):
        """Handle when a printer is found"""
        self.detected_printers.append(printer_info)
        
        # Add to list widget
        item_text = f"🖨️ {printer_info['ip']} - Port {printer_info['port']}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, printer_info)
        self.printer_list.addItem(item)
        
        # Update button states in case this is the first item
        self.update_button_states()
    
    def on_scan_progress(self, progress_text):
        """Update progress label"""
        self.progress_label.setText(progress_text)
    
    def on_scan_complete(self, found_printers):
        """Handle scan completion"""
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Start Network Scan")
        
        if found_printers:
            self.progress_label.setText(f"Scan complete! Found {len(found_printers)} printers. Please select printers to add.")
            
            # If only one printer was found, auto-select it
            if len(found_printers) == 1:
                self.printer_list.item(0).setSelected(True)
        else:
            self.progress_label.setText("Scan complete. No printers found.")
    
    def add_selected_printers(self):
        """Add selected printers and close dialog"""
        selected_printers = []
        for item in self.printer_list.selectedItems():
            printer_info = item.data(Qt.UserRole)
            if printer_info:
                selected_printers.append(printer_info)
        
        if not selected_printers:
            QMessageBox.warning(self, "Selection Error", "Please select at least one printer")
            return
        
        # Debug info
        print(f"Selected {len(selected_printers)} printers:")
        for i, printer in enumerate(selected_printers):
            print(f"  {i+1}. {printer['ip']} - Port {printer['port']}")
        
        # Emit signal with selected printers
        self.printers_selected.emit(selected_printers)
        
        # Close the dialog
        self.accept()

import logging
import asyncio
from licenseManager import LicenseManager  

class PrinterSetupWindow(QMainWindow):
    # Signal for when printer is saved
    printer_saved = pyqtSignal(dict)
    def __init__(self, edit_printer=None):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.resize(650, 700)
        
        license_manager = LicenseManager()
                
        # We need to run the async method in a synchronous context
        def get_license_data():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                license_data = loop.run_until_complete(license_manager.get_license_db())
                return license_data
            finally:
                loop.close()
        
        # Get license data and extract the key
        license_data = get_license_data()
        if license_data and 'LicenseKey' in license_data:
            self.license_key = license_data['LicenseKey']
            print("*****************")
            print(self.license_key)
            print("*****************")
        

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
        
        # Auto-detect button (only when not in edit mode)
        if not self.edit_mode:
            auto_detect_layout = QHBoxLayout()
            self.auto_detect_button = QPushButton("🔍 Auto-Detect Printers")
            self.auto_detect_button.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: white;
                    padding: 8px 16px;
                    font-weight: bold;
                    border-radius: 6px;
                    margin-bottom: 10px;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
            """)
            self.auto_detect_button.clicked.connect(self.open_auto_detect_dialog)
            auto_detect_layout.addWidget(self.auto_detect_button)
            auto_detect_layout.addStretch()
            frame_layout.addLayout(auto_detect_layout)
        
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
    
    def open_auto_detect_dialog(self):
        """Open the auto-detect printers dialog"""
        try:
            dialog = PrinterSelectionDialog(self)
            
            # Explicitly connect the signal
            dialog.printers_selected.connect(self._on_printers_selected)
            
            # Execute the dialog (modal)
            result = dialog.exec_()
            print(f"Dialog closed with result: {result}")
            
        except Exception as e:
            print(f"Error in auto-detect dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            
    def _on_printers_selected(self, selected_printers):
        """Explicitly handle the selected printers signal"""
        print(f"Signal received with {len(selected_printers)} printers")
        
        # Process the selected printers
        self.handle_detected_printers(selected_printers)
    
    def handle_detected_printers(self, selected_printers):
        """Handle the selected printers from auto-detection"""
        print(f"Processing {len(selected_printers)} selected printers")
        
        if not selected_printers:
            print("No printers to process")
            return
        
        if len(selected_printers) == 1:
            # If only one printer selected, populate the form
            printer = selected_printers[0]
            print(f"Populating form with single printer: {printer['ip']}")
            self.populate_form_from_printer(printer)
        else:
            # If multiple printers, ask user if they want to save all
            message = (f"You selected {len(selected_printers)} printers.\n\n"
                      f"• Click 'Save All' to automatically save all printers with default settings\n"
                      f"• Click 'Edit First' to fill the form with the first printer to edit before saving\n"
                      f"• Click 'Cancel' to close this dialog")
            
            reply = QMessageBox.question(
                self, 
                "Multiple Printers Selected", 
                message,
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, 
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Save all printers
                print(f"Saving all {len(selected_printers)} printers")
                self.save_multiple_printers(selected_printers)
            elif reply == QMessageBox.No:
                # Just populate form with first printer
                print("Populating form with first printer")
                self.populate_form_from_printer(selected_printers[0])
            else:
                print("Operation canceled by user")
                # If Cancel, do nothing
            
    def populate_form_from_printer(self, printer):
        """Populate form fields from detected printer"""
        # Set printer name with a meaningful default
        self.printer_name.setText(printer.get('name', f"Thermal Printer ({printer['ip']})"))
        
        # Set printer type
        printer_type = printer.get('model', 'Thermal').capitalize()
        index = self.printer_type.findText(printer_type)
        if index >= 0:
            self.printer_type.setCurrentIndex(index)
            
        # Set IP and port
        self.printer_ip.setText(printer.get('ip', ''))
        self.printer_port.setText(printer.get('port', '9100'))
        
        # Select medium font size as default (commonly used)
        for i in range(self.font_size.count()):
            if self.font_size.itemData(i) == 'B':  # Medium font
                self.font_size.setCurrentIndex(i)
                break
        
        # Default to disabled header and footer (safer default)
        if hasattr(self, 'disable_header') and hasattr(self, 'disable_footer'):
            self.disable_header.setChecked(True)
            self.disable_footer.setChecked(True)
            
            # Clear any existing text
            if hasattr(self, 'token_header') and hasattr(self, 'token_footer'):
                self.token_header.clear()
                self.token_footer.clear()
        
        QMessageBox.information(self, "Printer Loaded", 
                              f"Printer {printer['ip']} loaded into form.\n\nYou can modify details before saving.")
    
    def save_multiple_printers(self, printers):
        """Save multiple printers automatically"""
        progress_dialog = QMessageBox(self)
        progress_dialog.setWindowTitle("Saving Printers")
        progress_dialog.setText("Starting batch save operation...")
        progress_dialog.setStandardButtons(QMessageBox.NoButton)
        progress_dialog.show()
        
        saved_count = 0
        errors = []
        
        for i, printer in enumerate(printers):
            try:
                # Update progress
                progress_dialog.setText(f"Saving printer {i+1} of {len(printers)}...\n{printer['ip']}")
                QApplication.processEvents()  # Allow UI to update
                
                # Create default printer data
                printer_data = {
                    'name': printer.get('name', f"Thermal Printer ({printer['ip']})"),
                    'type': printer.get('model', 'thermal').lower(),
                    'ip': printer['ip'],
                    'port': printer.get('port', '9100'),
                    'fontSize': 'B',  # Medium font
                    'header': {'enable': False, 'text': ''},
                    'footer': {'enable': False, 'text': ''}
                }
                
                # Connect to database
                conn = self.db_connect()
                if not conn:
                    errors.append(f"Database connection failed for {printer['ip']}")
                    continue
                
                cursor = conn.cursor()
                device_number = self.get_next_device_number(cursor, printer_data['name'])
                
                # Create database entry
                now = datetime.now()
                formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
                
                # Default username/password for printers
                username = "admin"
                password = "admin"
                
                # Location string with font size (required by the system)
                location = f"FontSize:{printer_data['fontSize']}"
                
                # Insert into database
                sql = """
                INSERT INTO configh (
                    DeviceType, DeviceNumber, IP, Port, ComUser, 
                    comKey, Enable, CreatedDateTime, DevicePrinterIP, DeviceLocation, LicenseKey
                ) VALUES (
                     %s, %s, %s, %s, %s, 
                    AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                    %s, %s, %s, %s, %s
                )
                """
                values = (
                    printer_data['name'],  # DeviceType
                    device_number,
                    printer_data['ip'],    # IP
                    printer_data['port'],
                    username,
                    password,
                    formatted_now,  # Pass timestamp for encryption
                    'Y',            # Enable value
                    formatted_now,  # CreatedDateTime field
                    "",             # DevicePrinterIP - empty for printers
                    location,        # DeviceLocation with font size
                    self.license_key  # LicenseKey
                )
                
                cursor.execute(sql, values)
                conn.commit()
                
                # Update printer_data with device number for JSON
                printer_data['deviceNumber'] = device_number
                printer_data['enable'] = 'Y'
                printer_data['location'] = location
                
                # Save to JSON as well
                self.save_to_json(printer_data)
                
                # Emit signal
                self.printer_saved.emit(printer_data)
                
                saved_count += 1
                conn.close()
                
            except Exception as e:
                errors.append(f"Error saving {printer['ip']}: {str(e)}")
        
        # Close progress dialog
        progress_dialog.close()
        
        # Show results
        message = f"Successfully saved {saved_count} out of {len(printers)} printers."
        if errors:
            message += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more errors"
        
        if saved_count > 0:
            message += "\n\nAll printers have been saved with default settings."
        
        QMessageBox.information(self, "Batch Save Results", message)
    
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
        
        # Set header if available
        header = self.edit_printer.get('header', {})
        # If header is in old format or missing, create a default one
        if not isinstance(header, dict):
            header = {'enable': False, 'text': ''}
        
        if header.get('enable', False):
            self.enable_header.setChecked(True)
        else:
            self.disable_header.setChecked(True)
        self.token_header.setText(header.get('text', ''))
        
        # Set footer if available
        footer = self.edit_printer.get('footer', {})
        # If footer is in old format or missing, create a default one
        if not isinstance(footer, dict):
            footer = {'enable': False, 'text': ''}
            
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
        
        # Validate header text if header is enabled
        if self.enable_header.isChecked() and not self.token_header.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter header text or disable header")
            return False
            
        # Validate footer text if footer is enabled
        if self.enable_footer.isChecked() and not self.token_footer.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter footer text or disable footer")
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
            cursor.execute("SELECT MAX(DeviceNumber) FROM configh WHERE DeviceType = %s AND LicenseKey = %s", (device_type, self.license_key))
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
        
        # Create properly formatted header and footer objects that match what print.py expects
        header = {
            "enable": self.enable_header.isChecked(),
            "text": self.token_header.toPlainText().strip()
        }
        
        footer = {
            "enable": self.enable_footer.isChecked(),
            "text": self.token_footer.toPlainText().strip()
        }
        
        try:
            # Connect to database
            conn = self.db_connect()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Convert header/footer to location text
            location = " "
            
            # Set enable value - Enable by default
            enable_value = 'Y'
            print("location ->>>>>>>>",location)
            if self.edit_mode:
                # Update existing printer
                device_number = self.edit_printer.get('deviceNumber', 1)
                
                # Use the original printer name for the WHERE clause
                original_printer_name = self.edit_printer.get('name', printer_name)
                
                # Prepare SQL statement for update
                sql = """
                UPDATE configh SET
                    DeviceType = %s,
                    IP = %s,
                    Port = %s,
                    DeviceLocation = %s,
                    Enable = %s
                WHERE DeviceType = %s AND DeviceNumber = %s AND LicenseKey = %s
                """
                print("location ->>>>>>>>",location)

                # Execute SQL with values
                values = (
                    printer_name,  # New name
                    printer_ip,
                    printer_port,
                    location,
                    enable_value,
                    original_printer_name,  # Use original name in WHERE clause
                    device_number,
                    self.license_key
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
                    comKey, Enable, CreatedDateTime, DevicePrinterIP, LicenseKey
                ) VALUES (
                     %s, %s, %s, %s, %s, 
                    AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', %s), 512)), 
                    %s, %s, %s, %s
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
                    "",  # DevicePrinterIP - empty for printers
                    self.license_key  # LicenseKey
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
        print("printer_data ->>>>>>>>",printer_data)
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
        
        # Also save header and footer to appSettings.json if they are enabled
        try:
            app_settings = {}
            if os.path.exists('appSettings.json'):
                with open('appSettings.json', 'r') as f:
                    app_settings = json.load(f)
            
            # Add or update PrinterConfig section
            if 'PrinterConfig' not in app_settings:
                app_settings['PrinterConfig'] = {}
            
            # Update printer configuration
            app_settings['PrinterConfig']['IP'] = printer_data['ip']
            app_settings['PrinterConfig']['Port'] = printer_data['port']
            
            # Create properly formatted header and footer for print.py compatibility
            header = printer_data.get('header', {})
            footer = printer_data.get('footer', {})
            
            # Ensure header has the correct structure
            clean_header = {
                "enable": header.get('enable', False),
                "text": header.get('text', '').strip()
            }
            
            # Ensure footer has the correct structure
            clean_footer = {
                "enable": footer.get('enable', False),
                "text": footer.get('text', '').strip()
            }
            
            # Save header to PrinterConfig if enabled
            if clean_header["enable"] and clean_header["text"]:
                app_settings['PrinterConfig']['Header'] = clean_header
            else:
                # If header is disabled or empty, set enable to False but keep any existing text
                if 'Header' in app_settings['PrinterConfig']:
                    app_settings['PrinterConfig']['Header']['enable'] = False
                else:
                    app_settings['PrinterConfig']['Header'] = {"enable": False, "text": ""}
            
            # Save footer to PrinterConfig if enabled
            if clean_footer["enable"] and clean_footer["text"]:
                app_settings['PrinterConfig']['Footer'] = clean_footer
            else:
                # If footer is disabled or empty, set enable to False but keep any existing text
                if 'Footer' in app_settings['PrinterConfig']:
                    app_settings['PrinterConfig']['Footer']['enable'] = False
                else:
                    app_settings['PrinterConfig']['Footer'] = {"enable": False, "text": ""}
                
            # Save back to appSettings.json
            with open('appSettings.json', 'w') as f:
                json.dump(app_settings, f, indent=4)
                
            print("Printer settings saved to appSettings.json")
            
        except Exception as e:
            print(f"Error saving to appSettings.json: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PrinterSetupWindow()
    window.show()
    sys.exit(app.exec_())