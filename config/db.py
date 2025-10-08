import MySQLdb
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a MySQL database connection"""
    return MySQLdb.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )

def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                age INT NOT NULL,
                location VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Database tables initialized successfully!")
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")

def create_user(first_name, last_name, email, age, location, password_hash):
    """
    Create a new user in the database
    Returns: (success: bool, message: str, user_id: int or None)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            return (False, 'Email already registered', None)
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, age, location, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, age, location, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return (True, 'User created successfully', user_id)
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return (False, 'An error occurred during registration', None)

def get_user_by_email(email):
    """
    Get user by email
    Returns: dict or None
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return user
        
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def get_user_by_id(user_id):
    """
    Get user by ID
    Returns: dict or None
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return user
        
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def update_user(user_id, first_name, last_name, age, location):
    """
    Update user information
    Returns: (success: bool, message: str)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET first_name = %s, last_name = %s, age = %s, location = %s
            WHERE id = %s
        ''', (first_name, last_name, age, location, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return (True, 'User updated successfully')
        
    except Exception as e:
        print(f"Error updating user: {e}")
        return (False, 'An error occurred while updating profile')

def delete_user(user_id):
    """
    Delete user by ID
    Returns: (success: bool, message: str)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return (True, 'User deleted successfully')
        
    except Exception as e:
        print(f"Error deleting user: {e}")
        return (False, 'An error occurred while deleting user')

def get_all_users():
    """
    Get all users
    Returns: list of dicts
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT id, first_name, last_name, email, age, location, created_at FROM users')
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return users
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []