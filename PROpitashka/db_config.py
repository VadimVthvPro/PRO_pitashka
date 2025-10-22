"""
Database configuration module for PROpitashka Bot
Centralized PostgreSQL connection settings
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection parameters
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'propitashka'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}


def get_db_connection():
    """
    Create and return a new PostgreSQL database connection
    
    Returns:
        psycopg2.connection: Active database connection
    
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        raise


def get_db_cursor(conn=None):
    """
    Get database cursor. If connection is not provided, creates new one.
    
    Args:
        conn: Existing database connection (optional)
    
    Returns:
        tuple: (connection, cursor)
    """
    if conn is None:
        conn = get_db_connection()
    cursor = conn.cursor()
    return conn, cursor


def close_db_connection(conn, cursor=None):
    """
    Safely close database connection and cursor
    
    Args:
        conn: Database connection
        cursor: Database cursor (optional)
    """
    try:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error closing database connection: {e}")


# Global connection for the bot (used in main.py)
# Single persistent connection for better performance
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Database connection established successfully")
except Exception as e:
    print(f"Failed to establish database connection: {e}")
    conn = None
    cursor = None

