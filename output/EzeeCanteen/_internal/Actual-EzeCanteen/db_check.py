import mysql.connector

# Database configuration
DB_HOST = "103.216.211.36"
DB_USER = "pgcanteen"
DB_PORT = 33975
DB_PASS = "L^{Z,8~zzfF9(nd8"
DB_NAME = "payguru_canteen"

def main():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            port=DB_PORT,
            password=DB_PASS,
            database=DB_NAME
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # Check device types in the database
        print("Device types in the database:")
        cursor.execute("SELECT DeviceType, COUNT(*) as count FROM configh GROUP BY DeviceType")
        device_types = cursor.fetchall()
        for device_type in device_types:
            print(f"- {device_type['DeviceType']}: {device_type['count']}")
        
        # Get sample data from configh table
        print("\nSample data from configh table:")
        cursor.execute("SELECT * FROM configh LIMIT 5")
        sample_data = cursor.fetchall()
        for row in sample_data:
            print(f"ID: {row.get('ID')}, Type: {row.get('DeviceType')}, Number: {row.get('DeviceNumber')}, IP: {row.get('IP')}, Enable: {row.get('Enable')}")
        
        # Check specifically for Device type entries
        print("\nLooking for Device (non-Printer) entries:")
        cursor.execute("SELECT * FROM configh WHERE DeviceType <> 'Printer'")
        devices = cursor.fetchall()
        if devices:
            for device in devices:
                print(f"ID: {device.get('ID')}, Type: {device.get('DeviceType')}, Number: {device.get('DeviceNumber')}, IP: {device.get('IP')}, Enable: {device.get('Enable')}")
        else:
            print("No non-Printer devices found in the database!")
        
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")

if __name__ == "__main__":
    main() 