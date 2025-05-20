import mysql.connector
import json

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

def test_connection():
    try:
        print(f"Testing connection to {DB_HOST}:{DB_PORT}...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            port=DB_PORT,
            password=DB_PASS,
            database=DB_NAME
        )
        print("Connection successful!")
        
        # Get database version
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"Database version: {version[0]}")
        
        # Check table structure using information_schema for accurate column names
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'configh'
            ORDER BY ORDINAL_POSITION
        """, (DB_NAME,))
        
        columns = cursor.fetchall()
        print("\nConfigh table structure from information_schema:")
        for col in columns:
            print(f"- {col[0]} ({col[1]}, {col[2]}, {col[3]})")
        
        # Get actual data with column names
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM configh LIMIT 3")
        rows = cursor.fetchall()
        
        print("\nSample data from configh table:")
        for i, row in enumerate(rows):
            print(f"\nRow {i+1} keys: {list(row.keys())}")
            # Print a few key fields
            for key in ['DeviceType', 'DeviceNumber', 'IP', 'Enable', 'DevicePrinterIP']:
                if key in row:
                    print(f"- {key}: {row[key]}")
                else:
                    print(f"- {key}: [KEY NOT FOUND]")
        
        # Get count of devices by type
        cursor.execute("""
            SELECT DeviceType, COUNT(*) as Count
            FROM configh
            GROUP BY DeviceType
            ORDER BY DeviceType
        """)
        type_counts = cursor.fetchall()
        print("\nDevice counts by type:")
        for type_count in type_counts:
            print(f"- {type_count['DeviceType']}: {type_count['Count']}")
            
        # Fetch all devices and printers for display
        cursor.execute("""
            SELECT 
                DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                Enable, DevicePrinterIP
            FROM configh
            ORDER BY DeviceType, DeviceNumber
        """)
        devices = cursor.fetchall()
        
        printers = []
        other_devices = []
        
        for device in devices:
            if device['DeviceType'] == 'Printer':
                printers.append(device)
            else:
                other_devices.append(device)
                
        print(f"\nFound {len(printers)} printers and {len(other_devices)} other devices")
        
        # Print sample printer
        if printers:
            print("\nSample printer:")
            print(json.dumps(printers[0], default=str, indent=2))
            
        # Print sample device
        if other_devices:
            print("\nSample device:")
            print(json.dumps(other_devices[0], default=str, indent=2))
        
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return False

if __name__ == "__main__":
    test_connection() 