"""
LicenseManager.py
This file is responsible for handling the license related operations
It includes functions to check the validity of the license, save the license data, activate the license, and handle the license activation process.
It also includes functions to encrypt and decrypt the license data for storage and retrieval.
It is used by the LicensePage.py file to handle the license activation process and by the main process to check the validity of the license.
It is also used to handle the license activation process in the main process.
"""

import os
import json
import hashlib
import platform
import psutil
from datetime import datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import mysql.connector
from mysql.connector import Error
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicenseManager:
    def __init__(self):
        # Get user data path (equivalent to app.getPath("userData") in Electron)
        if platform.system() == "Windows":
            self.user_data_path = os.path.join(os.environ.get('APPDATA', ''), 'YourAppName')
        elif platform.system() == "Darwin":  # macOS
            self.user_data_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'YourAppName')
        else:  # Linux
            self.user_data_path = os.path.join(os.path.expanduser('~'), '.config', 'YourAppName')
        
        # Create directory if it doesn't exist
        Path(self.user_data_path).mkdir(parents=True, exist_ok=True)
        
        self.license_file_path = os.path.join(self.user_data_path, "license.json")
        
        # Encryption settings
        self.algorithm = "aes-256-cbc"
        self.secret_key = hashlib.sha256("Payguru123$ecureKey!".encode()).digest()

    def encrypt_data(self, data):
        """Encrypt data using AES-256-CBC"""
        try:
            # Generate random IV
            iv = os.urandom(16)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.secret_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Pad data to be multiple of 16 bytes
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data.encode()) + padder.finalize()
            
            # Encrypt
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                "iv": iv.hex(),
                "content": encrypted.hex()
            }
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return None

    def decrypt_data(self, data):
        """Decrypt data using AES-256-CBC"""
        try:
            iv = bytes.fromhex(data["iv"])
            encrypted = bytes.fromhex(data["content"])
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.secret_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # Decrypt
            padded_data = decryptor.update(encrypted) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return None

    async def get_device_id(self):
        """Get device ID based on CPU models and total memory"""
        try:
            # Get CPU models and total memory as static identifiers
            cpu_info = platform.processor()
            total_memory = str(psutil.virtual_memory().total)
            static_identifier = cpu_info + total_memory
            
            # Create a SHA-256 hash of the static identifier
            machine_id = hashlib.sha256(static_identifier.encode()).hexdigest()
            
            return machine_id
        except Exception as e:
            logger.error(f"Error retrieving device ID: {e}")
            return None

    async def get_db_connection(self):
        """Create and return a connection to the MySQL database"""
        try:
            connection = mysql.connector.connect(
                host="103.216.211.36",
                port="33975",
                user="pgcanteen",
                password="L^{Z,8~zzfF9(nd8",
                database="payguru_canteen"
            )
            return connection
        except Error as e:
            logger.error(f"Error connecting to MySQL database: {e}")
            return None

    async def check_license_exist_db(self):
        """Check if license exists in database"""
        try:
            current_device_id = await self.get_device_id()
            if current_device_id:
                connection = await self.get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("SELECT * FROM license WHERE DeviceID = %s", (current_device_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    connection.close()
                    return result is not None
                else:
                    return False
            else:
                return False
        except Exception as e:
            logger.error("Failed to retrieve DB License")
            return False

    async def get_license_db(self):
        """Get license from database"""
        try:
            current_device_id = await self.get_device_id()
            if current_device_id:
                connection = await self.get_db_connection()
                if connection:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM license WHERE DeviceID = %s", (current_device_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    connection.close()
                    return result
                else:
                    return False
            else:
                return False
        except Exception as e:
            logger.error("Failed to retrieve DB License")
            return False

    async def check_license_validity_db(self):
        """Check license validity from database"""
        try:
            license_data = await self.get_license_db()
            if not license_data:
                return {"isValid": False, "message": "InvalidLicense"}
            
            db_reg_id = license_data.get("RegID")
            db_license_id = license_data.get("LicenseID")
            db_license_key = license_data.get("LicenseKey")
            db_active_status = license_data.get("ActiveStatus")
            db_device_id = license_data.get("DeviceID")
            db_activation_date = license_data.get("ActivationDate")
            
            current_device_id = await self.get_device_id()
            
            if current_device_id is None:
                return {"isValid": False, "message": "InvalidLicense"}
            
            if db_device_id.upper() != current_device_id.upper():
                return {"isValid": False, "message": "InvalidLicense"}
            else:
                if db_active_status.upper() == "Y":
                    if db_activation_date < datetime.now():
                        return {"isValid": True, "message": "ValidLicense"}
                    else:
                        return {"isValid": False, "message": "InvalidLicense"}
                else:
                    return {"isValid": False, "message": "InvalidLicense"}
        except Exception as e:
            logger.error(f"checkTrialValidityDB error: {e}")
            return {
                "isValid": False,
                "message": "InvalidLicense",
                "error": str(e)
            }

    async def check_license_validity(self):
        """Check license validity from file and database"""
        file_exists = False
        db_record_exists = False
        
        try:
            file_exists = os.path.exists(self.license_file_path)
            db_record_exists = await self.check_license_exist_db()
            
            if not file_exists and not db_record_exists:
                return {
                    "isValid": False,
                    "message": "LicenseNotFound"
                }
            
            if db_record_exists:
                db_response = await self.check_license_validity_db()
                if not db_response["isValid"]:
                    return {
                        "isValid": False,
                        "message": "InvalidLicense"
                    }
                else:
                    if not file_exists:
                        license_data = await self.get_license_db()
                        await self.save_license(license_data)
                    return {
                        "isValid": True,
                        "message": "ValidLicense"
                    }
            
            if file_exists:
                try:
                    logger.info("File Exist")
                    with open(self.license_file_path, 'r') as f:
                        license_enc_data = f.read()
                    
                    decrypted_data = self.decrypt_data(json.loads(license_enc_data))
                    if decrypted_data is None:
                        return {"isValid": False, "message": "InvalidLicense"}
                    
                    license_data = json.loads(decrypted_data)
                    
                    reg_id = license_data.get("RegID")
                    license_key = license_data.get("LicenseKey")
                    license_id = license_data.get("LicenseID")
                    active_status = license_data.get("ActiveStatus")
                    device_id = license_data.get("DeviceID")
                    activation_date = license_data.get("ActivationDate")
                    
                    current_device_id = await self.get_device_id()
                    if current_device_id is None:
                        return {"isValid": False, "message": "InvalidLicense"}
                    
                    if current_device_id.upper() != device_id.upper():
                        return {"isValid": False, "message": "InvalidLicense"}
                    else:
                        if active_status.upper() == "Y":
                            if datetime.fromisoformat(activation_date.replace(' ', 'T')) < datetime.now():
                                return {"isValid": True, "message": "ValidLicense"}
                            else:
                                return {"isValid": False, "message": "InvalidLicense"}
                        else:
                            return {"isValid": False, "message": "InvalidLicense"}
                except Exception as e:
                    logger.error(f"Error checking license validity: {e}")
                    return {"isValid": False, "message": "InvalidLicense"}
        
        except Exception as e:
            logger.error(f"checkLicenseValidity error: {e}")
            return {
                "isValid": False,
                "message": "InvalidLicense",
                "error": str(e)
            }
        
        return {"isValid": False, "message": "InvalidLicense"}

    async def save_license(self, license_data):
        """Save license data to encrypted file"""
        try:
            encrypted_data = self.encrypt_data(json.dumps(license_data, indent=4))
            if encrypted_data is None:
                return {"success": False, "message": "LicenseSaveFailed"}
            
            with open(self.license_file_path, 'w') as f:
                json.dump(encrypted_data, f, indent=4)
            
            logger.info("License saved in local file")
            return {"success": True, "message": "LicenseSaved"}
        except Exception as e:
            logger.error(f"Error saving license data: {e}")
            return {"success": False, "message": "LicenseSaveFailed"}

    def get_current_ist_datetime(self):
        """Get current IST datetime in yyyy-mm-dd hh:mm:ss format"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    async def activate_license(self, key):
        """Activate license with given key"""
        db_connection = None
        
        try:
            logger.info(f"Key: {key}")
            db_connection = await self.get_db_connection()
            if not db_connection:
                return {"success": False, "message": "LicenseActivationFailed"}
            
            cursor = db_connection.cursor(dictionary=True)
            query = """
                SELECT l.RegID, l.LicenseID, l.LicenseKey, u.ActiveStatus
                FROM license l
                JOIN users u ON l.RegID = u.RegID
                WHERE l.LicenseKey = %s
            """
            cursor.execute(query, (key,))
            results = cursor.fetchall()
            
            if not results:
                logger.info("License key not found.")
                cursor.close()
                db_connection.close()
                return {"success": False, "message": "LicenseKeyNotFound"}
            
            license_data = results[0]
            reg_id = license_data.get("RegID")
            license_id = license_data.get("LicenseID")
            license_key = license_data.get("LicenseKey")
            active_status = license_data.get("ActiveStatus")
            
            if not all([reg_id, license_id, license_key, active_status]):
                cursor.close()
                db_connection.close()
                return {"success": False, "message": "LicenseKeyNotFound"}
            
            logger.info(f"RegID: {reg_id}")
            logger.info(f"LicenseID: {license_id}")
            logger.info(f"LicenseKey: {license_key}")
            logger.info(f"ActiveStatus: {active_status}")
            
            cursor.close()
            db_connection.close()
            
        except Exception as e:
            logger.error(f"Error activating license: {e}")
            if db_connection:
                db_connection.close()
            return {"success": False, "message": "LicenseActivationFailed"}
        
        try:
            db_connection = await self.get_db_connection()
            if not db_connection:
                return {"success": False, "message": "LicenseActivationFailed"}
            
            if active_status.upper() == "Y":
                db_connection.close()
                return {"success": False, "message": "LicenseAlreadyActive"}
            elif active_status.upper() == "N":
                device_id = await self.get_device_id()
                if device_id is None:
                    db_connection.close()
                    return {"success": False, "message": "DeviceNotFound"}
                
                device_id = device_id.upper()
                activation_date_time = self.get_current_ist_datetime()
                logger.info(f"ActivationDateTime: {activation_date_time}")
                
                cursor = db_connection.cursor()
                query = """
                    UPDATE license l 
                    JOIN users u ON l.RegID = u.RegID 
                    SET u.ActiveStatus = 'Y', l.ActiveStatus = 'Y', l.DeviceID = %s, l.ActivationDate = %s 
                    WHERE l.LicenseKey = %s
                """
                cursor.execute(query, (device_id, activation_date_time, license_key))
                db_connection.commit()
                cursor.close()
                db_connection.close()
                
                logger.info("License activated")
                
                license_data = {
                    "RegID": reg_id,
                    "LicenseID": license_id,
                    "LicenseKey": license_key,
                    "ActiveStatus": "Y",
                    "DeviceID": device_id,
                    "ActivationDate": activation_date_time
                }
                
                save_license_result = await self.save_license(license_data)
                if save_license_result["success"]:
                    return {"success": True, "message": "LicenseActivated"}
                else:
                    return {"success": False, "message": "LicenseActivationFailed"}
            else:
                db_connection.close()
                return {"success": False, "message": "LicenseUnknownStatus"}
                
        except Exception as e:
            logger.error(f"Error activating license: {e}")
            if db_connection:
                db_connection.close()
            return {"success": False, "message": "LicenseActivationFailed"}

    async def handle_license_activated(self):
        """Handle license activation completion"""
        # This would be equivalent to destroyLoginWindow() and createMainWindow()
        # Implementation depends on your GUI framework (tkinter, PyQt, etc.)
        logger.info("License activated - transitioning to main window")
        pass


# Usage example:
license_manager = LicenseManager()
validity = license_manager.check_license_validity()
print(validity)
# activation_result = license_manager.activate_license("Z6T5Y2W9X1G0B3K8V7P0N4S2M5J6Q1r7")  