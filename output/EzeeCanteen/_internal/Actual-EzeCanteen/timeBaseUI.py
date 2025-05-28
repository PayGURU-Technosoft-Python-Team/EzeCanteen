import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                             QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon

class Communicator(QObject):
    # Signal to communicate between components
    stop_server = pyqtSignal()

class TimeDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("color: white; font-weight: bold;")
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

class EzeeCanteen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.communicator = Communicator()
        self.init_ui()
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("EzeeCanteen")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #1f2937;") # bg-gray-800
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #111827; border-radius: 8px;") # bg-gray-900
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        # Time display
        self.time_display = TimeDisplay()
        self.time_display.setMinimumWidth(150)
        
        # Title display
        title_label = QLabel("Live Display")
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_label.setFont(QFont("Arial", 14))
        title_label.setAlignment(Qt.AlignCenter)
        
        # Settings button
        settings_button = QPushButton("⚙️")
        settings_button.setFont(QFont("Arial", 14))
        settings_button.setStyleSheet("color: white; font-weight: bold; border: none;")
        settings_button.clicked.connect(self.open_settings)
        
        # Add widgets to header layout
        header_layout.addWidget(self.time_display)
        header_layout.addWidget(title_label, 1)
        header_layout.addWidget(settings_button)
        
        # Grid for content
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        
        # Footer
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setStyleSheet("color: #9ca3af; font-size: 16px;") # text-gray-400
        footer_label.setAlignment(Qt.AlignCenter)
        
        # Add sections to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.grid_widget, 1)
        main_layout.addWidget(footer_label)
        
        # Example of adding items to grid (this would be filled dynamically)
        # You would replace this with your actual content logic
        self.populate_grid_with_dummy_data()
        
    def populate_grid_with_dummy_data(self):
        """Temporary function to populate grid with example items - replace with your actual data"""
        for row in range(3):
            for col in range(4):
                item = QFrame()
                item.setStyleSheet("background-color: #374151; border-radius: 8px;")
                item_layout = QVBoxLayout(item)
                
                label = QLabel(f"Item {row*4+col+1}")
                label.setStyleSheet("color: white; font-weight: bold;")
                label.setAlignment(Qt.AlignCenter)
                
                item_layout.addWidget(label)
                self.grid_layout.addWidget(item, row, col)
                
    def open_settings(self):
        """Function to handle settings button click"""
        # In the original code this would stop the server and redirect to settings
        self.communicator.stop_server.emit()
        # For demonstration, we'll just print a message
        print("Opening settings page...")
        # In a real application, you would create a settings dialog or switch to a settings screen
        # self.close()
        # os.system("python appSettings.py")  # Example approach

def main():
    app = QApplication(sys.argv)
    window = EzeeCanteen()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
