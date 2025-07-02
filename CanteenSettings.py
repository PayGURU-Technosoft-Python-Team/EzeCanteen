import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QRadioButton, QLineEdit, QTableWidget,
                            QTableWidgetItem, QHeaderView, QFrame, QTimeEdit, QTextEdit,
                            QStackedWidget, QButtonGroup)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont, QIcon
from reports import ReportsWidget
from AddMail import MailSettingsWindow

class EzeeCanteenApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EzeeCanteen")
        self.setStyleSheet("background-color: #1E293B; color: white;")
        self.setMinimumSize(900, 920)
        
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
        
        # Select Menu Options
        menu_options_frame = QFrame()
        menu_options_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        menu_options_layout = QVBoxLayout(menu_options_frame)
        
        menu_options_label = QLabel("Select Menu Options:")
        menu_options_label.setFont(QFont("Arial", 12, QFont.Bold))
        menu_options_layout.addWidget(menu_options_label)
        
        # Radio buttons layout
        radio_layout = QHBoxLayout()
        
        # Create button group to ensure only one is selected at a time
        self.menu_option_group = QButtonGroup()
        
        # Time Based radio button
        self.time_based_radio = QRadioButton("Time Based")
        self.time_based_radio.setStyleSheet("""
            QRadioButton {
                font-size: 12px;
                font-weight: bold;
                color: white;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator::unchecked {
                border: 2px solid #64748B;
                border-radius: 8px;
                background-color: transparent;
            }
            QRadioButton::indicator::checked {
                border: 2px solid #3B82F6;
                border-radius: 8px;
                background-color: #3B82F6;
            }
            QRadioButton::indicator::checked::before {
                content: '';
                width: 6px;
                height: 6px;
                border-radius: 3px;
                background-color: white;
                margin: 3px;
            }
        """)
        self.time_based_radio.setChecked(True)  # Default selection
        self.time_based_radio.toggled.connect(self.on_menu_option_changed)
        
        # Custom radio button
        self.custom_radio = QRadioButton("Custom")
        self.custom_radio.setStyleSheet(self.time_based_radio.styleSheet())
        self.custom_radio.toggled.connect(self.on_menu_option_changed)
        
        # Device radio button
        self.device_radio = QRadioButton("Device")
        self.device_radio.setStyleSheet(self.time_based_radio.styleSheet())
        self.device_radio.toggled.connect(self.on_menu_option_changed)
        
        # Add radio buttons to button group
        self.menu_option_group.addButton(self.time_based_radio, 0)
        self.menu_option_group.addButton(self.custom_radio, 1)
        self.menu_option_group.addButton(self.device_radio, 2)
        
        radio_layout.addWidget(self.time_based_radio)
        radio_layout.addWidget(self.custom_radio)
        radio_layout.addWidget(self.device_radio)
        radio_layout.addStretch()
        
        menu_options_layout.addLayout(radio_layout)
        main_layout.addWidget(menu_options_frame)
        
        # Punch Interval Section (only for Custom mode)
        self.punch_interval_frame = QFrame()
        self.punch_interval_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        punch_interval_layout = QHBoxLayout(self.punch_interval_frame)
        
        punch_interval_label = QLabel("Punch Interval:")
        punch_interval_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.punch_interval_input = QLineEdit("1")
        self.punch_interval_input.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px; max-width: 60px;"
        )
        
        minutes_label = QLabel("Minute(s)")
        minutes_label.setFont(QFont("Arial", 12))
        
        # Select All / Deselect All buttons
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(
            "background-color: #10B981; border-radius: 4px; padding: 8px 15px; font-size: 12px; font-weight: bold;"
        )
        select_all_btn.clicked.connect(self.select_all_items)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet(
            "background-color: #EF4444; border-radius: 4px; padding: 8px 15px; font-size: 12px; font-weight: bold;"
        )
        deselect_all_btn.clicked.connect(self.deselect_all_items)
        
        # Toggle for Yes/No
        self.punch_yes_no_btn = QPushButton("Yes")
        self.punch_yes_no_btn.setStyleSheet(
            "background-color: #10B981; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
        )
        self.punch_yes_no_btn.setFixedSize(60, 30)
        self.punch_yes_no_btn.setCheckable(True)
        self.punch_yes_no_btn.setChecked(True)
        self.punch_yes_no_btn.toggled.connect(self.toggle_punch_yes_no)
        
        punch_interval_layout.addWidget(punch_interval_label)
        punch_interval_layout.addWidget(self.punch_interval_input)
        punch_interval_layout.addWidget(minutes_label)
        punch_interval_layout.addStretch()
        punch_interval_layout.addWidget(select_all_btn)
        punch_interval_layout.addWidget(deselect_all_btn)
        punch_interval_layout.addWidget(self.punch_yes_no_btn)
        
        main_layout.addWidget(self.punch_interval_frame)
        self.punch_interval_frame.hide()  # Initially hidden
        
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
        
        # Meal Time Table / Food Items Table (conditional based on mode)
        self.create_time_based_section(main_layout)
        self.create_custom_section(main_layout)
        
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
    
    def create_time_based_section(self, main_layout):
        """Create the time-based meal schedule section"""
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
    
    def create_custom_section(self, main_layout):
        """Create the custom food items section"""
        # Food Items Table
        self.food_table_frame = QFrame()
        self.food_table_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; padding: 15px;")
        food_table_layout = QVBoxLayout(self.food_table_frame)
        
        # Table headers
        food_headers = QHBoxLayout()
        food_item_label = QLabel("Food Item")
        food_item_label.setAlignment(Qt.AlignCenter)
        food_item_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        food_price_label = QLabel("Price")
        food_price_label.setAlignment(Qt.AlignCenter)
        food_price_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        # Add empty label for delete button column
        food_empty_label = QLabel("")
        
        food_headers.addWidget(food_item_label, 2)
        food_headers.addWidget(food_price_label, 1)
        food_headers.addWidget(food_empty_label, 0)
        
        food_table_layout.addLayout(food_headers)
        
        # Store food rows for handling multiple entries
        self.food_rows = []
        
        # Initial row for food inputs
        self.create_food_row()
        
        food_table_layout.addLayout(self.food_rows[0]['layout'])
        main_layout.addWidget(self.food_table_frame)
        self.food_table_frame.hide()  # Initially hidden
    
    def create_food_row(self):
        """Create a new food item row with all necessary widgets"""
        row = {}
        food_row = QHBoxLayout()
        
        # Food Item
        food_item = QLineEdit()
        food_item.setPlaceholderText("eg. Pizza")
        food_item.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # Price
        price_input = QLineEdit()
        price_input.setPlaceholderText("Price")
        price_input.setStyleSheet(
            "background-color: #1E293B; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(
            "background-color: #EF4444; border-radius: 4px; padding: 8px; font-size: 14px;"
        )
        delete_btn.clicked.connect(lambda: self.delete_food_row(row))
        
        food_row.addWidget(food_item, 2)
        food_row.addWidget(price_input, 1)
        food_row.addWidget(delete_btn, 0)
        
        row['layout'] = food_row
        row['food_item'] = food_item
        row['price_input'] = price_input
        row['delete_btn'] = delete_btn
        
        self.food_rows.append(row)
        return row
    
    def delete_food_row(self, row_to_delete):
        """Delete the specified food row"""
        # Don't delete if it's the only row
        if len(self.food_rows) <= 1:
            return
        
        # Delete all widgets in the row
        for i in range(row_to_delete['layout'].count()):
            widget = row_to_delete['layout'].itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Remove the layout
        self.food_table_frame.layout().removeItem(row_to_delete['layout'])
        
        # Remove from our list
        self.food_rows.remove(row_to_delete)
    
    def on_menu_option_changed(self):
        """Handle menu option radio button changes"""
        if self.time_based_radio.isChecked():
            # Show time-based elements
            self.time_table_frame.show()
            self.food_table_frame.hide()
            self.punch_interval_frame.hide()
        elif self.custom_radio.isChecked():
            # Show custom elements
            self.time_table_frame.hide()
            self.food_table_frame.show()
            self.punch_interval_frame.show()
        elif self.device_radio.isChecked():
            # Hide both tables for device mode
            self.time_table_frame.hide()
            self.food_table_frame.hide()
            self.punch_interval_frame.hide()
    
    def toggle_punch_yes_no(self, checked):
        """Toggle the punch interval yes/no button"""
        if checked:
            self.punch_yes_no_btn.setText("Yes")
            self.punch_yes_no_btn.setStyleSheet(
                "background-color: #10B981; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
            )
        else:
            self.punch_yes_no_btn.setText("No")
            self.punch_yes_no_btn.setStyleSheet(
                "background-color: #EF4444; color: white; border-radius: 15px; padding: 5px; font-weight: bold; min-width: 60px;"
            )
    
    def select_all_items(self):
        """Select all items (implementation depends on specific requirements)"""
        print("Select All clicked")
        # This would typically select all items in a list or table
        pass
    
    def deselect_all_items(self):
        """Deselect all items (implementation depends on specific requirements)"""
        print("Deselect All clicked")
        # This would typically deselect all items in a list or table
        pass
    
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
        """Add a new row to the appropriate table based on current mode"""
        if self.time_based_radio.isChecked():
            # Add time-based row
            row = self.create_time_row()
            layout = self.time_table_frame.layout()
            layout.addLayout(row['layout'])
        elif self.custom_radio.isChecked():
            # Add custom food row
            row = self.create_food_row()
            layout = self.food_table_frame.layout()
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
                
                # Load current mode (use 'timeBased' as key instead of 'timeOptions')
                current_mode = canteen_menu.get('currentMode', 'timeBased')
                if current_mode == 'timeBased' or current_mode == 'timeOptions':  # Handle both old and new format
                    self.time_based_radio.setChecked(True)
                    current_mode = 'timeBased'  # Normalize to new format
                elif current_mode == 'custom':
                    self.custom_radio.setChecked(True)
                elif current_mode == 'device':
                    self.device_radio.setChecked(True)
                else:
                    self.time_based_radio.setChecked(True)
                    current_mode = 'timeBased'
                
                # Load mode-specific configurations
                time_based_config = canteen_menu
                custom_config = canteen_menu.get('custom', {})
                device_config = canteen_menu.get('device', {})
                
                # If old format exists, migrate it
                if 'Type' in canteen_menu and not time_based_config and not custom_config:
                    old_type = canteen_menu.get('Type', 'timeOptions')
                    if old_type == 'timeOptions':
                        time_based_config = {
                            'DisablePunch': canteen_menu.get('DisablePunch', False),
                            'SpecialMessage': canteen_menu.get('SpecialMessage', ''),
                            'MealSchedule': canteen_menu.get('MealSchedule', [])
                        }
                        
                    elif old_type == 'custom':
                        custom_config = {
                            'DisablePunch': canteen_menu.get('DisablePunch', False),
                            'SpecialMessage': canteen_menu.get('SpecialMessage', ''),
                            'PunchInterval': canteen_menu.get('PunchInterval', '1'),
                            'FoodItems': canteen_menu.get('FoodItems', [])
                        }
                
                # Load settings based on current mode
                if current_mode == 'timeBased':
                    current_config = time_based_config
                    print("TIME BASE : ", current_config)
                elif current_mode == 'custom':
                    current_config = custom_config
                elif current_mode == 'device':
                    current_config = device_config
                else:
                    current_config = {}
                
                # Load common settings from current mode
                disable_punch = current_config.get('DisablePunch', False)
                self.yes_no_btn.setChecked(disable_punch)
                
                special_msg = current_config.get('SpecialMessage', '')
                self.special_msg_input.setText(special_msg)
                
                # Load punch interval from custom config (always available for custom mode)
                punch_interval = custom_config.get('PunchInterval', '1')
                self.punch_interval_input.setText(str(punch_interval))
                
                # Load time-based meal schedule
                meal_schedule = time_based_config.get('MealSchedule', [])
                
                # Clear existing time rows
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
                    try:
                        hours, minutes = map(int, from_time.split(':'))
                        row['from_time'].setTime(QTime(hours, minutes))
                        
                        hours, minutes = map(int, to_time.split(':'))
                        row['to_time'].setTime(QTime(hours, minutes))
                    except:
                        # Default times if parsing fails
                        row['from_time'].setTime(QTime(0, 0))
                        row['to_time'].setTime(QTime(0, 0))
                    
                    row['meal_label'].setText(meal_type)
                    row['price_input'].setText(str(price))
                    
                    # Add row to layout
                    self.time_table_frame.layout().addLayout(row['layout'])
                
                # If no meals were loaded, add an empty row
                if len(self.time_rows) == 0:
                    row = self.create_time_row()
                    self.time_table_frame.layout().addLayout(row['layout'])
                
                # Load custom food items
                food_items = custom_config.get('FoodItems', [])
                
                # Clear existing food rows
                for i in range(len(self.food_rows)):
                    row = self.food_rows[0]  # Always delete the first one
                    for j in range(row['layout'].count()):
                        widget = row['layout'].itemAt(j).widget()
                        if widget is not None:
                            widget.deleteLater()
                    self.food_table_frame.layout().removeItem(row['layout'])
                
                self.food_rows.clear()
                
                # Add rows for each food item
                for food_item in food_items:
                    row = self.create_food_row()
                    
                    # Set values from loaded data
                    item_name = food_item.get('name', '')
                    item_price = food_item.get('price', '0')
                    
                    row['food_item'].setText(item_name)
                    row['price_input'].setText(str(item_price))
                    
                    # Add row to layout
                    self.food_table_frame.layout().addLayout(row['layout'])
                
                # If no food items were loaded, add an empty row
                if len(self.food_rows) == 0:
                    row = self.create_food_row()
                    self.food_table_frame.layout().addLayout(row['layout'])
                
                # Trigger UI update based on loaded menu type
                self.on_menu_option_changed()
                
                print(f"Settings loaded successfully. Current mode: {current_mode}")
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            # If there's an error, ensure we have at least one row for each table
            if len(self.time_rows) == 0:
                row = self.create_time_row()
                self.time_table_frame.layout().addLayout(row['layout'])
            if len(self.food_rows) == 0:
                row = self.create_food_row()
                self.food_table_frame.layout().addLayout(row['layout'])
    
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
            
            # Initialize mode configs if they don't exist
            if 'timeBased' not in settings['CanteenMenu']:
                settings['CanteenMenu'] = {
                    "DisablePunch": False,
                    "SpecialMessage": "",
                    "MealSchedule": []
                }
            if 'custom' not in settings['CanteenMenu']:
                settings['CanteenMenu']['custom'] = {
                    "DisablePunch": False,
                    "SpecialMessage": "",
                    "PunchInterval": "1",
                    "FoodItems": []
                }
            if 'device' not in settings['CanteenMenu']:
                settings['CanteenMenu']['device'] = {
                    "DisablePunch": False,
                    "SpecialMessage": ""
                }
            
            # Determine current mode based on selected radio button
            if self.time_based_radio.isChecked():
                current_mode = 'timeBased'
                mode_key = 'timeBased'
            elif self.custom_radio.isChecked():
                current_mode = 'custom'
                mode_key = 'custom'
            elif self.device_radio.isChecked():
                current_mode = 'device'
                mode_key = 'device'
            else:
                current_mode = 'timeBased'  # Default
                mode_key = 'timeBased'
            
            # Set current mode
            settings['CanteenMenu']['currentMode'] = current_mode
            
            # Update only the current mode's configuration
            if current_mode == 'timeBased':
                # Update time-based configuration
                settings['CanteenMenu']['DisablePunch'] = self.yes_no_btn.isChecked()
                settings['CanteenMenu']['SpecialMessage'] = self.special_msg_input.text()
                
                # Collect meal schedules
                meal_schedule = []
                for row in self.time_rows:
                    if row['meal_label'].text().strip():  # Only save non-empty meals
                        meal = {
                            'fromTime': row['from_time'].time().toString('HH:mm'),
                            'toTime': row['to_time'].time().toString('HH:mm'),
                            'mealType': row['meal_label'].text(),
                            'price': row['price_input'].text()
                        }
                        meal_schedule.append(meal)
                
                settings['CanteenMenu']['MealSchedule'] = meal_schedule
                
            elif current_mode == 'custom':
                # Update custom configuration
                settings['CanteenMenu']['custom']['DisablePunch'] = self.yes_no_btn.isChecked()
                settings['CanteenMenu']['custom']['SpecialMessage'] = self.special_msg_input.text()
                settings['CanteenMenu']['custom']['PunchInterval'] = self.punch_interval_input.text()
                
                # Collect food items
                food_items = []
                for row in self.food_rows:
                    if row['food_item'].text().strip():  # Only save non-empty items
                        food_item = {
                            'name': row['food_item'].text(),
                            'price': row['price_input'].text()
                        }
                        food_items.append(food_item)
                
                settings['CanteenMenu']['custom']['FoodItems'] = food_items
                
            elif current_mode == 'device':
                # Update device configuration
                settings['CanteenMenu']['device']['DisablePunch'] = self.yes_no_btn.isChecked()
                settings['CanteenMenu']['device']['SpecialMessage'] = self.special_msg_input.text()
            
            # Save to file
            with open('appSettings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            
            print(f"Settings saved successfully for {current_mode} mode")
            # print(f"Complete JSON structure:")
            # print(json.dumps(settings, indent=2))
            
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
        self.mail_window = MailSettingsWindow(self)
        self.mail_window.show()
    
    def get_reports(self):
        print("Get Reports button clicked")
        self.show_reports_view()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EzeeCanteenApp()
    window.show()
    sys.exit(app.exec_())