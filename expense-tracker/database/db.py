import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.path.dirname(__file__), 'spendly.db')


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
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def seed_db():
    """Seed database with demo user and sample expenses."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if users table already has data
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Create demo user
    demo_email = "demo@spendly.com"
    password_hash = generate_password_hash("demo123")
    cursor.execute('''
        INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)
    ''', ("Demo User", demo_email, password_hash))

    user_id = cursor.lastrowid

    # Sample expenses across categories
    sample_expenses = [
        (150.00, "Food", "2026-04-01", "Lunch at office cafeteria"),
        (45.50, "Transport", "2026-04-02", "Metro card recharge"),
        (1200.00, "Bills", "2026-04-03", "Electricity bill"),
        (350.00, "Health", "2026-04-05", "Pharmacy purchase"),
        (800.00, "Entertainment", "2026-04-07", "Movie tickets"),
        (2500.00, "Shopping", "2026-04-10", "New shoes"),
        (75.00, "Food", "2026-04-12", "Coffee and snacks"),
        (200.00, "Other", "2026-04-15", "Miscellaneous"),
    ]

    cursor.executemany('''
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
    ''', [(user_id, *exp) for exp in sample_expenses])

    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    """Get user by ID."""
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()


def get_user_by_email(email):
    """Get user by email address."""
    db = get_db()
    return db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()


def create_user(name, email, password):
    """Create a new user. Returns (success, user_id_or_error_message)."""
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name, email, generate_password_hash(password))
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
    from werkzeug.security import check_password_hash
    if not check_password_hash(user['password_hash'], password):
        return False, "Invalid email or password"
    return True, user
