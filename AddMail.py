import sys
import json
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, 
                             QCheckBox, QTimeEdit, QGroupBox, QFormLayout, QMessageBox,
                             QSpinBox, QFrame)
from PyQt5.QtCore import Qt, QTime, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import os
from encryMail import encrypt_password, decrypt_password
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
import reportGen

def send_daily_report_email(date=None):
    """
    Send an email with the daily report attachment
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. If None, today's date will be used.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Use today's date if not specified
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Load mail settings
        if not os.path.exists('appSettings.json'):
            print("Mail settings not found")
            return False
            
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
            
        mail_settings = all_settings.get('MailSettings', {})
        if not mail_settings:
            print("Mail settings not configured")
            return False
            
        # Get mail settings
        smtp_server = mail_settings.get('SMTPServer')
        smtp_port = mail_settings.get('SMTPPort')
        smtp_user = mail_settings.get('SMTPUser')
        smtp_pass = decrypt_password(mail_settings.get('SMTPPass', ''))
        use_ssl_tls = mail_settings.get('SSLTLS', False)
        to_emails = mail_settings.get('ToEmails', [])
        subject = mail_settings.get('MailSubject', 'Daily Canteen Report')
        body = mail_settings.get('MailBody', 'Please find attached the daily canteen consumption report.')
        
        if not smtp_server or not smtp_port or not smtp_user or not smtp_pass or not to_emails:
            print("Incomplete mail settings")
            return False
            
        # Generate daily report
        report_path = reportGen.generate_daily_report(date)
        if not report_path or not os.path.exists(report_path):
            print(f"Failed to generate report for {date}")
            return False
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body))
        
        # Attach report file
        with open(report_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), Name=os.path.basename(report_path))
            attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_path)}"'
            msg.attach(attachment)
        
        # Connect to SMTP server and send email with better error handling
        smtp = None
        try:
            # Try different connection methods based on port and settings
            if use_ssl_tls:
                print(f"Attempting SSL connection to {smtp_server}:{smtp_port}")
                try:
                    # Try direct SSL connection
                    smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
                except Exception as ssl_error:
                    print(f"SSL connection failed: {ssl_error}")
                    print("Trying standard connection with STARTTLS...")
                    # Fall back to standard + STARTTLS
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
            else:
                # Standard connection
                print(f"Attempting standard connection to {smtp_server}:{smtp_port}")
                smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                # Check if STARTTLS is supported
                try:
                    smtp.ehlo()
                    if smtp.has_extn('STARTTLS'):
                        print("Server supports STARTTLS, enabling...")
                        smtp.starttls()
                        smtp.ehlo()
                except Exception as tls_error:
                    print(f"STARTTLS failed: {tls_error}")
                    print("Continuing without TLS...")
                
            # Login and send
            print(f"Logging in as {smtp_user}...")
            smtp.login(smtp_user, smtp_pass)
            print("Sending email...")
            smtp.sendmail(smtp_user, to_emails, msg.as_string())
            smtp.close()
            
            print(f"Email sent successfully with report for {date}")
            return True
            
        except Exception as conn_error:
            print(f"Connection error: {conn_error}")
            # Try alternative connection method if first method fails
            if smtp:
                try:
                    smtp.close()
                except:
                    pass
                    
            # If we failed with SSL, try without it
            if use_ssl_tls:
                print("Trying non-SSL connection as fallback...")
                try:
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    try:
                        smtp.starttls()
                        smtp.ehlo()
                    except:
                        print("STARTTLS failed, continuing without encryption")
                    smtp.login(smtp_user, smtp_pass)
                    smtp.sendmail(smtp_user, to_emails, msg.as_string())
                    smtp.close()
                    print(f"Email sent successfully with non-SSL connection")
                    return True
                except Exception as fallback_error:
                    print(f"Fallback connection also failed: {fallback_error}")
                    return False
            return False
            
    except Exception as e:
        print(f"Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_monthly_report_email(year=None, month=None):
    """
    Send an email with the monthly report attachment
    
    Args:
        year (int, optional): Year for the report. If None, current year will be used.
        month (int, optional): Month for the report (1-12). If None, current month will be used.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Use current year/month if not specified
        if year is None or month is None:
            current_date = datetime.now()
            year = year or current_date.year
            month = month or current_date.month
        
        # Load mail settings
        if not os.path.exists('appSettings.json'):
            print("Mail settings not found")
            return False
            
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
            
        mail_settings = all_settings.get('MailSettings', {})
        if not mail_settings:
            print("Mail settings not configured")
            return False
            
        # Get mail settings
        smtp_server = mail_settings.get('SMTPServer')
        smtp_port = mail_settings.get('SMTPPort')
        smtp_user = mail_settings.get('SMTPUser')
        smtp_pass = decrypt_password(mail_settings.get('SMTPPass', ''))
        use_ssl_tls = mail_settings.get('SSLTLS', False)
        to_emails = mail_settings.get('ToEmails', [])
        
        # Customize subject and body for monthly report
        month_name = datetime(year, month, 1).strftime('%B')
        subject = mail_settings.get('MailSubject', f'Monthly Canteen Report - {month_name} {year}')
        body = mail_settings.get('MailBody', f'Please find attached the monthly canteen consumption report for {month_name} {year}.')
        
        if not smtp_server or not smtp_port or not smtp_user or not smtp_pass or not to_emails:
            print("Incomplete mail settings")
            return False
            
        # Generate monthly report using timebase format
        report_path = reportGen.generate_timebase_monthly_report(year, month, "deviceoptions", output_dir="Reports/monthly", prompt_for_location=False)
        if not report_path or not os.path.exists(report_path):
            print(f"Failed to generate report for {month}/{year}")
            return False
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body))
        
        # Attach report file
        with open(report_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), Name=os.path.basename(report_path))
            attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_path)}"'
            msg.attach(attachment)
        
        # Connect to SMTP server and send email with better error handling
        smtp = None
        try:
            # Try different connection methods based on port and settings
            if use_ssl_tls:
                print(f"Attempting SSL connection to {smtp_server}:{smtp_port}")
                try:
                    # Try direct SSL connection
                    smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
                except Exception as ssl_error:
                    print(f"SSL connection failed: {ssl_error}")
                    print("Trying standard connection with STARTTLS...")
                    # Fall back to standard + STARTTLS
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
            else:
                # Standard connection
                print(f"Attempting standard connection to {smtp_server}:{smtp_port}")
                smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                # Check if STARTTLS is supported
                try:
                    smtp.ehlo()
                    if smtp.has_extn('STARTTLS'):
                        print("Server supports STARTTLS, enabling...")
                        smtp.starttls()
                        smtp.ehlo()
                except Exception as tls_error:
                    print(f"STARTTLS failed: {tls_error}")
                    print("Continuing without TLS...")
                
            # Login and send
            print(f"Logging in as {smtp_user}...")
            smtp.login(smtp_user, smtp_pass)
            print("Sending email...")
            smtp.sendmail(smtp_user, to_emails, msg.as_string())
            smtp.close()
            
            print(f"Email sent successfully with monthly report for {month}/{year}")
            return True
            
        except Exception as conn_error:
            print(f"Connection error: {conn_error}")
            # Try alternative connection method if first method fails
            if smtp:
                try:
                    smtp.close()
                except:
                    pass
                    
            # If we failed with SSL, try without it
            if use_ssl_tls:
                print("Trying non-SSL connection as fallback...")
                try:
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    try:
                        smtp.starttls()
                        smtp.ehlo()
                    except:
                        print("STARTTLS failed, continuing without encryption")
                    smtp.login(smtp_user, smtp_pass)
                    smtp.sendmail(smtp_user, to_emails, msg.as_string())
                    smtp.close()
                    print(f"Email sent successfully with non-SSL connection")
                    return True
                except Exception as fallback_error:
                    print(f"Fallback connection also failed: {fallback_error}")
                    return False
            return False
        
    except Exception as e:
        print(f"Error sending monthly report email: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_and_send_scheduled_email():
    """
    Check if it's time to send scheduled email and send if needed
    This function is meant to be called periodically by a scheduler
    
    Returns:
        bool: True if email was sent or not needed, False if error
    """
    try:
        # Load mail settings
        if not os.path.exists('appSettings.json'):
            print("Mail settings not found")
            return False
            
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
            
        mail_settings = all_settings.get('MailSettings', {})
        if not mail_settings:
            print("Mail settings not configured")
            return False
        
        # Check if auto mail is enabled
        auto_mail_enabled = mail_settings.get('AutoMail', False)
        if not auto_mail_enabled:
            # No need to send email if auto mail is disabled
            return True
            
        # Get scheduled time
        scheduled_time_str = mail_settings.get('AutoMailTime', '09:00')
        scheduled_time = datetime.strptime(scheduled_time_str, '%H:%M').time()
        
        # Get current time
        current_time = datetime.now().time()
        
        # Check if the current hour and minute match the scheduled time
        if current_time.hour == scheduled_time.hour and current_time.minute == scheduled_time.minute:
            # It's time to send the email
            # Get yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            
            # Check if we already sent today's email
            last_sent_file = 'last_sent_email.txt'
            if os.path.exists(last_sent_file):
                with open(last_sent_file, 'r') as f:
                    last_sent = f.read().strip()
                if last_sent == datetime.now().strftime('%Y-%m-%d'):
                    # Already sent today
                    return True
            
            # Send the combined reports email
            result = send_combined_reports_email(yesterday_str)
            
            if result:
                # Update last sent date with today's date
                with open(last_sent_file, 'w') as f:
                    f.write(datetime.now().strftime('%Y-%m-%d'))
                
                print(f"Scheduled email sent with combined reports for {yesterday_str}")
                return True
            else:
                print(f"Failed to send scheduled email with combined reports for {yesterday_str}")
                return False
        
        # Not time to send yet
        return True
        
    except Exception as e:
        print(f"Error in scheduled email check: {e}")
        return False

def send_combined_reports_email(date=None):
    """
    Send an email with multiple report attachments: daily report, monthly device/time/menu reports, and canteen logs
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format for daily report. If None, yesterday's date will be used.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Use yesterday's date if not specified
        if date is None:
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")
        
        # Get current year and month for monthly reports
        current_date = datetime.strptime(date, "%Y-%m-%d")
        year = current_date.year
        month = current_date.month
        
        # Load mail settings
        if not os.path.exists('appSettings.json'):
            print("Mail settings not found")
            return False
            
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
            
        mail_settings = all_settings.get('MailSettings', {})
        if not mail_settings:
            print("Mail settings not configured")
            return False
            
        # Get mail settings
        smtp_server = mail_settings.get('SMTPServer')
        smtp_port = mail_settings.get('SMTPPort')
        smtp_user = mail_settings.get('SMTPUser')
        smtp_pass = decrypt_password(mail_settings.get('SMTPPass', ''))
        use_ssl_tls = mail_settings.get('SSLTLS', False)
        to_emails = mail_settings.get('ToEmails', [])
        subject = mail_settings.get('MailSubject', f'EzeeCanteen Reports for {date}')
        body = mail_settings.get('MailBody', f'Please find attached the following EzeeCanteen reports for {date}:\n\n1. Daily Consumption Report\n2. Device-based Monthly Report\n3. Time-based Monthly Report\n4. Menu-based Monthly Report\n5. Canteen Logs')
        
        if not smtp_server or not smtp_port or not smtp_user or not smtp_pass or not to_emails:
            print("Incomplete mail settings")
            return False
        
        # Generate all reports
        report_paths = []
        
        # 1. Generate daily report
        daily_report_path = reportGen.generate_daily_report(date)
        if daily_report_path and os.path.exists(daily_report_path):
            report_paths.append(daily_report_path)
        else:
            print(f"Failed to generate daily report for {date}")
        
        # 2. Generate device-based monthly report
        device_report_path = reportGen.generate_timebase_monthly_report(year, month, "deviceoptions", output_dir="Reports/monthly", prompt_for_location=False)
        if device_report_path and os.path.exists(device_report_path):
            report_paths.append(device_report_path)
        else:
            print(f"Failed to generate device-based report for {month}/{year}")
        
        # 3. Generate time-based monthly report
        time_report_path = reportGen.generate_timebase_monthly_report(year, month, "timeoptions", output_dir="Reports/monthly", prompt_for_location=False)
        if time_report_path and os.path.exists(time_report_path):
            report_paths.append(time_report_path)
        else:
            print(f"Failed to generate time-based report for {month}/{year}")
        
        # 4. Generate menu-based monthly report
        menu_report_path = reportGen.generate_timebase_monthly_report(year, month, "menuoptions", output_dir="Reports/monthly", prompt_for_location=False)
        if menu_report_path and os.path.exists(menu_report_path):
            report_paths.append(menu_report_path)
        else:
            print(f"Failed to generate menu-based report for {month}/{year}")
        
        # 5. Generate canteen logs report
        logs_report_path = reportGen.generate_logs_report(year, month)
        if logs_report_path and os.path.exists(logs_report_path):
            report_paths.append(logs_report_path)
        else:
            print(f"Failed to generate logs report for {month}/{year}")
        
        # Check if we have at least one report to send
        if not report_paths:
            print("No reports were successfully generated")
            return False
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body))
        
        # Attach all report files
        for report_path in report_paths:
            with open(report_path, 'rb') as file:
                attachment = MIMEApplication(file.read(), Name=os.path.basename(report_path))
                attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_path)}"'
                msg.attach(attachment)
        
        # Connect to SMTP server and send email with better error handling
        smtp = None
        try:
            # Try different connection methods based on port and settings
            if use_ssl_tls:
                print(f"Attempting SSL connection to {smtp_server}:{smtp_port}")
                try:
                    # Try direct SSL connection
                    smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
                except Exception as ssl_error:
                    print(f"SSL connection failed: {ssl_error}")
                    print("Trying standard connection with STARTTLS...")
                    # Fall back to standard + STARTTLS
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
            else:
                # Standard connection
                print(f"Attempting standard connection to {smtp_server}:{smtp_port}")
                smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                # Check if STARTTLS is supported
                try:
                    smtp.ehlo()
                    if smtp.has_extn('STARTTLS'):
                        print("Server supports STARTTLS, enabling...")
                        smtp.starttls()
                        smtp.ehlo()
                except Exception as tls_error:
                    print(f"STARTTLS failed: {tls_error}")
                    print("Continuing without TLS...")
                
            # Login and send
            print(f"Logging in as {smtp_user}...")
            smtp.login(smtp_user, smtp_pass)
            print("Sending email...")
            smtp.sendmail(smtp_user, to_emails, msg.as_string())
            smtp.close()
            
            print(f"Email sent successfully with {len(report_paths)} reports for {date}")
            return True
            
        except Exception as conn_error:
            print(f"Connection error: {conn_error}")
            # Try alternative connection method if first method fails
            if smtp:
                try:
                    smtp.close()
                except:
                    pass
                    
            # If we failed with SSL, try without it
            if use_ssl_tls:
                print("Trying non-SSL connection as fallback...")
                try:
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    smtp.ehlo()
                    try:
                        smtp.starttls()
                        smtp.ehlo()
                    except:
                        print("STARTTLS failed, continuing without encryption")
                    smtp.login(smtp_user, smtp_pass)
                    smtp.sendmail(smtp_user, to_emails, msg.as_string())
                    smtp.close()
                    print(f"Email sent successfully with non-SSL connection")
                    return True
                except Exception as fallback_error:
                    print(f"Fallback connection also failed: {fallback_error}")
                    return False
            return False
            
    except Exception as e:
        print(f"Error sending combined reports email: {e}")
        import traceback
        traceback.print_exc()
        return False

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 32)
        self._checked = False
        self.setStyleSheet("""
            QWidget {
                background-color: #EF4444;
                border-radius: 16px;
                border: none;
            }
        """)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt5.QtGui import QPainter, QBrush
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        bg_color = QColor("#10B981") if self._checked else QColor("#EF4444")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
        
        # Draw circle
        circle_x = 28 if self._checked else 4
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(circle_x, 4, 24, 24)
        
        # Draw text
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        
        if self._checked:
            painter.drawText(8, 20, "Yes")
        else:
            painter.drawText(40, 20, "No")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
    
    def toggle(self):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()
    
    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.update()
    
    def isChecked(self):
        return self._checked

class MailSettingsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("EzeeCanteen - Mail Settings")
        self.setGeometry(100, 100, 800, 900)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1F2937;
                color: white;
            }
            QGroupBox {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QLineEdit, QTextEdit, QSpinBox {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border-color: #3B82F6;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#backButton {
                background-color: #D97706;
                color: white;
                border: none;
            }
            QPushButton#backButton:hover {
                background-color: #92400E;
            }
            QPushButton#saveButton {
                background-color: #059669;
                color: white;
                border: none;
            }
            QPushButton#saveButton:hover {
                background-color: #047857;
            }
            QPushButton#testButton {
                background-color: #3B82F6;
                color: white;
                border: none;
            }
            QPushButton#testButton:hover {
                background-color: #2563EB;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border-color: #3B82F6;
            }
            QTimeEdit {
                background-color: #374151;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
        """)
        
        self.init_ui()
        self.load_mail_settings()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("Mail Settings")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                background-color: #111827;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # SMTP Settings Group
        smtp_group = QGroupBox("SMTP Settings")
        smtp_layout = QFormLayout()
        
        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("Enter SMTP server address")
        smtp_layout.addRow("SMTP Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(0, 65535)
        self.smtp_port.setValue(587)  # Default SMTP port
        smtp_layout.addRow("SMTP Port:", self.smtp_port)
        
        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("Enter SMTP username (email address)")
        smtp_layout.addRow("SMTP Username (Email):", self.smtp_user)
        
        # Password field with show/hide toggle
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(10)
        
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_pass.setPlaceholderText("Enter SMTP password")
        password_layout.addWidget(self.smtp_pass)
        
        self.show_password_button = QPushButton("Show")
        self.show_password_button.setObjectName("showPasswordButton")
        self.show_password_button.setFixedWidth(60)
        self.show_password_button.setStyleSheet("""
            QPushButton#showPasswordButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 5px;
            }
            QPushButton#showPasswordButton:hover {
                background-color: #2563EB;
            }
        """)
        self.show_password_button.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_button)
        
        smtp_layout.addRow("SMTP Password:", password_container)
        
        self.ssl_tls = QCheckBox("Use SSL/TLS")
        smtp_layout.addRow("", self.ssl_tls)
        
        smtp_group.setLayout(smtp_layout)
        main_layout.addWidget(smtp_group)
        
        # MailBox Settings Group
        mailbox_group = QGroupBox("MailBox Settings")
        mailbox_layout = QFormLayout()
        
        self.to_emails = QTextEdit()
        self.to_emails.setPlaceholderText("Enter to email addresses, separated by commas eg - abcd@gmail.com, xyzk@yahoo.com, qwerty@outlook.com")
        self.to_emails.setMaximumHeight(80)
        mailbox_layout.addRow("To Email Addresses:", self.to_emails)
        
        self.mail_subject = QLineEdit()
        self.mail_subject.setPlaceholderText("Enter mail subject")
        mailbox_layout.addRow("Mail Subject:", self.mail_subject)
        
        self.mail_body = QTextEdit()
        self.mail_body.setPlaceholderText("Enter mail body")
        self.mail_body.setMaximumHeight(120)
        mailbox_layout.addRow("Mail Body:", self.mail_body)
        
        mailbox_group.setLayout(mailbox_layout)
        main_layout.addWidget(mailbox_group)
        
        # Schedule Auto Mail Group
        auto_mail_group = QGroupBox("Schedule Auto Mail")
        auto_mail_layout = QVBoxLayout()
        
        # Toggle section
        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("Schedule Auto Mail")
        toggle_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #D1D5DB;")
        
        self.auto_mail_toggle = ToggleSwitch()
        self.auto_mail_toggle.toggled.connect(self.toggle_auto_mail)
        
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.auto_mail_toggle)
        
        auto_mail_layout.addLayout(toggle_layout)
        
        # Time input section
        self.auto_mail_time_frame = QFrame()
        time_layout = QFormLayout()
        
        self.auto_mail_time = QTimeEdit()
        self.auto_mail_time.setDisplayFormat("HH:mm")
        time_layout.addRow("Auto Mail Time:", self.auto_mail_time)
        
        self.auto_mail_time_frame.setLayout(time_layout)
        self.auto_mail_time_frame.hide()
        
        auto_mail_layout.addWidget(self.auto_mail_time_frame)
        auto_mail_group.setLayout(auto_mail_layout)
        main_layout.addWidget(auto_mail_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        back_button = QPushButton("Back")
        back_button.setObjectName("backButton")
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)
        
        test_button = QPushButton("Test Email")
        test_button.setObjectName("testButton")
        test_button.clicked.connect(self.send_test_email)
        button_layout.addWidget(test_button)
        
        save_button = QPushButton("Save")
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self.save_mail_settings)
        button_layout.addWidget(save_button)
        
        main_layout.addLayout(button_layout)
        
        # Footer
        footer_label = QLabel("Developed by PayGURU Technosoft Pvt. Ltd.")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 16px;
                margin-top: 40px;
            }
        """)
        main_layout.addWidget(footer_label)
    
    def toggle_auto_mail(self, checked):
        if checked:
            self.auto_mail_time_frame.show()
        else:
            self.auto_mail_time_frame.hide()
    
    def toggle_password_visibility(self):
        """Toggle between showing and hiding the password"""
        if self.smtp_pass.echoMode() == QLineEdit.Password:
            self.smtp_pass.setEchoMode(QLineEdit.Normal)
            self.show_password_button.setText("Hide")
        else:
            self.smtp_pass.setEchoMode(QLineEdit.Password)
            self.show_password_button.setText("Show")
    
    def validate_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    def load_mail_settings(self):
        """Load mail settings from appSettings.json"""
        try:
            if os.path.exists('appSettings.json'):
                with open('appSettings.json', 'r') as file:
                    all_settings = json.load(file)
                    
                    mail_settings = all_settings.get('MailSettings', {})
                    
                    self.to_emails.setText(', '.join(mail_settings.get('ToEmails', [])))
                    self.smtp_server.setText(mail_settings.get('SMTPServer', ''))
                    self.smtp_port.setValue(mail_settings.get('SMTPPort', 587))
                    self.smtp_user.setText(mail_settings.get('SMTPUser', ''))
                    
                    # Decrypt and show the saved password
                    encrypted_password = mail_settings.get('SMTPPass', '')
                    decrypted_password = decrypt_password(encrypted_password)
                    self.smtp_pass.setText(decrypted_password)
                    
                    self.ssl_tls.setChecked(mail_settings.get('SSLTLS', False))
                    self.auto_mail_toggle.setChecked(mail_settings.get('AutoMail', False))
                    
                    time_str = mail_settings.get('AutoMailTime', '09:00')
                    time_obj = QTime.fromString(time_str, 'HH:mm')
                    self.auto_mail_time.setTime(time_obj)
                    
                    self.mail_subject.setText(mail_settings.get('MailSubject', ''))
                    self.mail_body.setText(mail_settings.get('MailBody', ''))
                    
                    self.toggle_auto_mail(mail_settings.get('AutoMail', False))
            else:
                # Default values if file doesn't exist
                default_settings = {
                    'ToEmails': ['example@gmail.com'],
                    'SMTPServer': 'smtp.gmail.com',
                    'SMTPPort': 587,
                    'SMTPUser': 'your_email@gmail.com',
                    'SMTPPass': '',
                    'SSLTLS': True,
                    'AutoMail': False,
                    'AutoMailTime': '09:00',
                    'MailSubject': 'Daily Report',
                    'MailBody': 'This is the daily report.'
                }
                
                self.to_emails.setText(', '.join(default_settings.get('ToEmails', [])))
                self.smtp_server.setText(default_settings.get('SMTPServer', ''))
                self.smtp_port.setValue(default_settings.get('SMTPPort', 587))
                self.smtp_user.setText(default_settings.get('SMTPUser', ''))
                self.smtp_pass.setText(default_settings.get('SMTPPass', ''))
                self.ssl_tls.setChecked(default_settings.get('SSLTLS', False))
                self.auto_mail_toggle.setChecked(default_settings.get('AutoMail', False))
                
                time_str = default_settings.get('AutoMailTime', '09:00')
                time_obj = QTime.fromString(time_str, 'HH:mm')
                self.auto_mail_time.setTime(time_obj)
                
                self.mail_subject.setText(default_settings.get('MailSubject', ''))
                self.mail_body.setText(default_settings.get('MailBody', ''))
                
                self.toggle_auto_mail(default_settings.get('AutoMail', False))
                
        except Exception as e:
            print(f"Error loading mail settings: {e}")
    
    def save_mail_settings(self):
        """Save mail settings to appSettings.json"""
        # Validate email addresses
        to_emails_text = self.to_emails.toPlainText()
        email_list = [email.strip() for email in to_emails_text.split(',') if email.strip()]
        
        valid = True
        for email in email_list:
            if not self.validate_email(email):
                valid = False
                break
        
        # Validate SMTP user email
        if not self.validate_email(self.smtp_user.text()):
            valid = False
        
        # Validate auto mail time if enabled
        if self.auto_mail_toggle.isChecked() and not self.auto_mail_time.time().isValid():
            valid = False
        
        if not valid:
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter valid email addresses and SMTP settings.")
            return
        
        # Encrypt the password
        password = self.smtp_pass.text()
        encrypted_password = encrypt_password(password) if password else ""
        
        # Collect mail settings
        mail_settings = {
            'ToEmails': email_list,
            'SMTPServer': self.smtp_server.text().strip(),
            'SMTPPort': self.smtp_port.value(),
            'SMTPUser': self.smtp_user.text(),
            'SMTPPass': encrypted_password,
            'SSLTLS': self.ssl_tls.isChecked(),
            'AutoMail': self.auto_mail_toggle.isChecked(),
            'AutoMailTime': self.auto_mail_time.time().toString('HH:mm'),
            'MailSubject': self.mail_subject.text(),
            'MailBody': self.mail_body.toPlainText()
        }
        
        try:
            # Load existing settings if file exists
            all_settings = {}
            if os.path.exists('appSettings.json'):
                with open('appSettings.json', 'r') as file:
                    all_settings = json.load(file)
            
            # Add or update mail settings
            all_settings['MailSettings'] = mail_settings
            
            # Save to file
            with open('appSettings.json', 'w') as file:
                json.dump(all_settings, file, indent=4)
            
            QMessageBox.information(self, "Success", "Mail settings saved successfully.")
            self.go_back()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: Mail settings not saved.\n{str(e)}")
    
    def send_test_email(self):
        """Send a test email with the current settings"""
        # First save the current settings
        to_emails_text = self.to_emails.toPlainText()
        email_list = [email.strip() for email in to_emails_text.split(',') if email.strip()]
        
        valid = True
        for email in email_list:
            if not self.validate_email(email):
                valid = False
                break
        
        # Validate SMTP user email
        if not self.validate_email(self.smtp_user.text()):
            valid = False
        
        if not valid:
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter valid email addresses and SMTP settings.")
            return
        
        try:
            # Create a temporary settings dict
            temp_settings = {
                'MailSettings': {
                    'ToEmails': email_list,
                    'SMTPServer': self.smtp_server.text().strip(),
                    'SMTPPort': self.smtp_port.value(),
                    'SMTPUser': self.smtp_user.text(),
                    'SMTPPass': encrypt_password(self.smtp_pass.text()) if self.smtp_pass.text() else "",
                    'SSLTLS': self.ssl_tls.isChecked(),
                    'MailSubject': "Test Email from EzeeCanteen",
                    'MailBody': "This is a test email to verify your mail settings."
                }
            }
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user.text()
            msg['To'] = ', '.join(email_list)
            msg['Subject'] = "Test Email from EzeeCanteen"
            
            # Attach body
            body = "This is a test email to verify your mail settings.\n\n"
            body += "If you received this email, your mail settings are configured correctly."
            msg.attach(MIMEText(body))
            
            # Connect to SMTP server with improved error handling
            smtp_server = self.smtp_server.text().strip()
            smtp_port = self.smtp_port.value()
            smtp_user = self.smtp_user.text()
            smtp_pass = self.smtp_pass.text()
            use_ssl_tls = self.ssl_tls.isChecked()
            
            # Connect to SMTP server and send email with better error handling
            smtp = None
            try:
                # Try different connection methods based on port and settings
                if use_ssl_tls:
                    print(f"Attempting SSL connection to {smtp_server}:{smtp_port}")
                    try:
                        # Try direct SSL connection
                        smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
                    except Exception as ssl_error:
                        print(f"SSL connection failed: {ssl_error}")
                        print("Trying standard connection with STARTTLS...")
                        # Fall back to standard + STARTTLS
                        smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()
                else:
                    # Standard connection
                    print(f"Attempting standard connection to {smtp_server}:{smtp_port}")
                    smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                    # Check if STARTTLS is supported
                    try:
                        smtp.ehlo()
                        if smtp.has_extn('STARTTLS'):
                            print("Server supports STARTTLS, enabling...")
                            smtp.starttls()
                            smtp.ehlo()
                    except Exception as tls_error:
                        print(f"STARTTLS failed: {tls_error}")
                        print("Continuing without TLS...")
                
                # Login and send
                print(f"Logging in as {smtp_user}...")
                smtp.login(smtp_user, smtp_pass)
                print("Sending test email...")
                smtp.sendmail(smtp_user, email_list, msg.as_string())
                smtp.close()
                
                QMessageBox.information(self, "Success", "Test email sent successfully!")
                
            except Exception as conn_error:
                print(f"Connection error: {conn_error}")
                # Try alternative connection method if first method fails
                if smtp:
                    try:
                        smtp.close()
                    except:
                        pass
                        
                # If we failed with SSL, try without it
                if use_ssl_tls:
                    print("Trying non-SSL connection as fallback...")
                    try:
                        smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                        smtp.ehlo()
                        try:
                            smtp.starttls()
                            smtp.ehlo()
                        except:
                            print("STARTTLS failed, continuing without encryption")
                        smtp.login(smtp_user, smtp_pass)
                        smtp.sendmail(smtp_user, email_list, msg.as_string())
                        smtp.close()
                        print(f"Email sent successfully with non-SSL connection")
                        QMessageBox.information(self, "Success", "Test email sent successfully using fallback connection!")
                    except Exception as fallback_error:
                        print(f"Fallback connection also failed: {fallback_error}")
                        QMessageBox.critical(self, "Error", f"Failed to send test email:\n{str(fallback_error)}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to send test email:\n{str(conn_error)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send test email:\n{str(e)}")
            print(f"Error in send_test_email: {e}")
            import traceback
            traceback.print_exc()
    
    def go_back(self):
        """Go back to the previous window"""
        # Close this window and return to the parent window
        self.close()

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show the main window
    window = MailSettingsWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    # Uncomment to test sending combined reports email
    # yesterday = datetime.now() - timedelta(days=1)
    # yesterday_str = yesterday.strftime('%Y-%m-%d')
    # send_combined_reports_email(yesterday_str)
    
    main()
    