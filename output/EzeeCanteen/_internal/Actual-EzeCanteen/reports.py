import sys
import datetime
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QFrame, QMessageBox, QProgressBar, QSpacerItem, 
                             QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QMovie, QPainter
from PyQt5.QtWidgets import QGraphicsOpacityEffect
# Import report generation functions
from reportGen import generate_monthly_report, generate_daily_report, generate_logs_report, generate_timebase_monthly_report
# Import email functions
from AddMail import send_daily_report_email, send_monthly_report_email


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        
    def start(self):
        self.timer.start(50)  # Update every 50ms
        self.show()
        
    def stop(self):
        self.timer.stop()
        self.hide()
        
    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # First spinner (blue)
        painter.save()
        painter.translate(20, 20)
        painter.rotate(self.angle)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(94, 144, 250))
        painter.drawEllipse(-15, -15, 30, 30)
        painter.setBrush(QColor(94, 144, 250, 0))
        painter.drawEllipse(-12, -12, 24, 24)
        painter.restore()
        
        # Second spinner (green, reverse direction)
        painter.save()
        painter.translate(20, 20)
        painter.rotate(-self.angle)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(83, 255, 41))
        painter.drawEllipse(-15, -15, 30, 30)
        painter.setBrush(QColor(83, 255, 41, 0))
        painter.drawEllipse(-12, -12, 24, 24)
        painter.restore()


class WorkerThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args
        
    def run(self):
        try:
            # Define reports output directory
            output_dir = "reports"
            
            # Call the appropriate report generation function
            if self.operation == "send_mail":
                # Use the send_monthly_report_email function from AddMail.py
                month, year = self.args
                
                # Check if mail settings exist
                if not os.path.exists('appSettings.json'):
                    self.finished.emit(False, "Error: Mail settings not found. Please configure mail settings first.")
                    return
                
                # Load mail settings to check if they're properly configured
                with open('appSettings.json', 'r') as file:
                    all_settings = json.load(file)
                
                mail_settings = all_settings.get('MailSettings', {})
                
                # Check if mail settings are properly configured
                if not mail_settings or not mail_settings.get('SMTPServer') or not mail_settings.get('SMTPUser') or not mail_settings.get('ToEmails'):
                    self.finished.emit(False, "Error: Mail settings are incomplete. Please configure them properly.")
                    return
                
                # Send the email with monthly report
                result = send_monthly_report_email(year, month)
                
                if result:
                    success_msg = f"Monthly report for {datetime.datetime(year, month, 1).strftime('%B %Y')} sent successfully"
                    self.finished.emit(True, success_msg)
                else:
                    self.finished.emit(False, "Error: Failed to send email. Check mail settings and try again.")
                
            elif self.operation == "daily_report":
                # Get today's date
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                file_path = generate_daily_report(today, output_dir)
                result = file_path is not None
                success_msg = f"Daily report saved to {file_path}" if result else "Error: Daily report not generated"
                error_msg = "Error generating daily report"
            elif self.operation == "monthly_report":
                month, year = self.args
                # Generate three types of reports using generate_timebase_monthly_report
                device_report = generate_timebase_monthly_report(year, month, "deviceoptions", output_dir)
                time_report = generate_timebase_monthly_report(year, month, "timeoptions", output_dir)
                menu_report = generate_timebase_monthly_report(year, month, "menuoptions", output_dir)
                
                # Check if at least one report was generated successfully
                if device_report or time_report or menu_report:
                    result = True
                    success_reports = []
                    if device_report and time_report and menu_report:
                        success_reports.append(f"{menu_report}")
                    elif device_report and time_report:
                        success_reports.append(f"{device_report}")
                        success_reports.append(f"{time_report}")
                    elif device_report and menu_report:
                        success_reports.append(f"{device_report}")
                        success_reports.append(f"{menu_report}")
                    success_msg = f"Monthly reports saved: {', '.join(success_reports)}"
                else:
                    result = False
                    success_msg = "Error: Monthly reports not generated"
                error_msg = "Error generating monthly reports"
            elif self.operation == "canteen_log":
                month, year = self.args
                file_path = generate_logs_report(year, month, output_dir)
                result = file_path is not None
                success_msg = f"Canteen logs saved to {file_path}" if result else "Error: Canteen logs not generated"
                error_msg = "Error generating canteen logs"
            else:
                result = False
                success_msg = "Operation completed successfully"
                error_msg = "Unknown operation"
                
            if result:
                self.finished.emit(True, success_msg)
            else:
                self.finished.emit(False, error_msg)
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    def send_mail(self, month, year):
        # This is now handled directly in the run method
        pass


class ReportsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reports")
        self.setGeometry(100, 100, 800, 600)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1f2937;
                color: white;
            }
            QLabel {
                color: white;
                font-family: Arial, sans-serif;
                font-size: 15px;
            }
            QComboBox {
                background-color: #374151;
                color: white;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 5px;
                font-size: 16px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 16px;
            }
            .green-button {
                background-color: #15803d;
                color: white;
                padding: 8px 18px;
                font-size: 18px;
            }
            .green-button:hover {
                background-color: #166534;
            }
            .purple-button {
                background-color: #7c3aed;
                color: white;
            }
            .purple-button:hover {
                background-color: #6d28d9;
            }
            .yellow-button {
                background-color: #d97706;
                color: white;
            }
            .yellow-button:hover {
                background-color: #b45309;
            }
            QFrame {
                background-color: #111827;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        self.init_ui()
        self.worker_thread = None
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(16)
        
        # Page Title
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_label = QLabel("Reports")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 26, QFont.Bold))
        title_layout.addWidget(title_label)
        main_layout.addWidget(title_frame)
        
        # Menu Options Frame
        menu_frame = QFrame()
        menu_layout = QHBoxLayout(menu_frame)
        
        # Left side - Month/Year selection
        
        left_layout = QHBoxLayout()
        month_year_label = QLabel("Select Month and Year:")
        month_year_label.setStyleSheet("font-size: 16px;")
        left_layout.addWidget(month_year_label)

        left_layout.addWidget(QLabel(""))  # Spacer
        
        # Month combo box
        self.month_combo = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        for i, month in enumerate(months, 1):
            self.month_combo.addItem(month, i)
        left_layout.addWidget(self.month_combo)
        
        # Year combo box
        self.year_combo = QComboBox()
        current_year = datetime.datetime.now().year
        for year in range(current_year - 5, current_year + 1):
            self.year_combo.addItem(str(year), year)
        self.year_combo.setCurrentText(str(current_year))
        left_layout.addWidget(self.year_combo)
        
        menu_layout.addLayout(left_layout)
        menu_layout.addStretch()
        
        # Right side - Send Mail button
        self.send_mail_btn = QPushButton("Send Mail")
        self.send_mail_btn.setProperty("class", "purple-button")
        self.send_mail_btn.clicked.connect(self.send_mail)
        menu_layout.addWidget(self.send_mail_btn)
        
        main_layout.addWidget(menu_frame)
        
        # Download Reports Section
        reports_frame = QFrame()
        reports_layout = QVBoxLayout(reports_frame)
        reports_layout.setSpacing(24)
        
        # Monthly Report
        monthly_frame = QFrame()
        monthly_frame.setStyleSheet("QFrame { background-color: #1f2937; }")
        monthly_layout = QHBoxLayout(monthly_frame)
        monthly_label = QLabel("Monthly Report")
        monthly_label.setStyleSheet("font-size: 16px;")
        monthly_layout.addWidget(monthly_label)
        monthly_layout.addStretch()
        monthly_btn = QPushButton("get")
        monthly_btn.setProperty("class", "green-button")
        monthly_btn.clicked.connect(self.monthly_consumption)
        monthly_layout.addWidget(monthly_btn)
        reports_layout.addWidget(monthly_frame)
        
        # Daily Consumption Report
        daily_frame = QFrame()
        daily_frame.setStyleSheet("QFrame { background-color: #1f2937; }")
        daily_layout = QHBoxLayout(daily_frame)
        daily_label = QLabel("Daily Consumption Report")
        daily_label.setStyleSheet("font-size: 16px;")
        daily_layout.addWidget(daily_label)
        daily_layout.addStretch()
        daily_btn = QPushButton("get")
        daily_btn.setProperty("class", "green-button")
        daily_btn.clicked.connect(self.daily_consumption)
        daily_layout.addWidget(daily_btn)
        reports_layout.addWidget(daily_frame)
        
        # Canteen Logs
        canteen_frame = QFrame()
        canteen_frame.setStyleSheet("QFrame { background-color: #1f2937; }")
        canteen_layout = QHBoxLayout(canteen_frame)
        canteen_label = QLabel("Canteen Logs")
        canteen_label.setStyleSheet("font-size: 16px;")
        canteen_layout.addWidget(canteen_label)
        canteen_layout.addStretch()
        canteen_btn = QPushButton("get")
        canteen_btn.setProperty("class", "green-button")
        canteen_btn.clicked.connect(self.canteen_log)
        canteen_layout.addWidget(canteen_btn)
        reports_layout.addWidget(canteen_frame)
        
        main_layout.addWidget(reports_frame)
        
        # Message and Button Container
        bottom_layout = QHBoxLayout()
        
        # Left side - Message area
        message_layout = QHBoxLayout()
        self.spinner = LoadingSpinner()
        self.spinner.hide()
        message_layout.addWidget(self.spinner)
        
        self.loading_label = QLabel("Processing, please wait...")
        self.loading_label.hide()
        self.loading_label.setStyleSheet("font-size: 16px;")
        message_layout.addWidget(self.loading_label)
        
        self.message_label = QLabel("")
        self.message_label.hide()
        message_layout.addWidget(self.message_label)
        message_layout.addStretch()
        
        bottom_layout.addLayout(message_layout)
        bottom_layout.addStretch()
        
        # Right side - Back button
        back_btn = QPushButton("Back")
        back_btn.setProperty("class", "yellow-button")
        back_btn.clicked.connect(self.go_back)
        bottom_layout.addWidget(back_btn)
        
        main_layout.addLayout(bottom_layout)
        
        # Footer
        main_layout.addStretch()
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #9ca3af; font-size: 18px; margin-top: 80px;")
        main_layout.addWidget(footer_label)
        
        # Apply custom styles
        self.apply_styles()
        
    def apply_styles(self):
        # Apply button styles
        for button in self.findChildren(QPushButton):
            class_name = button.property("class")
            if class_name == "green-button":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #15803d;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 12px 12px;
                        
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #166534;
                    }
                """)
            elif class_name == "purple-button":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #7c3aed;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #6d28d9;
                    }
                """)
            elif class_name == "yellow-button":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #d97706;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #b45309;
                    }
                """)
    
    def show_loading(self):
        self.message_label.hide()
        self.spinner.start()
        self.loading_label.show()
        
    def hide_loading(self):
        self.spinner.stop()
        self.loading_label.hide()
        
    def display_message(self, is_success, message):
        self.hide_loading()
        self.message_label.setText(message)
        
        if is_success:
            self.message_label.setStyleSheet("color: #4ade80; font-size: 18px; font-weight: bold;")
        else:
            self.message_label.setStyleSheet("color: #f87171; font-size: 18px; font-weight: bold;")
        
        self.message_label.show()
        
        # Hide message after 5 seconds
        QTimer.singleShot(5000, self.message_label.hide)
    
    def send_mail(self):
        # Check if mail settings are configured
        if not os.path.exists('appSettings.json'):
            QMessageBox.warning(self, "Mail Settings Missing", 
                              "Mail settings not found. Please configure mail settings first.")
            return
            
        # Load mail settings to check if they're properly configured
        try:
            with open('appSettings.json', 'r') as file:
                all_settings = json.load(file)
            
            mail_settings = all_settings.get('MailSettings', {})
            
            # Check if mail settings are properly configured
            if not mail_settings or not mail_settings.get('SMTPServer') or not mail_settings.get('SMTPUser') or not mail_settings.get('ToEmails'):
                QMessageBox.warning(self, "Incomplete Mail Settings", 
                                  "Mail settings are incomplete. Please configure them properly.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading mail settings: {str(e)}")
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(self, 'Confirm', f'Are you sure you want to send the monthly report for {self.month_combo.currentText()} {self.year_combo.currentText()}?',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading()
        self.worker_thread = WorkerThread("send_mail", month, year)
        self.worker_thread.finished.connect(self.display_message)
        self.worker_thread.start()
    
    def daily_consumption(self):
        self.show_loading()
        self.worker_thread = WorkerThread("daily_report")
        self.worker_thread.finished.connect(self.display_message)
        self.worker_thread.start()
    
    def monthly_consumption(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading()
        self.worker_thread = WorkerThread("monthly_report", month, year)
        self.worker_thread.finished.connect(self.display_message)
        self.worker_thread.start()
    
    def canteen_log(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading()
        self.worker_thread = WorkerThread("canteen_log", month, year)
        self.worker_thread.finished.connect(self.display_message)
        self.worker_thread.start()
    
    def go_back(self):
        # Close this window and show the parent window again
        print("Going back to canteen settings...")
        self.close()
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.show()
    
    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        event.accept()


# Add ReportsWidget class that extends ReportsWindow for compatibility with CanteenSettings
class ReportsWidget(ReportsWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        
    def go_back(self):
        # For ReportsWidget, go back means returning to canteen settings view
        if self.parent_window:
            self.parent_window.show_settings_view()
        else:
            # Fall back to original implementation if no parent
            super().go_back()


def main():
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = ReportsWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()