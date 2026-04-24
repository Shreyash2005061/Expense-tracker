import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'expense_tracker.db')


def _get_connection():
    """Get a database connection with proper settings."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_by_id(user_id):
    """Get user info by ID. Returns dict with name, email, member_since or None if not found."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT name, email, created_at FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return None

    # Format created_at as "Month YYYY"
    from datetime import datetime
    created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
    member_since = created_at.strftime('%B %Y')

    result = {
        'name': row['name'],
        'email': row['email'],
        'member_since': member_since
    }

    conn.close()
    return result


def get_summary_stats(user_id):
    """Get summary statistics for a user. Returns dict with total_spent, transaction_count, top_category."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Get total spent and transaction count
    cursor.execute('''
        SELECT SUM(amount) as total, COUNT(*) as count
        FROM expenses
        WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()

    total_spent = row['total'] if row['total'] else 0
    transaction_count = row['count'] if row['count'] else 0

    if transaction_count == 0:
        conn.close()
        return {
            'total_spent': 0,
            'transaction_count': 0,
            'top_category': '—'
        }

    # Get top category (highest total spending)
    cursor.execute('''
        SELECT category, SUM(amount) as category_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY category_total DESC
        LIMIT 1
    ''', (user_id,))
    top_row = cursor.fetchone()
    top_category = top_row['category'] if top_row else '—'

    conn.close()
    return {
        'total_spent': total_spent,
        'transaction_count': transaction_count,
        'top_category': top_category
    }


def get_recent_transactions(user_id, limit=10):
    """Get recent transactions for a user. Returns list of dicts ordered newest-first."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
    ''', (user_id, limit))

    rows = cursor.fetchall()

    transactions = []
    for row in rows:
        transactions.append({
            'date': row['date'],
            'description': row['description'],
            'category': row['category'],
            'amount': row['amount']
        })

    conn.close()
    return transactions


def get_category_breakdown(user_id):
    """Get category breakdown for a user. Returns list of dicts with name, amount, percentage (sums to 100)."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Get total spent
    cursor.execute('''
        SELECT SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
    ''', (user_id,))
    total_row = cursor.fetchone()
    grand_total = total_row['total'] if total_row['total'] else 0

    if grand_total == 0:
        conn.close()
        return []

    # Get category totals
    cursor.execute('''
        SELECT category, SUM(amount) as category_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY category_total DESC
    ''', (user_id,))

    rows = cursor.fetchall()

    categories = []
    percentages = []

    for row in rows:
        raw_pct = (row['category_total'] / grand_total) * 100
        categories.append({
            'name': row['category'],
            'amount': row['category_total'],
            'pct': raw_pct
        })
        percentages.append(raw_pct)

    # Round percentages to integers
    for cat in categories:
        cat['pct'] = round(cat['pct'])

    # Adjust for rounding error to ensure sum is 100
    pct_sum = sum(cat['pct'] for cat in categories)
    if pct_sum != 100 and categories:
        # Find the largest category by amount and adjust
        largest_idx = max(range(len(categories)), key=lambda i: categories[i]['amount'])
        categories[largest_idx]['pct'] += (100 - pct_sum)

    # Remove raw pct and keep only integer
    result = []
    for cat in categories:
        result.append({
            'name': cat['name'],
            'amount': cat['amount'],
            'percentage': cat['pct']
        })

    conn.close()
    return result
