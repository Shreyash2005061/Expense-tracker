from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from functools import wraps
from database.db import get_db, init_db, seed_db, create_user, validate_user, get_user_by_id
from database.queries import (
    insert_expense,
    get_expense_by_id,
    update_expense,
    get_recent_transactions,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters")

        success, result = create_user(name, email, password)
        if success:
            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for("login"))
        else:
            return render_template("register.html", error=result)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, send to profile
    if 'user_id' in session:
        return redirect(url_for('profile'))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Validation
        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        success, result = validate_user(email, password)
        if success:
            session["user_id"] = result["id"]
            session["user_name"] = result["name"]
            session["user_email"] = result["email"]
            # Redirect to profile after login
            return redirect(url_for("profile"))
        else:
            return render_template("login.html", error=result)

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/profile")
@login_required
def profile():
    user = get_user_by_id(session['user_id'])
    transactions = get_recent_transactions(session['user_id'])
    return render_template("profile.html", user=user, transactions=transactions)


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "GET":
        return render_template("add_expense.html")

    # POST request handling
    # Extract form data
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    # Validation
    error = None

    # Validate amount
    if not amount:
        error = "Amount is required"
    else:
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                error = "Amount must be greater than 0"
        except ValueError:
            error = "Amount must be a valid number"

    # Validate category
    if not error and not category:
        error = "Category is required"
    elif not error:
        if category not in VALID_CATEGORIES:
            error = "Invalid category selected"

    # Validate date
    if not error and not date:
        error = "Date is required"
    elif not error:
        try:
            from datetime import datetime
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            error = "Date must be in YYYY-MM-DD format"

    # Handle description (optional)
    if not error and description == "":
        description = None

    # If validation fails, re-render form with error and preserved values
    if error:
        return render_template("add_expense.html",
                             error=error,
                             amount=amount,
                             category=category,
                             date=date,
                             description=description)

    # Insert expense into database
    success, result = insert_expense(
        session["user_id"],
        float(amount),
        category,
        date,
        description
    )

    if not success:
        return render_template("add_expense.html",
                             error=result,
                             amount=amount,
                             category=category,
                             date=date,
                             description=description)

    # Success - redirect to profile
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = get_expense_by_id(id, session['user_id'])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
        )

    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    error = None

    if not amount:
        error = "Amount is required"
    else:
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                error = "Amount must be greater than 0"
        except ValueError:
            error = "Amount must be a valid number"

    if not error and not category:
        error = "Category is required"
    elif not error and category not in VALID_CATEGORIES:
        error = "Invalid category selected"

    if not error and not date:
        error = "Date is required"
    elif not error:
        try:
            from datetime import datetime
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            error = "Date must be in YYYY-MM-DD format"

    if not error and description == "":
        description = None

    if error:
        return render_template(
            "edit_expense.html",
            error=error,
            expense={
                'id': id,
                'amount': amount,
                'category': category,
                'date': date,
                'description': description,
            }
        )

    success, result = update_expense(
        id,
        session['user_id'],
        float(amount),
        category,
        date,
        description
    )

    if not success:
        return render_template(
            "edit_expense.html",
            error=result,
            expense={
                'id': id,
                'amount': amount,
                'category': category,
                'date': date,
                'description': description,
            }
        )

    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


@app.route("/analytics")
@login_required
def analytics():
    # UI-first mode: render profile with hardcoded data per spec 04-profile-page.md
    user_info = {
        'name': session.get('user_name', 'Demo User'),
        'email': session.get('user_email', 'demo@spendly.com'),
        'member_since': 'April 2026'
    }
    user_info['initials'] = ''.join([word[0].upper() for word in user_info['name'].split()])

    summary_stats = {
        'total_spent': 1067.00,
        'transaction_count': 8,
        'top_category': 'Food'
    }

    transactions = [
        {'date': '2026-04-10', 'description': 'Grocery shopping', 'category': 'Food', 'amount': 320.00},
        {'date': '2026-04-08', 'description': 'Monthly bus pass', 'category': 'Transport', 'amount': 150.00},
        {'date': '2026-04-05', 'description': 'Electricity bill', 'category': 'Bills', 'amount': 597.00},
    ]

    categories = [
        {'name': 'Food', 'amount': 320.00, 'percentage': 30},
        {'name': 'Transport', 'amount': 150.00, 'percentage': 14},
        {'name': 'Bills', 'amount': 597.00, 'percentage': 56},
    ]

    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        categories=categories
    )
