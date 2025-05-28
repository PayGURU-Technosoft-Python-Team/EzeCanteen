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
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QBrush, QPalette
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy
import urllib.request
from io import BytesIO

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
            background-color: #111827;
            padding: 5px 10px;
            border-radius: 5px;
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
                        "minor": 75,  # Authentication passed
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
            time.sleep(5)
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        self.quit()
        self.wait()

class AuthEventItem(QFrame):
    def __init__(self, event_data):
        super().__init__()
        self.event_data = event_data
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a4a61, stop:1 #374151);
                border-radius: 10px;
                border: 1px solid #4b5563;
            }
        """)
        self.setMinimumSize(220, 240)
        self.setMaximumSize(250, 270)
        
        # Apply shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header with employee ID
        emp_id = event_data.get('employeeNoString', event_data.get('employeeNo', 'N/A'))
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        id_label = QLabel(f"ID: {emp_id}")
        id_label.setStyleSheet("color: #e5e7eb; background: transparent; border: none; font-size: 12px;")
        
        # Get time and format it nicely
        event_time = event_data.get('time', 'N/A')
        if 'T' in event_time:
            time_parts = event_time.split('T')[1].split('+')[0]
            if len(time_parts) > 5:  # Has seconds
                time_display = time_parts
            else:
                time_display = time_parts
        else:
            time_display = event_time
            
        time_label = QLabel(time_display)
        time_label.setStyleSheet("color: #9ca3af; background: transparent; border: none; font-size: 12px;")
        
        header_layout.addWidget(id_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        
        # Create image label with rounded corners
        self.image_container = QWidget()
        self.image_container.setStyleSheet("""
            background-color: #1f2937; 
            border-radius: 8px;
            border: 1px solid #4b5563;
        """)
        self.image_container.setFixedSize(140, 140)
        
        image_layout = QVBoxLayout(self.image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setFixedSize(130, 130)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")
        
        image_layout.addWidget(self.image_label)
        image_layout.setAlignment(Qt.AlignCenter)
        
        # Container for the image
        image_outer_container = QWidget()
        image_outer_layout = QHBoxLayout(image_outer_container)
        image_outer_layout.setContentsMargins(0, 0, 0, 0)
        image_outer_layout.addWidget(self.image_container)
        image_outer_layout.setAlignment(Qt.AlignCenter)
        
        # Name with bigger font
        name = event_data.get('name', 'N/A')
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            color: white; 
            font-weight: bold; 
            font-size: 16px;
            background: transparent;
            border: none;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        
        # Create info section
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Check for attendance info
        attendance_status = "N/A"
        label_name = "N/A"
        if "AttendanceInfo" in event_data:
            att = event_data["AttendanceInfo"]
            attendance_status = att.get('attendanceStatus', 'N/A')
            label_name = att.get('labelName', 'N/A')
            
        # Left column
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        status_label = QLabel("STATUS")
        status_label.setStyleSheet("color: #9ca3af; font-size: 10px; background: transparent; border: none;")
        
        status_value = QLabel(attendance_status)
        status_value.setStyleSheet("""
            color: #10b981; 
            font-weight: bold; 
            font-size: 14px;
            background: transparent;
            border: none;
        """)
        
        left_layout.addWidget(status_label)
        left_layout.addWidget(status_value)
        
        # Right column
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        label_title = QLabel("LABEL")
        label_title.setStyleSheet("color: #9ca3af; font-size: 10px; background: transparent; border: none;")
        
        label_value = QLabel(label_name)
        label_value.setStyleSheet("""
            color: #60a5fa; 
            font-weight: bold; 
            font-size: 14px;
            background: transparent;
            border: none;
        """)
        
        right_layout.addWidget(label_title)
        right_layout.addWidget(label_value)
        
        # Add columns to info layout
        info_layout.addWidget(left_column)
        info_layout.addWidget(right_column)
        
        # Add all widgets to main layout
        layout.addWidget(header)
        layout.addWidget(image_outer_container)
        layout.addWidget(name_label)
        layout.addWidget(info_widget)
        
        # Load image if available - do this last
        self.is_deleted = False
        self.load_image(event_data.get('pictureURL'))
    
    def load_image(self, url):
        """Load image from URL and display it"""
        if not url or url == 'N/A':
            # Set default image if no URL provided
            self.image_label.setText("No Image")
            self.image_label.setStyleSheet("color: #9ca3af; background: transparent; border: none;")
            return
            
        try:
            # Show loading indicator
            self.image_label.setText("Loading...")
            self.image_label.setStyleSheet("color: #9ca3af; background: transparent; border: none;")
            
            # Create a QTimer to load the image asynchronously
            self.timer = QTimer()
            self.timer.timeout.connect(lambda: self._fetch_image(url))
            self.timer.setSingleShot(True)
            self.timer.start(100)  # Start after 100ms
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_label.setText("Error")
            self.image_label.setStyleSheet("color: #f87171; background: transparent; border: none;")
    
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
                    self.image_label.size(),
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
        self.max_events = 12  # Maximum number of events to display in grid
        self.init_ui()
        
        # Start authentication event monitor thread
        self.auth_monitor = AuthEventMonitor(self.communicator)
        self.communicator.new_auth_event.connect(self.add_auth_event)
        self.auth_monitor.start()
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("EzeeCanteen")
        self.setGeometry(100, 100, 900, 700)  # Larger window
        
        # Set background gradient
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#111827"))  # Dark blue/gray at top
        gradient.setColorAt(1, QColor("#1f2937"))  # Slightly lighter at bottom
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111827, stop:1 #1e3a8a);
                border-radius: 12px;
                border: 1px solid #374151;
            }
        """)
        
        # Apply shadow effect to header
        header_shadow = QGraphicsDropShadowEffect(header_frame)
        header_shadow.setBlurRadius(15)
        header_shadow.setColor(QColor(0, 0, 0, 100))
        header_shadow.setOffset(0, 2)
        header_frame.setGraphicsEffect(header_shadow)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Time display
        self.time_display = TimeDisplay()
        self.time_display.setMinimumWidth(150)
        
        # Title display with icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_icon = QLabel("🔐")  # Authentication icon
        title_icon.setFont(QFont("Arial", 18))
        title_icon.setStyleSheet("background: transparent; border: none;")
        
        title_label = QLabel("Authentication Events")
        title_label.setStyleSheet("color: white; font-weight: bold; background: transparent; border: none;")
        title_label.setFont(QFont("Arial", 18))
        title_label.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.setAlignment(Qt.AlignCenter)
        
        # Settings button
        settings_button = QPushButton("⚙️")
        settings_button.setFont(QFont("Arial", 16))
        settings_button.setStyleSheet("""
            QPushButton {
                color: white;
                font-weight: bold;
                background-color: #374151;
                border-radius: 8px;
                padding: 5px 10px;
                border: 1px solid #4b5563;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        settings_button.setFixedSize(40, 40)
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
                background-color: rgba(17, 24, 39, 0.7);
                border-radius: 12px;
                border: 1px solid #374151;
            }
        """)
        
        # Apply shadow effect to grid container
        grid_shadow = QGraphicsDropShadowEffect(grid_container)
        grid_shadow.setBlurRadius(15)
        grid_shadow.setColor(QColor(0, 0, 0, 100))
        grid_shadow.setOffset(0, 2)
        grid_container.setGraphicsEffect(grid_shadow)
        
        grid_layout = QVBoxLayout(grid_container)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        
        # Grid for content
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)  # Reduced spacing between items
        
        grid_layout.addWidget(self.grid_widget)
        
        # Add grid container to scroll area
        scroll_area.setWidget(grid_container)
        
        # Footer with gradient
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:1 #111827);
                border-radius: 12px;
                border: 1px solid #374151;
            }
        """)
        footer_frame.setMaximumHeight(50)
        
        # Apply shadow effect to footer
        footer_shadow = QGraphicsDropShadowEffect(footer_frame)
        footer_shadow.setBlurRadius(15)
        footer_shadow.setColor(QColor(0, 0, 0, 100))
        footer_shadow.setOffset(0, 2)
        footer_frame.setGraphicsEffect(footer_shadow)
        
        footer_layout = QHBoxLayout(footer_frame)
        
        # Logo/icon for footer
        footer_icon = QLabel("🍽️")
        footer_icon.setFont(QFont("Arial", 16))
        footer_icon.setStyleSheet("background: transparent; border: none;")
        
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setStyleSheet("color: #9ca3af; font-size: 14px; background: transparent; border: none;")
        footer_label.setAlignment(Qt.AlignCenter)
        
        footer_layout.addWidget(footer_icon)
        footer_layout.addWidget(footer_label)
        
        # Add sections to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(footer_frame)
    
    def add_auth_event(self, event_data):
        """Add a new authentication event to the grid"""
        # Add event to the list
        self.events.insert(0, event_data)
        
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
        cols = 3  # Number of columns in the grid
        
        for i, event in enumerate(self.events):
            row = i // cols
            col = i % cols
            
            event_item = AuthEventItem(event)
            self.grid_layout.addWidget(event_item, row, col)
    
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

def main():
    app = QApplication(sys.argv)
    window = EzeeCanteen()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
        