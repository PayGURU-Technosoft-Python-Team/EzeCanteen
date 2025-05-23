import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QRadioButton, QLineEdit, QTableWidget,
                            QTableWidgetItem, QHeaderView, QFrame, QTimeEdit, QTextEdit,
                            QStackedWidget)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont, QIcon
from reports import ReportsWidget

class EzeeCanteenApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.setStyleSheet("background-color: #1E293B; color: white;")
        self.setMinimumSize(900, 650)
        
        # Track if we're running inside settings.py
        self.is_embedded = False
        
        # Create stacked widget to switch between views
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create settings widget
        self.settings_widget = QWidget()
        self.setup_settings_ui()
        
        # Create reports widget
        self.reports_widget = ReportsWidget(self)
        
        # Add widgets to stacked widget
        self.stacked_widget.addWidget(self.settings_widget)
        self.stacked_widget.addWidget(self.reports_widget)
        
        # Load settings from appSettings.json
        self.load_settings()
    
    def setup_settings_ui(self):
        # Main layout for settings
        main_layout = QVBoxLayout(self.settings_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel("Canteen Settings")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        
        # Email and Report buttons
        email_btn = QPushButton()
        email_btn.setIcon(QIcon.fromTheme("mail-send"))
        email_btn.setText("📧")
        email_btn.setStyleSheet("background-color: #8B5CF6; padding: 10px; border-radius: 4px; font-size: 18px;")
        email_btn.setFixedSize(50, 40)
        email_btn.clicked.connect(self.add_mail)
        
        reports_btn = QPushButton()
        reports_btn.setIcon(QIcon.fromTheme("document"))
        reports_btn.setText("📃")
        reports_btn.setStyleSheet("background-color: #3B82F6; padding: 10px; border-radius: 4px; font-size: 18px;")
        reports_btn.setFixedSize(50, 40)
        reports_btn.clicked.connect(self.get_reports)
        
        header_layout.addStretch()
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(email_btn)
        header_layout.addWidget(reports_btn)
        
        main_layout.addWidget(header_frame)
        
        # Disable Punch Until Next Meal
        disable_punch_frame = QFrame()
        disable_punch_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        disable_punch_layout = QHBoxLayout(disable_punch_frame)
        
        disable_punch_label = QLabel("Disable Punch Until Next Meal")
        disable_punch_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        # Yes/No toggle button
        self.yes_no_btn = QPushButton("No")
        self.yes_no_btn.setStyleSheet(
            "background-color: #EF4444; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
        )
        self.yes_no_btn.setFixedSize(60, 30)
        self.yes_no_btn.setCheckable(True)
        self.yes_no_btn.toggled.connect(self.toggle_yes_no)
        
        disable_punch_layout.addWidget(disable_punch_label)
        disable_punch_layout.addStretch()
        disable_punch_layout.addWidget(self.yes_no_btn)
        
        main_layout.addWidget(disable_punch_frame)
        
        # Meal Time Table
        self.time_table_frame = QFrame()
        self.time_table_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        time_table_layout = QVBoxLayout(self.time_table_frame)
        
        # Table headers
        table_headers = QHBoxLayout()
        from_time_label = QLabel("From Time")
        from_time_label.setAlignment(Qt.AlignCenter)
        from_time_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        to_time_label = QLabel("To Time")
        to_time_label.setAlignment(Qt.AlignCenter)
        to_time_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        meal_label_label = QLabel("Meal Label")
        meal_label_label.setAlignment(Qt.AlignCenter)
        meal_label_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        price_label = QLabel("Price")
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        # Add empty label for delete button column
        empty_label = QLabel("")
        
        table_headers.addWidget(from_time_label, 1)
        table_headers.addWidget(to_time_label, 1)
        table_headers.addWidget(meal_label_label, 1)
        table_headers.addWidget(price_label, 1)
        table_headers.addWidget(empty_label, 0)
        
        time_table_layout.addLayout(table_headers)
        
        # Store time rows for handling multiple entries
        self.time_rows = []
        
        # Initial row for time inputs (will be replaced by loaded data)
        self.create_time_row()
        
        time_table_layout.addLayout(self.time_rows[0]['layout'])
        main_layout.addWidget(self.time_table_frame)
        
        # Special Message
        special_msg_frame = QFrame()
        special_msg_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        special_msg_layout = QVBoxLayout(special_msg_frame)
        
        special_msg_label = QLabel("Special Message(optional)")
        special_msg_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.special_msg_input = QLineEdit()
        self.special_msg_input.setPlaceholderText("eg. No lunch on weekends")
        self.special_msg_input.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 10px; font-size: 14px;"
        )
        
        special_msg_layout.addWidget(special_msg_label)
        special_msg_layout.addWidget(self.special_msg_input)
        
        main_layout.addWidget(special_msg_frame)
        
        # Bottom Buttons
        buttons_layout = QHBoxLayout()
        
        # Add spacer to push buttons to the right
        buttons_layout.addStretch()
        
        add_row_btn = QPushButton("Add Row")
        add_row_btn.setStyleSheet(
            "background-color: #3B82F6; border-radius: 4px; padding: 10px 20px; font-size: 14px; font-weight: bold;"
        )
        add_row_btn.clicked.connect(self.add_row)
        
        save_changes_btn = QPushButton("Save Changes")
        save_changes_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #10B981;"
            "    border-radius: 4px;"
            "    padding: 10px 20px;"
            "    font-size: 14px;"
            "    font-weight: bold;"
            "    color: white;"
            "}"
            "QPushButton:hover {"
            "    background-color: #0DA271;"
            "}"
            "QPushButton:pressed {"
            "    background-color: #0C8A61;"
            "    padding-top: 11px;"
            "    padding-bottom: 9px;"
            "}"
        )

        save_changes_btn.clicked.connect(self.save_changes)
        
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #F59E0B;"
            "    border-radius: 4px;"
            "    padding: 10px 20px;"
            "    font-size: 14px;"
            "    font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "    background-color:rgb(185, 122, 12);"
            "}"
            "QPushButton:pressed {"
            "    background-color:rgb(231, 136, 12);"
            "    padding-top: 11px;"
            "    padding-bottom: 9px;"
            "}"
        )
        back_btn.clicked.connect(self.go_back)
        
        buttons_layout.addWidget(add_row_btn)
        buttons_layout.addWidget(save_changes_btn)
        buttons_layout.addWidget(back_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Footer
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #94A3B8; margin-top: 20px;")
        main_layout.addWidget(footer_label)
        
        # Push everything up with a stretch at the bottom
        main_layout.addStretch()
    
    # Methods for switching between views
    def show_settings_view(self):
        self.stacked_widget.setCurrentIndex(0)
    
    def show_reports_view(self):
        self.stacked_widget.setCurrentIndex(1)
    
    def create_time_row(self):
        """Create a new time row with all necessary widgets"""
        row = {}
        time_row = QHBoxLayout()
        
        # From Time
        from_time = QTimeEdit()
        from_time.setDisplayFormat("HH:mm")
        from_time.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # To Time
        to_time = QTimeEdit()
        to_time.setDisplayFormat("HH:mm")
        to_time.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # Meal Label
        meal_label = QLineEdit()
        meal_label.setPlaceholderText("eg. Lunch")
        meal_label.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # Price
        price_input = QLineEdit()
        price_input.setPlaceholderText("0.00")
        price_input.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(
            "background-color: #EF4444; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        
        time_row.addWidget(from_time, 1)
        time_row.addWidget(to_time, 1)
        time_row.addWidget(meal_label, 1)
        time_row.addWidget(price_input, 1)
        time_row.addWidget(delete_btn, 0)
        
        row['layout'] = time_row
        row['from_time'] = from_time
        row['to_time'] = to_time
        row['meal_label'] = meal_label
        row['price_input'] = price_input
        row['delete_btn'] = delete_btn
        
        self.time_rows.append(row)
        return row
    
    def update_ui(self):
        # This would handle UI updates based on selected radio button
        pass
    
    def toggle_yes_no(self, checked):
        if checked:
            self.yes_no_btn.setText("Yes")
            self.yes_no_btn.setStyleSheet(
                "background-color: #10B981; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
            )
        else:
            self.yes_no_btn.setText("No")
            self.yes_no_btn.setStyleSheet(
                "background-color: #EF4444; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
            )
    
    def add_row(self):
        """Add a new row to the meal time table"""
        row = self.create_time_row()
        layout = self.time_table_frame.layout()
        layout.addLayout(row['layout'])
    
    def delete_row(self, row_to_delete):
        """Delete the specified row from the meal time table"""
        # Don't delete if it's the only row
        if len(self.time_rows) <= 1:
            return
        
        # Delete all widgets in the row
        for i in range(row_to_delete['layout'].count()):
            widget = row_to_delete['layout'].itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Remove the layout
        self.time_table_frame.layout().removeItem(row_to_delete['layout'])
        
        # Remove from our list
        self.time_rows.remove(row_to_delete)
    
    def load_settings(self):
        """Load settings from appSettings.json file"""
        try:
            if os.path.exists('appSettings.json'):
                with open('appSettings.json', 'r') as f:
                    settings = json.load(f)
                
                canteen_menu = settings.get('CanteenMenu', {})
                
                # Load disable punch setting
                disable_punch = canteen_menu.get('DisablePunch', False)
                self.yes_no_btn.setChecked(disable_punch)
                
                # Load special message
                special_msg = canteen_menu.get('SpecialMessage', '')
                self.special_msg_input.setText(special_msg)
                
                # Load meal schedule
                meal_schedule = canteen_menu.get('MealSchedule', [])
                
                # Clear existing rows
                for i in range(len(self.time_rows)):
                    row = self.time_rows[0]  # Always delete the first one
                    for j in range(row['layout'].count()):
                        widget = row['layout'].itemAt(j).widget()
                        if widget is not None:
                            widget.deleteLater()
                    self.time_table_frame.layout().removeItem(row['layout'])
                
                self.time_rows.clear()
                
                # Add rows for each meal in schedule
                for meal in meal_schedule:
                    row = self.create_time_row()
                    
                    # Set values from loaded data
                    from_time = meal.get('fromTime', '00:00')
                    to_time = meal.get('toTime', '00:00')
                    meal_type = meal.get('mealType', '')
                    price = meal.get('price', '0')
                    
                    # Parse time strings and set QTimeEdit values
                    hours, minutes = map(int, from_time.split(':'))
                    row['from_time'].setTime(QTime(hours, minutes))
                    
                    hours, minutes = map(int, to_time.split(':'))
                    row['to_time'].setTime(QTime(hours, minutes))
                    
                    row['meal_label'].setText(meal_type)
                    row['price_input'].setText(price)
                    
                    # Add row to layout
                    self.time_table_frame.layout().addLayout(row['layout'])
                
                # If no meals were loaded, add an empty row
                if len(self.time_rows) == 0:
                    row = self.create_time_row()
                    self.time_table_frame.layout().addLayout(row['layout'])
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            # If there's an error, ensure we have at least one row
            if len(self.time_rows) == 0:
                row = self.create_time_row()
                self.time_table_frame.layout().addLayout(row['layout'])
    
    def save_changes(self):
        """Save current settings to appSettings.json file"""
        try:
            # Prepare the settings object
            settings = {}
            
            # Try to load existing settings first to preserve any settings we're not modifying
            if os.path.exists('appSettings.json'):
                with open('appSettings.json', 'r') as f:
                    settings = json.load(f)
            
            # Create CanteenMenu if it doesn't exist
            if 'CanteenMenu' not in settings:
                settings['CanteenMenu'] = {}
            
            # Update CanteenMenu settings
            settings['CanteenMenu']['Type'] = 'timeOptions'
            settings['CanteenMenu']['DisablePunch'] = self.yes_no_btn.isChecked()
            settings['CanteenMenu']['SpecialMessage'] = self.special_msg_input.text()
            
            # Collect meal schedules
            meal_schedule = []
            for row in self.time_rows:
                meal = {
                    'fromTime': row['from_time'].time().toString('HH:mm'),
                    'toTime': row['to_time'].time().toString('HH:mm'),
                    'mealType': row['meal_label'].text(),
                    'price': row['price_input'].text()
                }
                meal_schedule.append(meal)
            
            settings['CanteenMenu']['MealSchedule'] = meal_schedule
            
            # Save to file
            with open('appSettings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            
            print("Settings saved successfully")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def go_back(self):
        """Navigate back to the previous screen"""
        print("Back button clicked in CanteenSettings.py - go_back method")
        # The original go_back should be safe to call in any context - only closes the window
        # when running as a standalone app, otherwise should be overridden
        if __name__ == "__main__":
            print("Closing standalone canteen settings")
            self.close()
    
    def add_mail(self):
        print("Add Mail button clicked")
    
    def get_reports(self):
        print("Get Reports button clicked")
        self.show_reports_view()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EzeeCanteenApp()
    window.show()
    sys.exit(app.exec_())