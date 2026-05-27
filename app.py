import calendar
from datetime import date, datetime

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


def _parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _subtract_months(source_date, months):
    year = source_date.year
    month = source_date.month - months
    while month <= 0:
        month += 12
        year -= 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(source_date.day, last_day)
    return date(year, month, day)


@app.route("/profile")
@login_required
def profile():
    user_id = session['user_id']

    # Fetch live user data
    user_info = get_user_by_id(user_id)
    if user_info is None:
        flash("User not found.", "error")
        session.clear()
        return redirect(url_for("login"))

    user_info['initials'] = ''.join([word[0].upper() for word in user_info['name'].split()])

    # Date filter query params
    requested_date_from = request.args.get("date_from")
    requested_date_to = request.args.get("date_to")

    parsed_date_from = _parse_iso_date(requested_date_from)
    parsed_date_to = _parse_iso_date(requested_date_to)

    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        flash("Start date must be before end date.", "error")
        parsed_date_from = None
        parsed_date_to = None

    if not (parsed_date_from and parsed_date_to):
        parsed_date_from = None
        parsed_date_to = None

    date_from = parsed_date_from.isoformat() if parsed_date_from else None
    date_to = parsed_date_to.isoformat() if parsed_date_to else None

    today = date.today()
    this_month_start = today.replace(day=1)
    three_months_ago = _subtract_months(today, 3)
    six_months_ago = _subtract_months(today, 6)

    preset_ranges = {
        'this_month': {
            'date_from': this_month_start.isoformat(),
            'date_to': today.isoformat()
        },
        'last_3_months': {
            'date_from': three_months_ago.isoformat(),
            'date_to': today.isoformat()
        },
        'last_6_months': {
            'date_from': six_months_ago.isoformat(),
            'date_to': today.isoformat()
        }
    }

    if date_from == preset_ranges['this_month']['date_from'] and date_to == preset_ranges['this_month']['date_to']:
        active_filter = 'this_month'
    elif date_from == preset_ranges['last_3_months']['date_from'] and date_to == preset_ranges['last_3_months']['date_to']:
        active_filter = 'last_3_months'
    elif date_from == preset_ranges['last_6_months']['date_from'] and date_to == preset_ranges['last_6_months']['date_to']:
        active_filter = 'last_6_months'
    elif date_from and date_to:
        active_filter = 'custom'
    else:
        active_filter = 'all'

    summary_stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)

    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        active_filter=active_filter,
        preset_ranges=preset_ranges
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
