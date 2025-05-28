# LicenseApp.py
# Complete desktop application with GUI for license management
# Integrates the LicenseManager with a tkinter-based user interface

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from datetime import datetime
import os
import json
import hashlib
import platform
import psutil
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import mysql.connector
from mysql.connector import Error
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

class LicenseManager:
    def __init__(self):
        
        # Configuration
        self.ALGORITHM = "AES"
        self.SECRET_KEY = hashlib.sha256("Payguru123$ecureKey!".encode()).digest()
        
        # Database configuration
        self.DB_CONFIG = {
            'host': '103.216.211.36',
            'port': 33975,
            'user': 'pgcanteen',
            'password': 'L^{Z,8~zzfF9(nd8',
            'database': 'payguru_canteen'
        }
        
        # File paths
        self.USER_DATA_PATH = self.get_user_data_path()
        self.LICENSE_FILE_PATH = os.path.join(self.USER_DATA_PATH, "license.json")
        print(f"license file path : {self.LICENSE_FILE_PATH}")
        # Ensure directory exists
        os.makedirs(self.USER_DATA_PATH, exist_ok=True)
    def get_user_data_path(self):
        """Get the user data directory path based on the operating system"""
        system = platform.system()
        if system == "Windows":
            return os.path.join(os.environ.get('APPDATA', ''), 'EzeeCanteen')
        elif system == "Darwin":  # macOS
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'EzeeCanteen')
        else:  # Linux
            return os.path.join(os.path.expanduser('~'), '.config', 'EzeeCanteen')

    def encrypt_data(self, data):
        """Encrypt data using AES-256-CBC"""
        try:
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(self.SECRET_KEY), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            data_bytes = data.encode('utf-8')
            padding_length = 16 - (len(data_bytes) % 16)
            padded_data = data_bytes + bytes([padding_length] * padding_length)
            
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                'iv': iv.hex(),
                'content': encrypted.hex()
            }
        except Exception as e:
            logging.error(f"Error encrypting data: {e}")
            raise

    def decrypt_data(self, data):
        """Decrypt data using AES-256-CBC"""
        try:
            iv = bytes.fromhex(data['iv'])
            encrypted = bytes.fromhex(data['content'])
            
            cipher = Cipher(algorithms.AES(self.SECRET_KEY), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
            padding_length = decrypted_padded[-1]
            decrypted = decrypted_padded[:-padding_length]
            
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"Error decrypting data: {e}")
            raise

    async def get_device_id(self):
        """Generate a unique device ID based on hardware characteristics"""
        try:
            cpu_info = platform.processor()
            total_memory = str(psutil.virtual_memory().total)
            system_info = platform.system() + platform.release()
            static_identifier = cpu_info + total_memory + system_info
            machine_id = hashlib.sha256(static_identifier.encode()).hexdigest()
            print(f"Machine ID: {machine_id}")
            return machine_id
        except Exception as e:
            logging.error(f"Error retrieving device ID: {e}")
            return None

    async def get_db_connection(self):
        """Create and return a connection to the MySQL database"""
        try:
            connection = mysql.connector.connect(**self.DB_CONFIG)
            return connection
        except Error as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    async def check_license_exist_db(self):
        """Check if license exists in database for current device"""
        try:
            current_device_id = await self.get_device_id()
            if not current_device_id:
                return False
            connection = await self.get_db_connection()
            cursor = connection.cursor()
            
            query = "SELECT * FROM license WHERE DeviceID = %s"
            cursor.execute(query, (current_device_id,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            return result is not None
        except Exception as e:
            logging.error(f"Failed to retrieve DB License: {e}")
            return False

    async def get_license_db(self):
        """Get license data from database for current device"""
        try:
            current_device_id = await self.get_device_id()
            if not current_device_id:
                return False
                
            connection = await self.get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM license WHERE DeviceID = %s"
            cursor.execute(query, (current_device_id,))
            result = cursor.fetchone()
            print(f"license details : {result}")
            cursor.close()
            connection.close()
            
            return result if result else False
        except Exception as e:
            logging.error(f"Failed to retrieve DB License: {e}")
            return False

    async def check_license_validity_db(self):
        """Check license validity from database"""
        try:
            license_data = await self.get_license_db()
            if not license_data:
                return {'isValid': False, 'message': 'InvalidLicense'}
            
            db_active_status = license_data.get('ActiveStatus')
            db_device_id = license_data.get('DeviceID')
            db_activation_date = license_data.get('ActivationDate')
            
            current_device_id = await self.get_device_id()
            
            if not current_device_id:
                return {'isValid': False, 'message': 'InvalidLicense'}
                
            if db_device_id.upper() != current_device_id.upper():
                return {'isValid': False, 'message': 'InvalidLicense'}
            
            if db_active_status.upper() == 'Y':
                if isinstance(db_activation_date, str):
                    db_activation_date = datetime.strptime(db_activation_date, '%Y-%m-%d %H:%M:%S')
                
                if db_activation_date < datetime.now():
                    return {'isValid': True, 'message': 'ValidLicense'}
                else:
                    return {'isValid': False, 'message': 'InvalidLicense'}
            else:
                return {'isValid': False, 'message': 'InvalidLicense'}
                
        except Exception as e:
            logging.error(f"checkLicenseValidityDB error: {e}")
            return {'isValid': False, 'message': 'InvalidLicense', 'error': str(e)}

    async def save_license(self, license_data):
        """Save license data to encrypted file"""
        try:
            encrypted_data = self.encrypt_data(json.dumps(license_data, indent=4))
            
            with open(self.LICENSE_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(encrypted_data, f, indent=4)
            print(f"license file path : {self.LICENSE_FILE_PATH}")
            print("License saved in local file")
            return {'success': True, 'message': 'LicenseSaved'}
        except Exception as e:
            logging.error(f"Error saving license data: {e}")
            return {'success': False, 'message': 'LicenseSaveFailed'}

    async def activate_license(self, key):
        """Activate license with provided key"""
        db_connection = None
        
        try:
            print(f"Activating license with key: {key}")
            db_connection = await self.get_db_connection()
            cursor = db_connection.cursor(dictionary=True)
            
            query = """
                SELECT l.RegID, l.LicenseID, l.LicenseKey, l.ActiveStatus, l.DeviceID
                FROM license l
                JOIN users u ON l.RegID = u.RegID
                WHERE l.LicenseKey = %s
            """
            cursor.execute(query, (key,))
            results = cursor.fetchall()
            
            if not results:
                print("License key not found.")
                return {'success': False, 'message': 'License key not found'}
            
            license_data = results[0]
            reg_id = license_data.get('RegID')
            license_id = license_data.get('LicenseID')
            license_key = license_data.get('LicenseKey')
            active_status = license_data.get('ActiveStatus')
            existing_device_id = license_data.get('DeviceID')
            
            if not all([reg_id, license_id, license_key, active_status]):
                return {'success': False, 'message': 'Invalid license data'}
            
            # Check if license is already bound to a different device
            if active_status.upper() == 'Y' and existing_device_id:
                current_device_id = await self.get_device_id()
                if current_device_id and existing_device_id.upper() != current_device_id.upper():
                    return {'success': False, 'message': 'Authentication failed: License already bound to another device'}
            
            cursor.close()
            db_connection.close()
            
        except Exception as e:
            logging.error(f"Error activating license: {e}")
            if db_connection:
                db_connection.close()
            return {'success': False, 'message': 'License activation failed'}
        
        try:
            db_connection = await self.get_db_connection()
            cursor = db_connection.cursor()
            
            if active_status.upper() == 'Y':
                return {'success': False, 'message': 'License already active'}
            elif active_status.upper() == 'N':
                device_id = await self.get_device_id()
                if not device_id:
                    return {'success': False, 'message': 'Device not found'}
                
                device_id = device_id.upper()
                activation_date_time = self.get_current_ist_datetime()
                
                query = """
                    UPDATE license l 
                    JOIN users u ON l.RegID = u.RegID 
                    SET u.ActiveStatus = 'Y', l.ActiveStatus = 'Y', 
                        l.DeviceID = %s, l.ActivationDate = %s 
                    WHERE l.LicenseKey = %s
                """
                cursor.execute(query, (device_id, activation_date_time, license_key))
                db_connection.commit()
                
                cursor.close()
                db_connection.close()
                
                license_data = {
                    'RegID': reg_id,
                    'LicenseID': license_id,
                    'LicenseKey': license_key,
                    'ActiveStatus': 'Y',
                    'DeviceID': device_id,
                    'ActivationDate': activation_date_time
                }
                
                save_result = await self.save_license(license_data)
                if save_result['success']:
                    return {'success': True, 'message': 'License activated successfully'}
                else:
                    return {'success': False, 'message': 'License activation failed'}
            else:
                return {'success': False, 'message': 'Unknown license status'}
                
        except Exception as e:
            logging.error(f"Error activating license: {e}")
            if db_connection:
                db_connection.close()
            return {'success': False, 'message': 'License activation failed'}

    def get_current_ist_datetime(self):
        """Get current IST time in yyyy-mm-dd hh:mm:ss format"""
        now = datetime.now()
        return now.strftime('%Y-%m-%d %H:%M:%S')

    async def check_license_validity(self):
        """Check license validity from both file and database"""
        try:
            file_exists = os.path.exists(self.LICENSE_FILE_PATH)
            db_record_exists = await self.check_license_exist_db()
            
            if not file_exists and not db_record_exists:
                return {'isValid': False, 'message': 'License not found'}
            
            if db_record_exists:
                db_response = await self.check_license_validity_db()
                if not db_response['isValid']:
                    return {'isValid': False, 'message': 'Invalid license'}
                else:
                    if not file_exists:
                        license_data = await self.get_license_db()
                        await self.save_license(license_data)
                    return {'isValid': True, 'message': 'Valid license'}
            
            return {'isValid': False, 'message': 'Invalid license'}
            
        except Exception as e:
            logging.error(f"checkLicenseValidity error: {e}")
            return {'isValid': False, 'message': 'License check failed', 'error': str(e)}


class LicenseApp:
    def __init__(self):
        self.license_manager = LicenseManager()
        self.root = tk.Tk()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main UI"""
        self.root.title("EzeeCanteen License")
        self.root.geometry("400x300")
        self.root.configure(bg='#1a202c')  # Dark gray background
        self.root.resizable(False, False)
        
        # Configure style for ttk widgets
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for dark theme
        style.configure('Dark.TLabel', background='#1a202c', foreground='white', font=('Arial', 10))
        style.configure('Title.TLabel', background='#1a202c', foreground='#818cf8', font=('Arial', 16, 'bold'))
        style.configure('Dark.TEntry', fieldbackground='#374151', foreground='white', borderwidth=1, relief='solid')
        style.configure('Dark.TButton', background='#4f46e5', foreground='white', font=('Arial', 10, 'bold'))
        style.map('Dark.TButton', background=[('active', '#4338ca')])
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a202c', padx=32, pady=40)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="EzeeCanteen License", style='Title.TLabel')
        title_label.pack(pady=(0, 16))
        
        # Subtitle
        subtitle_label = ttk.Label(main_frame, text="Register or activate with license key.", style='Dark.TLabel')
        subtitle_label.pack(pady=(0, 24))
        
        # License key input
        self.license_key_var = tk.StringVar()
        license_entry = ttk.Entry(main_frame, textvariable=self.license_key_var, style='Dark.TEntry', font=('Arial', 10))
        license_entry.pack(fill='x', pady=(0, 16), ipady=8)
        license_entry.focus()
        
        # Activate button
        activate_btn = tk.Button(
            main_frame, 
            text="Activate", 
            command=self.activate_license,
            bg='#4f46e5', 
            fg='white', 
            font=('Arial', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            pady=8
        )
        activate_btn.pack(fill='x', pady=(0, 8))
        
        # Button frame for trial and register buttons
        button_frame = tk.Frame(main_frame, bg='#1a202c')
        button_frame.pack(fill='x', pady=(0, 16))
        
        # Continue to trial button
        trial_btn = tk.Button(
            button_frame, 
            text="Continue to Trial", 
            command=self.continue_to_trial,
            bg='#059669', 
            fg='white', 
            font=('Arial', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            pady=8
        )
        trial_btn.pack(side='left', fill='x', expand=True, padx=(0, 4))
        
        # Register now button
        register_btn = tk.Button(
            button_frame, 
            text="Register Now", 
            command=self.register_now,
            bg='#d97706', 
            fg='white', 
            font=('Arial', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            pady=8
        )
        register_btn.pack(side='right', fill='x', expand=True, padx=(4, 0))
        
        # Message label
        self.message_var = tk.StringVar()
        self.message_label = ttk.Label(main_frame, textvariable=self.message_var, style='Dark.TLabel', font=('Arial', 9))
        self.message_label.pack(pady=(16, 0))
        
        # Bind Enter key to activate button
        self.root.bind('<Return>', lambda event: self.activate_license())
        
        # Display initial message
        self.show_message("Please enter your license key to activate.", '#fbbf24')
    
    def show_message(self, message, color='white', duration=5000):
        """Show a message to the user"""
        self.message_var.set(message)
        self.message_label.configure(foreground=color)
        if duration > 0:
            self.root.after(duration, lambda: self.message_var.set(''))
    
    def run_async_task(self, coro):
        """Run an async task in a separate thread"""
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()
        return thread
    
    def activate_license(self):
        """Activate license with the entered key"""
        license_key = self.license_key_var.get().strip()
        
        if not license_key:
            self.show_message("Please enter a license key", '#ef4444')
            return
        
        self.show_message("Activating license...", '#3b82f6', 0)
        
        def activate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.license_manager.activate_license(license_key))
                self.root.after(0, lambda: self.handle_activation_result(result))
            finally:
                loop.close()
        
        thread = threading.Thread(target=activate)
        thread.daemon = True
        thread.start()
    
    def handle_activation_result(self, result):
        """Handle the result of license activation"""
        if result['success']:
            self.show_message("License activated successfully!", '#10b981')
            messagebox.showinfo("Success", "License activated successfully!")
            self.root.after(1000, self.open_main_application)
        else:
            self.show_message(result['message'], '#ef4444')
    
    def continue_to_trial(self):
        """Handle continue to trial button"""
        self.show_message("Starting trial mode...", '#10b981')
        messagebox.showinfo("Trial Mode", "Trial mode activated!")
        # Open the main application after trial activation
        self.root.after(1000, self.open_main_application)
    
    def register_now(self):
        """Handle register now button"""
        import webbrowser
        webbrowser.open("https://your-registration-website.com")
        self.show_message("Opening registration page...", '#3b82f6')
    
    def open_main_application(self):
        """Open the main application window"""
        # Close the license window
        self.root.quit()
        
        # Run settings.py directly after activation
        import os
        import sys
        import subprocess
        
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(current_dir, "settings.py")
        
        # Check if settings.py exists and run it
        if os.path.exists(settings_path):
            messagebox.showinfo("Success", "Opening EzeeCanteen main application...")
            # Use the same Python interpreter that's running this script
            python_executable = sys.executable
            subprocess.Popen([python_executable, settings_path])
        else:
            messagebox.showerror("Error", f"Could not find settings.py in {current_dir}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


# Trial License Manager (placeholder)
class TrialLicenseManager:
    def __init__(self):
        pass
    
    def continue_to_trial(self):
        """Handle trial continuation"""
        print("Continuing to trial...")
        return {'success': True, 'message': 'Trial started'}


def main():
    """Main function to run the application"""
    try:
        # Create license manager first to check validity
        license_manager = LicenseManager()
        
        # Check license validity before showing UI
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(license_manager.check_license_validity())
            loop.close()
            
            if result['isValid']:
                # License is valid, open main application directly
                messagebox.showinfo("Success", "License is valid! Opening main application...")
                # Run settings.py directly
                import os
                import sys
                import subprocess
                
                # Get the current directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                settings_path = os.path.join(current_dir, "settings.py")
                
                # Check if settings.py exists and run it
                if os.path.exists(settings_path):
                    # Use the same Python interpreter that's running this script
                    python_executable = sys.executable
                    subprocess.Popen([python_executable, settings_path])
                else:
                    messagebox.showerror("Error", f"Could not find settings.py in {current_dir}")
                return
            else:
                # License is invalid, show the license UI
                app = LicenseApp()
                app.run()
        except Exception as e:
            logging.error(f"License check error: {e}")
            # If there's an error checking license, show the UI anyway
            app = LicenseApp()
            app.run()
    except Exception as e:
        logging.error(f"Application error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    main()