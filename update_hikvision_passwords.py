import mysql.connector
import argparse
import sys
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox, QLineEdit

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

def db_connect():
    """Connect to MySQL database"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            port=DB_PORT,
            password=DB_PASS,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def update_hikvision_passwords(password, show_ui=True):
    """Update passwords for all Hikvision devices using proper encryption"""
    try:
        conn = db_connect()
        if not conn:
            print("Failed to connect to database")
            return False
                
        cursor = conn.cursor()
        
        # Update Hikvision device passwords
        sql = """
        UPDATE configh 
        SET comKey = AES_ENCRYPT(%s, SHA2(CONCAT('pg2175', CreatedDateTime), 512)) 
        WHERE LCASE(DeviceType) = 'hikvision'
        """
        
        cursor.execute(sql, (password,))
        rows_affected = cursor.rowcount
        conn.commit()
        
        if show_ui:
            app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            QMessageBox.information(None, "Password Update", 
                f"Updated passwords for {rows_affected} Hikvision devices.")
        else:
            print(f"Success: Updated passwords for {rows_affected} Hikvision devices.")
        
        return True
    except mysql.connector.Error as err:
        if show_ui:
            app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            QMessageBox.critical(None, "Database Error", f"Failed to update Hikvision passwords: {str(err)}")
        else:
            print(f"Error: Failed to update Hikvision passwords: {err}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description='Update passwords for all Hikvision devices')
    parser.add_argument('-p', '--password', help='Password to set for devices (if not provided, will prompt)')
    parser.add_argument('-c', '--console', action='store_true', help='Run in console mode (no GUI)')
    args = parser.parse_args()
    
    if args.password:
        # Use password from command line
        password = args.password
        show_ui = not args.console
        update_hikvision_passwords(password, show_ui)
    else:
        # Prompt for password
        if args.console:
            # Console mode
            password = input("Enter password for Hikvision devices: ")
            update_hikvision_passwords(password, False)
        else:
            # GUI mode
            app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            password, ok = QInputDialog.getText(None, "Password Input", 
                                              "Enter password for Hikvision devices:", 
                                              QLineEdit.Password)
            if ok and password:
                update_hikvision_passwords(password)

if __name__ == "__main__":
    main() 