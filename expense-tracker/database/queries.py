def insert_expense(user_id, amount, category, date, description=None):
    """Insert a new expense record. Returns (success, expense_id_or_error_message)."""
    from database.db import get_db
    import sqlite3

    db = get_db()
    try:
        cursor = db.execute(
            '''
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (user_id, amount, category, date, description)
        )
        db.commit()
        return True, cursor.lastrowid
    except sqlite3.IntegrityError as e:
        return False, f"Database error: {str(e)}"