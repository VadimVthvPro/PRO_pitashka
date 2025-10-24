"""
Database configuration module for PROpitashka Bot
Centralized PostgreSQL connection settings
"""
import psycopg2
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import config

# PostgreSQL connection parameters (from centralized config)
DB_CONFIG = config.get_db_config(admin=False)


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

