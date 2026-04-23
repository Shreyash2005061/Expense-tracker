from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from database.db import get_db, init_db, seed_db, create_user, validate_user, close_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.teardown_appcontext(close_db)


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

        # Validation
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

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
            return redirect(url_for("landing"))
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
def profile():
    if 'user_id' not in session:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))
    
    # Hardcoded profile context data
    user_info = {
        'name': session.get('user_name', 'User'),
        'email': session.get('user_email', 'user@example.com'),
        'initials': ''.join([word[0].upper() for word in session.get('user_name', 'User').split()]),
        'member_since': 'January 15, 2024'
    }
    
    # Summary statistics (hardcoded)
    summary_stats = {
        'total_spent': 18240,
        'transaction_count': 34,
        'top_category': 'Food'
    }
    
    # Hardcoded transaction history
    transactions = [
        {'date': 'Apr 18, 2024', 'description': 'Grocery Shopping', 'category': 'Food', 'amount': 850},
        {'date': 'Apr 17, 2024', 'description': 'Uber to Office', 'category': 'Transport', 'amount': 250},
        {'date': 'Apr 16, 2024', 'description': 'Netflix Subscription', 'category': 'Entertainment', 'amount': 199},
        {'date': 'Apr 15, 2024', 'description': 'Coffee at Café', 'category': 'Food', 'amount': 120},
        {'date': 'Apr 14, 2024', 'description': 'Electricity Bill', 'category': 'Utilities', 'amount': 1200},
        {'date': 'Apr 13, 2024', 'description': 'Movie Tickets', 'category': 'Entertainment', 'amount': 500},
    ]
    
    # Hardcoded category breakdown
    categories = [
        {'name': 'Food', 'total': 5840, 'percentage': 32},
        {'name': 'Transport', 'total': 2450, 'percentage': 13},
        {'name': 'Entertainment', 'total': 3120, 'percentage': 17},
        {'name': 'Utilities', 'total': 2800, 'percentage': 15},
        {'name': 'Health', 'total': 1640, 'percentage': 9},
        {'name': 'Shopping', 'total': 1350, 'percentage': 7},
    ]
    
    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        categories=categories
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


@app.context_processor
def inject_user():
    """Make user info available to all templates."""
    return {
        'user': session.get('user_id') and {
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': session.get('user_email')
        }
    }


if __name__ == "__main__":
    init_db()
    seed_db()
    app.run(debug=True, port=5001)
