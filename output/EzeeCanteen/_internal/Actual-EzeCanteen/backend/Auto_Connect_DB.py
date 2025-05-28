import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, Any
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._pool:
            self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            db_config = {
                "host": "103.216.211.36",
                "port": "33975",
                "user": "pgcanteen",
                "password": "L^{Z,8~zzfF9(nd8",
                "database": "payguru_canteen",
                "pool_name": "mypool",
                "pool_size": 5
            }
            
            self._pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
            logger.info("Connection pool initialized successfully")
        except Error as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            connection = self._pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[list]:
        """Execute a query and return results."""
        try:
            with self.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(query, params or ())
                    if query.strip().upper().startswith(('SELECT', 'SHOW')):
                        return cursor.fetchall()
                    connection.commit()
                    return None
        except Error as e:
            logger.error(f"Error executing query: {e}")
            raise

    def check_connection(self) -> Dict[str, Any]:
        """Check database connection and return server information."""
        try:
            with self.get_connection() as connection:
                server_info = {
                    'version': connection.server_info,
                    'database': connection.database,
                    'connected': connection.is_connected()
                }
                logger.info(f"Successfully connected to MySQL Server version {server_info['version']}")
                logger.info(f"Connected to database: {server_info['database']}")
                return server_info
        except Error as e:
            logger.error(f"Error checking connection: {e}")
            raise

def main():
    try:
        # Create database connection instance
        db = DatabaseConnection()
        
        # Check connection
        connection_info = db.check_connection()
        
        # Example query
        result = db.execute_query("SELECT VERSION()")
        if result:
            logger.info(f"Database version: {result[0]['VERSION()']}")
            
    except Error as e:
        logger.error(f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()