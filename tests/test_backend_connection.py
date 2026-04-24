import pytest
import sqlite3
import os
from werkzeug.security import generate_password_hash

from app import app
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown
)

DATABASE_PATH = os.path.join('database', '..', 'expense_tracker.db')


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_connection():
    """Create a database connection for test setup."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def test_user_id(db_connection):
    """Create a test user and return their ID."""
    cursor = db_connection.cursor()

    # Check if test user already exists
    cursor.execute('SELECT id FROM users WHERE email = ?', ('test@backend.com',))
    row = cursor.fetchone()
    if row:
        return row['id']

    # Create test user
    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Test Backend User', 'test@backend.com', generate_password_hash('testpass123'))
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def test_user_with_expenses(db_connection, test_user_id):
    """Add test expenses for the test user."""
    cursor = db_connection.cursor()

    # Check if expenses already exist for this user
    cursor.execute('SELECT COUNT(*) FROM expenses WHERE user_id = ?', (test_user_id,))
    if cursor.fetchone()[0] > 0:
        return test_user_id

    # Add test expenses
    test_expenses = [
        (100.00, 'Food', '2026-04-01', 'Test lunch'),
        (200.00, 'Transport', '2026-04-02', 'Test taxi'),
        (300.00, 'Food', '2026-04-03', 'Test dinner'),
        (50.00, 'Health', '2026-04-04', 'Test pharmacy'),
        (150.00, 'Entertainment', '2026-04-05', 'Test movie'),
    ]

    for amount, category, date, description in test_expenses:
        cursor.execute(
            'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
            (test_user_id, amount, category, date, description)
        )

    db_connection.commit()
    return test_user_id


def cleanup_test_data(db_connection, test_user_id):
    """Clean up test data after tests."""
    cursor = db_connection.cursor()
    cursor.execute('DELETE FROM expenses WHERE user_id = ?', (test_user_id,))
    cursor.execute('DELETE FROM users WHERE email = ?', ('test@backend.com',))
    db_connection.commit()


# =============================================================================
# Unit Tests for Query Functions
# =============================================================================

class TestGetUserById:
    """Tests for get_user_by_id function."""

    def test_valid_user_id(self, db_connection):
        """Test get_user_by_id with a valid user ID."""
        user = get_user_by_id(1)  # Demo user

        assert user is not None
        assert user['name'] == 'Demo User'
        assert user['email'] == 'demo@spendly.com'
        assert 'member_since' in user
        assert isinstance(user['member_since'], str)
        # Should be in "Month YYYY" format
        assert len(user['member_since'].split()) == 2

    def test_non_existent_user_id(self):
        """Test get_user_by_id with a non-existent user ID."""
        user = get_user_by_id(99999)
        assert user is None


class TestGetSummaryStats:
    """Tests for get_summary_stats function."""

    def test_user_with_expenses(self, db_connection, test_user_with_expenses):
        """Test get_summary_stats for a user with expenses."""
        stats = get_summary_stats(test_user_with_expenses)

        assert stats['total_spent'] == 800.00  # 100+200+300+50+150
        assert stats['transaction_count'] == 5
        assert stats['top_category'] == 'Food'  # 400 total

    def test_user_with_no_expenses(self, test_user_id):
        """Test get_summary_stats for a user with no expenses."""
        stats = get_summary_stats(test_user_id)

        assert stats['total_spent'] == 0
        assert stats['transaction_count'] == 0
        assert stats['top_category'] == '—'


class TestGetRecentTransactions:
    """Tests for get_recent_transactions function."""

    def test_user_with_expenses(self, db_connection, test_user_with_expenses):
        """Test get_recent_transactions returns expenses in newest-first order."""
        transactions = get_recent_transactions(test_user_with_expenses)

        assert len(transactions) == 5

        # Verify newest-first ordering
        dates = [t['date'] for t in transactions]
        assert dates == sorted(dates, reverse=True)

        # Verify each transaction has required fields
        for txn in transactions:
            assert 'date' in txn
            assert 'description' in txn
            assert 'category' in txn
            assert 'amount' in txn

    def test_user_with_no_expenses(self, test_user_id):
        """Test get_recent_transactions for a user with no expenses."""
        transactions = get_recent_transactions(test_user_id)
        assert transactions == []

    def test_limit_parameter(self, db_connection, test_user_with_expenses):
        """Test that the limit parameter restricts results."""
        transactions = get_recent_transactions(test_user_with_expenses, limit=3)
        assert len(transactions) == 3


class TestGetCategoryBreakdown:
    """Tests for get_category_breakdown function."""

    def test_user_with_expenses(self, db_connection, test_user_with_expenses):
        """Test get_category_breakdown for a user with expenses."""
        categories = get_category_breakdown(test_user_with_expenses)

        assert len(categories) == 4  # Food, Transport, Health, Entertainment

        # Verify ordering by amount descending
        amounts = [c['amount'] for c in categories]
        assert amounts == sorted(amounts, reverse=True)

        # Verify percentages sum to 100
        total_pct = sum(c['percentage'] for c in categories)
        assert total_pct == 100

        # Verify each category has required fields
        for cat in categories:
            assert 'name' in cat
            assert 'amount' in cat
            assert 'percentage' in cat
            assert isinstance(cat['percentage'], int)

    def test_user_with_no_expenses(self, test_user_id):
        """Test get_category_breakdown for a user with no expenses."""
        categories = get_category_breakdown(test_user_id)
        assert categories == []


# =============================================================================
# Route Tests
# =============================================================================

class TestProfileRoute:
    """Tests for the /profile route."""

    def test_unauthenticated_redirects_to_login(self, client):
        """Test that unauthenticated users are redirected to login."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_authenticated_user_sees_profile(self, client, db_connection):
        """Test that authenticated users can access their profile."""
        # Login as demo user
        response = client.post('/login', data={
            'email': 'demo@spendly.com',
            'password': 'demo123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Demo User' in response.data
        assert b'demo@spendly.com' in response.data

    def test_profile_displays_rupee_symbol(self, client):
        """Test that the profile page displays the rupee symbol."""
        # Login as demo user
        client.post('/login', data={
            'email': 'demo@spendly.com',
            'password': 'demo123'
        }, follow_redirects=True)

        response = client.get('/profile')
        assert b'\xe2\x82\xb9' in response.data  # UTF-8 encoding of ₹

    def test_profile_displays_correct_total(self, client):
        """Test that total_spent matches sum of demo user expenses."""
        client.post('/login', data={
            'email': 'demo@spendly.com',
            'password': 'demo123'
        }, follow_redirects=True)

        response = client.get('/profile')
        # Total should be 1067.0 (sum of 8 seed expenses)
        assert b'1,067' in response.data or b'1067' in response.data

    def test_profile_displays_transaction_count(self, client):
        """Test that transaction count is displayed."""
        client.post('/login', data={
            'email': 'demo@spendly.com',
            'password': 'demo123'
        }, follow_redirects=True)

        response = client.get('/profile')
        assert b'8' in response.data  # 8 transactions

    def test_new_user_sees_zeros(self, client, db_connection):
        """Test that a new user with no expenses sees zeros."""
        # Create new user
        cursor = db_connection.cursor()
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            ('New User', 'newuser@test.com', generate_password_hash('newpass123'))
        )
        db_connection.commit()

        # Login as new user
        client.post('/login', data={
            'email': 'newuser@test.com',
            'password': 'newpass123'
        }, follow_redirects=True)

        response = client.get('/profile')
        assert response.status_code == 200
        assert b'0' in response.data

        # Cleanup
        cursor.execute('DELETE FROM users WHERE email = ?', ('newuser@test.com',))
        db_connection.commit()
