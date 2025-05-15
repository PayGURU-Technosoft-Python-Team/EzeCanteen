import requests
from requests.auth import HTTPDigestAuth
import json
from datetime import datetime, timedelta
import time
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                             QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
                             QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QThread, QFile
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QBrush, QPalette
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy
import urllib.request
from io import BytesIO
from print import print_slip  # Import print_slip function

# Device configuration
IP = "192.168.0.82"
PORT = 80
USERNAME = "admin"
PASSWORD = "a1234@4321"

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
            else:
                self.from_time_str = ''
                self.to_time_str = ''
        except Exception as e:
            print(f"Error reading appSettings.json: {e}")
            self.from_time_str = ''
            self.to_time_str = ''
        
        # Use the global configuration
        self.ip = IP
        self.port = PORT
        self.username = USERNAME
        self.password = PASSWORD
        
        # URL for access control events
        self.url = f"http://{self.ip}:{self.port}/ISAPI/AccessControl/AcsEvent?format=json"
        
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
                                    
                                    # Emit signal with event data
                                    self.communicator.new_auth_event.emit(event)
                            
                            # Limit the size of processed_events to avoid memory issues
                            if len(self.processed_events) > 1000:
                                # Keep only the most recent 500 events
                                self.processed_events = set(list(self.processed_events)[-500:])
                    
                    except json.JSONDecodeError:
                        print("Response is not valid JSON")
                        
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            # Sleep for a short period before the next check
            time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread"""
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
        name_label.setStyleSheet("color: #bdc3c7; font-size: 10px; background: transparent;")
        
        name = event_data.get('name', 'N/A')
        name_value = QLabel(name)
        name_value.setStyleSheet("""
            color: #2ecc71; 
            font-weight: bold; 
            font-size: 13px;
            background: transparent;
        """)
        
        left_layout.addWidget(name_label)
        left_layout.addWidget(name_value)
        
        # Right column - Date (previously Label)
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        date_title = QLabel("DATE")
        date_title.setStyleSheet("color: #bdc3c7; font-size: 10px; background: transparent;")
        
        date_value = QLabel(date_parts)
        date_value.setStyleSheet("""
            color: #3498db; 
            font-weight: bold; 
            font-size: 13px;
            background: transparent;
        """)
        
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
                    
                # Load the image data
                image_data = BytesIO(response.content)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data.getvalue())
                
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
        self.max_events = 18  # Increased maximum number of events
        self.token_counter = 0  # Initialize token counter
        self.current_date = datetime.now().date()  # Track date for token counter reset
        self.init_ui()
        
        # Connect resize event to refresh grid
        self.resized = False
        
        # Start authentication event monitor thread
        self.auth_monitor = AuthEventMonitor(self.communicator)
        print
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
            # Default printer settings
            self.printer_ip = "192.168.0.251"
            self.printer_port = 9100
            self.header = {'enable': True, 'text': "EzeeCanteen"}
            self.footer = {'enable': True, 'text': "Thank you!"}
            self.special_message = ""
        
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
        
        title_label = QLabel("Authentication Events")
        title_label.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        title_label.setFont(QFont("Arial", 16))
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
        scroll_area.setStyleSheet("background: transparent; border: none;")
        
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
            
            # Print token slip
            try:
                print_slip(
                    self.printer_ip, 
                    self.printer_port, 
                    self.token_counter, 
                    self.header, 
                    coupon_type, 
                    emp_id, 
                    name, 
                    punch_time, 
                    self.special_message, 
                    self.footer
                )
                print(f"Token {self.token_counter} printed for {name}")
            except Exception as e:
                print(f"Error printing token: {e}")
        
        # Limit the number of events
        if len(self.events) > self.max_events:
            self.events = self.events[:self.max_events]
        
        # Clear the grid
        self.clear_grid()
        
        # Repopulate the grid with updated events
        self.populate_grid()
        
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
    
    def clear_grid(self):
        """Clear all items from the grid layout"""
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
    
    def open_settings(self):
        """Function to handle settings button click"""
        # Stop the authentication monitor
        self.communicator.stop_server.emit()
        
        # Close the current window
        self.close()
        
        # Launch the settings application
        os.system("python appSettings.py")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.communicator.stop_server.emit()
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
        if self.events:
            self.clear_grid()
            self.populate_grid()

def main():
    app = QApplication(sys.argv)
    window = EzeeCanteen()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
        