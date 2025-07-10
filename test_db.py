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
        
        # Try using a raw SQL query
        print("\nTrying direct SQL query with specific column names:")
        try:
            cursor.execute("""
                SELECT DeviceType, DeviceNumber, IP, Port, DeviceLocation, ComUser, 
                       Enable, DevicePrinterIP
                FROM configh
                LIMIT 3
            """)
            raw_rows = cursor.fetchall()
            print(f"Retrieved {len(raw_rows)} rows with direct column selection")
            
            for i, row in enumerate(raw_rows):
                print(f"\nRow {i+1}:")
                print(json.dumps(row, default=str, indent=2))
                
        except mysql.connector.Error as sql_err:
            print(f"SQL query error: {sql_err}")
        
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return False

if __name__ == "__main__":
    test_connection() 