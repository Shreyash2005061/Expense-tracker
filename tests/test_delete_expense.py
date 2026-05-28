import os
import sqlite3
import pytest
from werkzeug.security import generate_password_hash

from app import app
from database.queries import delete_expense, get_expense_by_id

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'expense_tracker.db'))
TEST_EMAIL = 'delete-test@backend.com'
TEST_PASSWORD = 'deletepass123'
OTHER_EMAIL = 'delete-test-other@backend.com'
OTHER_PASSWORD = 'otherpass123'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def test_user_id(db_connection):
    cursor = db_connection.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (TEST_EMAIL,))
    row = cursor.fetchone()
    if row:
        return row['id']

    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Delete Test User', TEST_EMAIL, generate_password_hash(TEST_PASSWORD))
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def other_user_id(db_connection):
    cursor = db_connection.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (OTHER_EMAIL,))
    row = cursor.fetchone()
    if row:
        return row['id']

    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Other Delete User', OTHER_EMAIL, generate_password_hash(OTHER_PASSWORD))
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def owned_expense_id(db_connection, test_user_id):
    cursor = db_connection.cursor()
    cursor.execute(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        (test_user_id, 42.50, 'Food', '2026-05-01', 'Delete test expense')
    )
    db_connection.commit()
    expense_id = cursor.lastrowid
    try:
        yield expense_id
    finally:
        cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        db_connection.commit()


@pytest.fixture
def other_user_expense_id(db_connection, other_user_id):
    cursor = db_connection.cursor()
    cursor.execute(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        (other_user_id, 75.00, 'Transport', '2026-05-02', 'Other user expense')
    )
    db_connection.commit()
    expense_id = cursor.lastrowid
    try:
        yield expense_id
    finally:
        cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        db_connection.commit()


def login(client, email, password):
    response = client.post('/login', data={'email': email, 'password': password}, follow_redirects=False)
    assert response.status_code == 302
    return response


class TestDeleteExpenseQuery:
    def test_delete_owned_expense(self, db_connection, owned_expense_id, test_user_id):
        assert get_expense_by_id(owned_expense_id, test_user_id) is not None
        result = delete_expense(owned_expense_id, test_user_id)
        assert result is True

        cursor = db_connection.cursor()
        cursor.execute('SELECT id FROM expenses WHERE id = ?', (owned_expense_id,))
        assert cursor.fetchone() is None

    def test_delete_other_user_expense_returns_false(self, db_connection, other_user_expense_id, test_user_id):
        result = delete_expense(other_user_expense_id, test_user_id)
        assert result is False

        cursor = db_connection.cursor()
        cursor.execute('SELECT id FROM expenses WHERE id = ?', (other_user_expense_id,))
        assert cursor.fetchone() is not None

    def test_delete_non_existent_expense_returns_false(self, db_connection, test_user_id):
        result = delete_expense(9999999, test_user_id)
        assert result is False


class TestDeleteExpenseRoute:
    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post('/expenses/1/delete')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_get_delete_endpoint_returns_405(self, client, test_user_id):
        login(client, TEST_EMAIL, TEST_PASSWORD)
        response = client.get('/expenses/1/delete')
        assert response.status_code == 405

    def test_authenticated_delete_own_expense(self, client, db_connection, test_user_id, owned_expense_id):
        login(client, TEST_EMAIL, TEST_PASSWORD)
        response = client.post(f'/expenses/{owned_expense_id}/delete', follow_redirects=False)
        assert response.status_code == 302
        assert '/profile' in response.location

        cursor = db_connection.cursor()
        cursor.execute('SELECT id FROM expenses WHERE id = ?', (owned_expense_id,))
        assert cursor.fetchone() is None

    def test_authenticated_delete_other_user_expense_returns_404(self, client, db_connection, test_user_id, other_user_expense_id):
        login(client, TEST_EMAIL, TEST_PASSWORD)
        response = client.post(f'/expenses/{other_user_expense_id}/delete')
        assert response.status_code == 404

        cursor = db_connection.cursor()
        cursor.execute('SELECT id FROM expenses WHERE id = ?', (other_user_expense_id,))
        assert cursor.fetchone() is not None

    def test_authenticated_delete_non_existent_expense_returns_404(self, client, test_user_id):
        login(client, TEST_EMAIL, TEST_PASSWORD)
        response = client.post('/expenses/9999999/delete')
        assert response.status_code == 404
