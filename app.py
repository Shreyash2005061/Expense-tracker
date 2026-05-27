from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from database.db import get_db, init_db, seed_db, create_user, validate_user, close_db
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

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
    # Redirect already logged-in users to profile or the page they tried to access
    if 'user_id' in session:
        redirect_to = request.args.get("redirectTo")
        if redirect_to:
            return redirect(redirect_to)
        return redirect(url_for("profile"))

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
            # Redirect to the page they tried to access, or to profile by default
            redirect_to = request.args.get("redirectTo")
            if redirect_to:
                return redirect(redirect_to)
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
    user_id = session['user_id']
    
    # Get user info
    user_info = get_user_by_id(user_id)
    if user_info is None:
        flash("User not found.", "error")
        session.clear()
        return redirect(url_for("login"))
    
    user_info['initials'] = ''.join([word[0].upper() for word in user_info['name'].split()])

    summary_stats = get_summary_stats(user_id)
    transactions = get_recent_transactions(user_id)
    categories = get_category_breakdown(user_id)

    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        categories=categories
    )


@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")

@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "GET":
        return render_template("add_expense.html")

    # POST handling
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

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
        valid_categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        if category not in valid_categories:
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

    # Handle description
    if not error and description == "":
        description = None

    if error:
        return render_template("add_expense.html",
                               error=error,
                               amount=amount,
                               category=category,
                               date=date,
                               description=description)

    # Insert into DB
    from database.queries import insert_expense
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

    return redirect(url_for("profile"))


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
