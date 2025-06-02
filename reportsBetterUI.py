import sys
import datetime
import pandas as pd
import mysql.connector
from mysql.connector import Error
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QFrame, QMessageBox, QProgressBar, QSpacerItem, 
                             QSizePolicy, QGraphicsDropShadowEffect, QGridLayout,
                             QTextEdit, QScrollArea, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLineEdit, QDateEdit,
                             QGroupBox, QCheckBox, QSlider, QFileDialog)
from PyQt5.QtCore import (Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, 
                          QEasingCurve, QRect, QDate, QParallelAnimationGroup,
                          QSequentialAnimationGroup, QSize)
from PyQt5.QtGui import (QFont, QPalette, QColor, QMovie, QPainter, QBrush,
                         QLinearGradient, QPen, QPixmap, QIcon, QFontDatabase)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QPieSeries, QBarSeries, QBarSet
import json

# Database configuration
DB_CONFIG = {
    'host': "103.216.211.36",
    'user': "pgcanteen",
    'port': 33975,
    'password': "L^{Z,8~zzfF9(nd8",
    'database': "payguru_canteen"
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        
    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            return True
        except Error as e:
            print(f"Database connection error: {e}")
            return False
            
    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            
    def execute_query(self, query, params=None):
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return None
                    
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"Query execution error: {e}")
            return None
              
    def get_monthly_summary(self, month, year):
        # Get license key from settings
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
        license_key = all_settings.get('LicenseKey')
        if not license_key:
            print("License key not found in settings")
            return None
            
        query = """
        SELECT 
            DATE(PunchDateTime) as date,
            Fooditem,
            COUNT(*) as count,
            PunchCardNo
        FROM sequentiallog 
        WHERE MONTH(PunchDateTime) = %s 
        AND YEAR(PunchDateTime) = %s 
        AND CanteenMode IS NOT NULL
        AND LicenseKey = %s
        GROUP BY DATE(PunchDateTime), Fooditem, PunchCardNo
        ORDER BY date DESC
        """
        return self.execute_query(query, (month, year, license_key))
        
    def get_daily_consumption(self):
        # Get license key from settings
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
        license_key = all_settings.get('LicenseKey')
        if not license_key:
            print("License key not found in settings")
            return None
            
        query = """
        SELECT 
            DATE(PunchDateTime) as date,
            Fooditem,
            COUNT(*) as total_items,
            COUNT(DISTINCT PunchCardNo) as unique_users
        FROM sequentiallog 
        WHERE DATE(PunchDateTime) = CURDATE()
        AND CanteenMode IS NOT NULL
        AND LicenseKey = %s
        GROUP BY Fooditem
        ORDER BY total_items DESC
        """
        return self.execute_query(query, (license_key,))
        
    def get_canteen_logs(self, month, year):
        # Get license key from settings
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
        license_key = all_settings.get('LicenseKey')
        if not license_key:
            print("License key not found in settings")
            return None
            
        query = """
        SELECT 
            PunchCardNo,
            PunchDateTime,
            Fooditem,
            CanteenMode,
            IPAddress,
            ZK_SerialNo
        FROM sequentiallog 
        WHERE MONTH(PunchDateTime) = %s 
        AND YEAR(PunchDateTime) = %s 
        AND CanteenMode IS NOT NULL
        AND LicenseKey = %s
        ORDER BY PunchDateTime DESC
        """
        return self.execute_query(query, (month, year, license_key))
        
    def get_statistics(self, month, year):
        # Get license key from settings
        with open('appSettings.json', 'r') as file:
            all_settings = json.load(file)
        license_key = all_settings.get('LicenseKey')
        if not license_key:
            print("License key not found in settings")
            return None
            
        query = """
        SELECT 
            COUNT(*) as total_transactions,
            COUNT(DISTINCT PunchCardNo) as unique_users,
            COUNT(DISTINCT Fooditem) as food_varieties,
            COUNT(DISTINCT DATE(PunchDateTime)) as active_days
        FROM sequentiallog 
        WHERE MONTH(PunchDateTime) = %s 
        AND YEAR(PunchDateTime) = %s 
        AND CanteenMode IS NOT NULL
        AND LicenseKey = %s
        """
        return self.execute_query(query, (month, year, license_key))


class ModernSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        
    def start(self):
        self.timer.start(30)
        self.show()
        
    def stop(self):
        self.timer.stop()
        self.hide()
        
    def rotate(self):
        self.angle = (self.angle + 8) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(30, 30)
        
        # Create gradient brush
        gradient = QLinearGradient(-20, -20, 20, 20)
        gradient.setColorAt(0, QColor(79, 172, 254))
        gradient.setColorAt(0.5, QColor(0, 242, 254))
        gradient.setColorAt(1, QColor(129, 236, 236))
        
        # Draw spinning arc
        painter.rotate(self.angle)
        painter.setPen(QPen(QBrush(gradient), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(-20, -20, 40, 40, 0, 270 * 16)


class AnimatedCard(QFrame):
    def __init__(self, title, value, subtitle="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setupUI(title, value, subtitle)
        self.setupAnimation()
        
    def setupUI(self, title, value, subtitle):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(str(value))
        value_label.setStyleSheet("color: #1e293b; font-size: 28px; font-weight: 700;")
        layout.addWidget(value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("color: #64748b; font-size: 11px;")
            layout.addWidget(subtitle_label)
            
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QFrame:hover {
                border: 1px solid #3b82f6;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #eff6ff);
            }
        """)
        
    def setupAnimation(self):
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class DatabaseWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args
        self.db_manager = DatabaseManager()
        
    def run(self):
        try:
            if self.operation == "monthly_report":
                month, year = self.args
                data = self.db_manager.get_monthly_summary(month, year)
                stats = self.db_manager.get_statistics(month, year)
                self.finished.emit({
                    'type': 'monthly_report',
                    'data': data,
                    'stats': stats[0] if stats else {},
                    'success': True
                })
                
            elif self.operation == "daily_report":
                data = self.db_manager.get_daily_consumption()
                self.finished.emit({
                    'type': 'daily_report',
                    'data': data,
                    'success': True
                })
                
            elif self.operation == "canteen_logs":
                month, year = self.args
                data = self.db_manager.get_canteen_logs(month, year)
                self.finished.emit({
                    'type': 'canteen_logs',
                    'data': data,
                    'success': True
                })
                
            elif self.operation == "send_mail":
                month, year = self.args
                # Generate report and send email
                success = self.send_email_report(month, year)
                self.finished.emit({
                    'type': 'send_mail',
                    'success': success
                })
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.db_manager.disconnect()
            
    def send_email_report(self, month, year):
        # This is a placeholder - implement actual email sending logic
        self.msleep(2000)  # Simulate processing
        return True


class ModernReportsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PayGuru Canteen Reports Dashboard")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Initialize database
        self.db_manager = DatabaseManager()
        self.worker_thread = None
        
        self.setupUI()
        self.setupStyles()
        self.load_initial_data()
        
    def setupUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)
        
        # Header section
        self.create_header(main_layout)
        
        # Controls section
        self.create_controls(main_layout)
        
        # Statistics cards
        self.create_stats_section(main_layout)
        
        # Main content with tabs
        self.create_main_content(main_layout)
        
        # Status bar
        self.create_status_bar(main_layout)
        
    def create_header(self, parent_layout):
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title section
        title_layout = QVBoxLayout()
        title_label = QLabel("Canteen Reports Dashboard")
        title_label.setStyleSheet("""
            color: #1e293b;
            font-size: 32px;
            font-weight: 700;
            margin: 0;
        """)
        
        subtitle_label = QLabel("Real-time analytics and reporting")
        subtitle_label.setStyleSheet("""
            color: #64748b;
            font-size: 16px;
            margin-top: 5px;
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Current date/time
        self.datetime_label = QLabel()
        self.datetime_label.setStyleSheet("""
            color: #475569;
            font-size: 14px;
            background: #f1f5f9;
            padding: 10px 15px;
            border-radius: 8px;
        """)
        header_layout.addWidget(self.datetime_label)
        
        # Update time every second
        timer = QTimer(self)
        timer.timeout.connect(self.update_datetime)
        timer.start(1000)
        self.update_datetime()
        
        parent_layout.addWidget(header_frame)
        
    def create_controls(self, parent_layout):
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(20, 20, 20, 20)
        
        # Date selection group
        date_group = QGroupBox("Filter Options")
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("Month:"))
        self.month_combo = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        for i, month in enumerate(months, 1):
            self.month_combo.addItem(month, i)
        self.month_combo.setCurrentIndex(datetime.datetime.now().month - 1)
        self.month_combo.currentChanged.connect(self.on_filter_changed)
        date_layout.addWidget(self.month_combo)
        
        date_layout.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        current_year = datetime.datetime.now().year
        for year in range(current_year - 5, current_year + 1):
            self.year_combo.addItem(str(year), year)
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentChanged.connect(self.on_filter_changed)
        date_layout.addWidget(self.year_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        date_layout.addWidget(refresh_btn)
        
        controls_layout.addWidget(date_group)
        controls_layout.addStretch()
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.send_mail_btn = QPushButton("📧 Send Report")
        self.send_mail_btn.clicked.connect(self.send_mail)
        actions_layout.addWidget(self.send_mail_btn)
        
        export_btn = QPushButton("💾 Export Data")
        export_btn.clicked.connect(self.export_data)
        actions_layout.addWidget(export_btn)
        
        back_btn = QPushButton("⬅ Back")
        back_btn.clicked.connect(self.go_back)
        actions_layout.addWidget(back_btn)
        
        controls_layout.addLayout(actions_layout)
        
        parent_layout.addWidget(controls_frame)
        
    def create_stats_section(self, parent_layout):
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(20)
        
        # Initialize stat cards
        self.total_transactions_card = AnimatedCard("Total Transactions", "0", "This month")
        self.unique_users_card = AnimatedCard("Unique Users", "0", "Active users")
        self.food_varieties_card = AnimatedCard("Food Varieties", "0", "Different items")
        self.active_days_card = AnimatedCard("Active Days", "0", "Days with activity")
        
        stats_layout.addWidget(self.total_transactions_card)
        stats_layout.addWidget(self.unique_users_card)
        stats_layout.addWidget(self.food_varieties_card)
        stats_layout.addWidget(self.active_days_card)
        
        parent_layout.addWidget(stats_frame)
        
    def create_main_content(self, parent_layout):
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Reports tab
        reports_tab = self.create_reports_tab()
        self.tab_widget.addTab(reports_tab, "📊 Reports")
        
        # Data view tab
        data_tab = self.create_data_tab()
        self.tab_widget.addTab(data_tab, "📋 Data View")
        
        # Analytics tab
        analytics_tab = self.create_analytics_tab()
        self.tab_widget.addTab(analytics_tab, "📈 Analytics")
        
        parent_layout.addWidget(self.tab_widget)
        
    def create_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        
        # Report generation section
        reports_grid = QGridLayout()
        
        # Monthly Report
        monthly_frame = self.create_report_card(
            "📊 Monthly Summary Report",
            "Comprehensive monthly consumption analysis",
            "Generate Monthly Report",
            self.generate_monthly_report
        )
        reports_grid.addWidget(monthly_frame, 0, 0)
        
        # Daily Report
        daily_frame = self.create_report_card(
            "📅 Daily Consumption Report", 
            "Today's food consumption details",
            "Generate Daily Report",
            self.generate_daily_report
        )
        reports_grid.addWidget(daily_frame, 0, 1)
        
        # Canteen Logs
        logs_frame = self.create_report_card(
            "📝 Canteen Activity Logs",
            "Detailed transaction logs and user activity",
            "Generate Logs Report", 
            self.generate_canteen_logs
        )
        reports_grid.addWidget(logs_frame, 1, 0)
        
        # Custom Report
        custom_frame = self.create_report_card(
            "🔧 Custom Report",
            "Create custom reports with filters",
            "Generate Custom Report",
            self.generate_custom_report
        )
        reports_grid.addWidget(custom_frame, 1, 1)
        
        layout.addLayout(reports_grid)
        layout.addStretch()
        
        return tab
        
    def create_data_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Data table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.data_table)
        
        return tab
        
    def create_analytics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Placeholder for charts
        analytics_label = QLabel("📈 Analytics Dashboard\n\nCharts and visualizations will be displayed here")
        analytics_label.setAlignment(Qt.AlignCenter)
        analytics_label.setStyleSheet("""
            color: #64748b;
            font-size: 18px;
            padding: 60px;
            background: #f8fafc;
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
        """)
        layout.addWidget(analytics_label)
        
        return tab
        
    def create_report_card(self, title, description, button_text, callback):
        frame = QFrame()
        frame.setFixedHeight(200)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #1e293b;
            font-size: 20px;
            font-weight: 600;
        """)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            color: #64748b;
            font-size: 14px;
            line-height: 1.5;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
        # Button
        btn = QPushButton(button_text)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #1e40af);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #1e3a8a);
            }
        """)
        layout.addWidget(btn)
        
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QFrame:hover {
                border: 1px solid #3b82f6;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f0f9ff);
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 3)
        frame.setGraphicsEffect(shadow)
        
        return frame
        
    def create_status_bar(self, parent_layout):
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 15, 20, 15)
        
        # Loading indicator
        self.spinner = ModernSpinner()
        self.spinner.hide()
        status_layout.addWidget(self.spinner)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #64748b; font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # Footer
        footer_label = QLabel("Developed by PayGuru Technosoft Pvt. Ltd.")
        footer_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        status_layout.addWidget(footer_label)
        
        parent_layout.addWidget(status_frame)
        
    def setupStyles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #e2e8f0);
            }
            QComboBox {
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #64748b;
            }
            QPushButton {
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 500;
                font-size: 14px;
                color: #374151;
            }
            QPushButton:hover {
                border-color: #3b82f6;
                background: #f0f9ff;
                color: #1e40af;
            }
            QGroupBox {
                font-weight: 600;
                color: #374151;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 15px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background: white;
            }
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                padding: 12px 20px;
                margin-right: 2px;
                border-radius: 8px 8px 0 0;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
                color: #3b82f6;
                font-weight: 600;
            }
            QTableWidget {
                gridline-color: #e2e8f0;
                background: white;
                alternate-background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #f1f5f9;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 12px;
                font-weight: 600;
                color: #374151;
            }
        """)
        
    def update_datetime(self):
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%B %d, %Y - %I:%M:%S %p")
        self.datetime_label.setText(formatted_time)
        
    def show_loading(self, message="Processing..."):
        self.status_label.setText(message)
        self.spinner.start()
        
    def hide_loading(self):
        self.spinner.stop()
        self.status_label.setText("Ready")
        
    def show_message(self, title, message, is_error=False):
        if is_error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)
            
    def load_initial_data(self):
        self.refresh_data()
        
    def on_filter_changed(self):
        self.refresh_data()
        
    def refresh_data(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading("Loading statistics...")
        self.worker_thread = DatabaseWorker("monthly_report", month, year)
        self.worker_thread.finished.connect(self.on_data_received)
        self.worker_thread.error.connect(self.on_error)
        self.worker_thread.start()
        
    def on_data_received(self, result):
        self.hide_loading()
        
        if result['success'] and result['type'] == 'monthly_report':
            stats = result.get('stats', {})
            
            # Update stat cards
            self.update_stat_card(self.total_transactions_card, stats.get('total_transactions', 0))
            self.update_stat_card(self.unique_users_card, stats.get('unique_users', 0)) 
            self.update_stat_card(self.food_varieties_card, stats.get('food_varieties', 0))
            self.update_stat_card(self.active_days_card, stats.get('active_days', 0))
            
            # Update data table
            self.populate_data_table(result.get('data', []))
            
        elif result['type'] == 'send_mail':
            if result['success']:
                self.show_message("Success", "Report sent successfully!")
            else:
                self.show_message("Error", "Failed to send report", True)
                
    def update_stat_card(self, card, value):
        # Find the value label and update it
        for child in card.children():
            if isinstance(child, QLabel):
                layout = card.layout()
                if layout and layout.itemAt(1):
                    value_widget = layout.itemAt(1).widget()
                    if isinstance(value_widget, QLabel):
                        value_widget.setText(str(value))
                        break
                        
    def populate_data_table(self, data):
        if not data:
            self.data_table.setRowCount(0)
            return
            
        # Set up table headers
        headers = ['Date', 'Card No', 'Food Item', 'Count']
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        
        # Populate data
        self.data_table.setRowCount(len(data))
        for row, record in enumerate(data):
            self.data_table.setItem(row, 0, QTableWidgetItem(str(record.get('date', ''))))
            self.data_table.setItem(row, 1, QTableWidgetItem(str(record.get('PunchCardNo', ''))))
            self.data_table.setItem(row, 2, QTableWidgetItem(str(record.get('Fooditem', ''))))
            self.data_table.setItem(row, 3, QTableWidgetItem(str(record.get('count', ''))))
            
        # Resize columns to content
        self.data_table.resizeColumnsToContents()
        
    def on_error(self, error_message):
        self.hide_loading()
        self.show_message("Database Error", f"An error occurred: {error_message}", True)
        
    def send_mail(self):
        reply = QMessageBox.question(
            self, 
            'Confirm Email', 
            'Are you sure you want to send the monthly report via email?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading("Sending email report...")
        self.worker_thread = DatabaseWorker("send_mail", month, year)
        self.worker_thread.finished.connect(self.on_data_received)
        self.worker_thread.error.connect(self.on_error)
        self.worker_thread.start()
        
    def generate_monthly_report(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading("Generating monthly report...")
        
        try:
            # Get data from database
            data = self.db_manager.get_monthly_summary(month, year)
            if data:
                # Create Excel file
                df = pd.DataFrame(data)
                filename = f"monthly_report_{year}_{month:02d}.xlsx"
                filepath = QFileDialog.getSaveFileName(
                    self, 
                    "Save Monthly Report", 
                    filename, 
                    "Excel Files (*.xlsx)"
                )[0]
                
                if filepath:
                    # Create a more detailed Excel report
                    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                        # Summary sheet
                        summary_data = df.groupby(['date', 'Fooditem']).agg({
                            'count': 'sum',
                            'PunchCardNo': 'nunique'
                        }).reset_index()
                        summary_data.columns = ['Date', 'Food Item', 'Total Count', 'Unique Users']
                        summary_data.to_excel(writer, sheet_name='Summary', index=False)
                        
                        # Detailed sheet
                        df.to_excel(writer, sheet_name='Detailed', index=False)
                        
                        # Daily totals sheet
                        daily_totals = df.groupby('date').agg({
                            'count': 'sum',
                            'PunchCardNo': 'nunique',
                            'Fooditem': 'nunique'
                        }).reset_index()
                        daily_totals.columns = ['Date', 'Total Items', 'Unique Users', 'Food Varieties']
                        daily_totals.to_excel(writer, sheet_name='Daily Totals', index=False)
                    
                    self.hide_loading()
                    self.show_message("Success", f"Monthly report saved successfully!\nLocation: {filepath}")
                else:
                    self.hide_loading()
            else:
                self.hide_loading()
                self.show_message("No Data", "No data found for the selected month and year.", True)
                
        except Exception as e:
            self.hide_loading()
            self.show_message("Error", f"Failed to generate report: {str(e)}", True)
            
    def generate_daily_report(self):
        self.show_loading("Generating daily report...")
        
        try:
            data = self.db_manager.get_daily_consumption()
            if data:
                df = pd.DataFrame(data)
                filename = f"daily_report_{datetime.datetime.now().strftime('%Y_%m_%d')}.xlsx"
                filepath = QFileDialog.getSaveFileName(
                    self, 
                    "Save Daily Report", 
                    filename, 
                    "Excel Files (*.xlsx)"
                )[0]
                
                if filepath:
                    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Daily Consumption', index=False)
                        
                        # Add summary statistics
                        summary = {
                            'Total Items Consumed': [df['total_items'].sum()],
                            'Unique Users': [df['unique_users'].sum()],
                            'Food Varieties': [len(df)],
                            'Most Popular Item': [df.loc[df['total_items'].idxmax(), 'Fooditem'] if len(df) > 0 else 'N/A']
                        }
                        summary_df = pd.DataFrame(summary)
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    self.hide_loading()
                    self.show_message("Success", f"Daily report saved successfully!\nLocation: {filepath}")
                else:
                    self.hide_loading()
            else:
                self.hide_loading()
                self.show_message("No Data", "No data found for today.", True)
                
        except Exception as e:
            self.hide_loading()
            self.show_message("Error", f"Failed to generate daily report: {str(e)}", True)
            
    def generate_canteen_logs(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        
        self.show_loading("Generating canteen logs...")
        
        try:
            data = self.db_manager.get_canteen_logs(month, year)
            if data:
                df = pd.DataFrame(data)
                filename = f"canteen_logs_{year}_{month:02d}.xlsx"
                filepath = QFileDialog.getSaveFileName(
                    self, 
                    "Save Canteen Logs", 
                    filename, 
                    "Excel Files (*.xlsx)"
                )[0]
                
                if filepath:
                    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                        # Format datetime column
                        df['PunchDateTime'] = pd.to_datetime(df['PunchDateTime']).dt.strftime('%Y-%m-%d %H:%M:%S')
                        df.to_excel(writer, sheet_name='Canteen Logs', index=False)
                        
                        # User activity summary
                        user_summary = df.groupby('PunchCardNo').agg({
                            'PunchDateTime': 'count',
                            'Fooditem': lambda x: ', '.join(x.unique())
                        }).reset_index()
                        user_summary.columns = ['Card Number', 'Total Transactions', 'Food Items']
                        user_summary.to_excel(writer, sheet_name='User Summary', index=False)
                    
                    self.hide_loading()
                    self.show_message("Success", f"Canteen logs saved successfully!\nLocation: {filepath}")
                else:
                    self.hide_loading()
            else:
                self.hide_loading()
                self.show_message("No Data", "No canteen logs found for the selected period.", True)
                
        except Exception as e:
            self.hide_loading()
            self.show_message("Error", f"Failed to generate canteen logs: {str(e)}", True)
            
    def generate_custom_report(self):
        # Create custom report dialog
        dialog = CustomReportDialog(self)
        if dialog.exec_() == dialog.Accepted:
            # Get custom parameters and generate report
            params = dialog.get_parameters()
            self.show_loading("Generating custom report...")
            # Implement custom report logic here
            QTimer.singleShot(2000, lambda: (
                self.hide_loading(),
                self.show_message("Success", "Custom report generated successfully!")
            ))
            
    def export_data(self):
        # Export current view data
        if self.data_table.rowCount() == 0:
            self.show_message("No Data", "No data to export.", True)
            return
            
        filename = f"exported_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = QFileDialog.getSaveFileName(
            self, 
            "Export Data", 
            filename, 
            "Excel Files (*.xlsx)"
        )[0]
        
        if filepath:
            try:
                # Extract data from table
                headers = []
                for col in range(self.data_table.columnCount()):
                    headers.append(self.data_table.horizontalHeaderItem(col).text())
                
                data = []
                for row in range(self.data_table.rowCount()):
                    row_data = []
                    for col in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(filepath, index=False)
                
                self.show_message("Success", f"Data exported successfully!\nLocation: {filepath}")
                
            except Exception as e:
                self.show_message("Error", f"Failed to export data: {str(e)}", True)
                
    def go_back(self):
        reply = QMessageBox.question(
            self, 
            'Confirm Exit', 
            'Are you sure you want to go back to the main menu?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()
            
    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        if self.db_manager:
            self.db_manager.disconnect()
            
        event.accept()


class CustomReportDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Report Generator")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(500, 400)
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Custom Report Parameters")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")
        layout.addWidget(title)
        
        # Date range
        date_group = QGroupBox("Date Range")
        date_layout = QGridLayout(date_group)
        
        date_layout.addWidget(QLabel("From:"), 0, 0)
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        date_layout.addWidget(self.from_date, 0, 1)
        
        date_layout.addWidget(QLabel("To:"), 1, 0)
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        date_layout.addWidget(self.to_date, 1, 1)
        
        layout.addWidget(date_group)
        
        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout(filter_group)
        
        self.include_food_items = QCheckBox("Include Food Items Analysis")
        self.include_food_items.setChecked(True)
        filter_layout.addWidget(self.include_food_items)
        
        self.include_user_activity = QCheckBox("Include User Activity")
        self.include_user_activity.setChecked(True)
        filter_layout.addWidget(self.include_user_activity)
        
        self.include_time_analysis = QCheckBox("Include Time-based Analysis")
        filter_layout.addWidget(self.include_time_analysis)
        
        layout.addWidget(filter_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(self.accept)
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        button_layout.addWidget(generate_btn)
        
        layout.addLayout(button_layout)
        
    def get_parameters(self):
        return {
            'from_date': self.from_date.date().toPyDate(),
            'to_date': self.to_date.date().toPyDate(),
            'include_food_items': self.include_food_items.isChecked(),
            'include_user_activity': self.include_user_activity.isChecked(),
            'include_time_analysis': self.include_time_analysis.isChecked()
        }
        
    def accept(self):
        self.close()
        return self.Accepted
        
    def reject(self):
        self.close()
        return self.Rejected
        
    Accepted = 1
    Rejected = 0


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("PayGuru Canteen Reports")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("PayGuru Technosoft Pvt. Ltd.")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = ModernReportsWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()