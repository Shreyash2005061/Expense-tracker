import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), '..', 'expense_tracker.db')


def get_db():
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '◎',
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER,
            category_name TEXT NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    ''')

    conn.commit()
    conn.close()


def seed_db():
    """Seed database with default categories."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    default_categories = [
        ('Food', '◎'),
        ('Transport', '◷'),
        ('Bills', '₹'),
        ('Health', '♥'),
        ('Shopping', '◎'),
        ('Entertainment', '★'),
        ('Education', '◎'),
        ('Personal', '◷'),
    ]

    for name, icon in default_categories:
        cursor.execute(
            'INSERT OR IGNORE INTO categories (name, icon) VALUES (?, ?)',
            (name, icon)
        )

    conn.commit()
    conn.close()


def get_user_by_email(email):
    """Get user by email address."""
    db = get_db()
    return db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()


def create_user(name, email, password):
    """Create a new user. Returns (success, user_id_or_error_message)."""
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
            (name, email, password)
        )
        db.commit()
        return True, cursor.lastrowid
    except sqlite3.IntegrityError:
        return False, "Email already registered"


def validate_user(email, password):
    """Validate user credentials. Returns (success, user_or_error_message)."""
    user = get_user_by_email(email)
    if user is None:
        return False, "Invalid email or password"
    if user['password'] != password:
        return False, "Invalid email or password"
    return True, user
