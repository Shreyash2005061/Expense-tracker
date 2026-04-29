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

    # Fetch live data from database
    user_info = get_user_by_id(user_id)
    if user_info is None:
        flash("User not found.", "error")
        session.clear()
        return redirect(url_for("login"))

    # Add initials for avatar display
    user_info['initials'] = ''.join([word[0].upper() for word in user_info['name'].split()])

    # Read and validate date filter params
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    active_preset = None

    # Validate dates
    validated_date_from = None
    validated_date_to = None

    # Compute preset dates for template
    today = datetime.now().date()
    this_month_from = today.replace(day=1)
    last_3_months_from = today - timedelta(days=90)
    last_6_months_from = today - timedelta(days=180)

    if date_from and date_to:
        try:
            parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()

            if parsed_from > parsed_to:
                flash("Start date must be before end date.", "error")
                # Fall back to no filter
            else:
                validated_date_from = date_from
                validated_date_to = date_to

                # Determine active preset
                if parsed_from == this_month_from and parsed_to == today:
                    active_preset = "this_month"
                elif parsed_from == last_3_months_from and parsed_to == today:
                    active_preset = "last_3_months"
                elif parsed_from == last_6_months_from and parsed_to == today:
                    active_preset = "last_6_months"
                else:
                    active_preset = "custom"
        except ValueError:
            # Malformed date, fall back to no filter
            pass

    summary_stats = get_summary_stats(user_id, validated_date_from, validated_date_to)
    transactions = get_recent_transactions(user_id, date_from=validated_date_from, date_to=validated_date_to)
    categories = get_category_breakdown(user_id, validated_date_from, validated_date_to)

    return render_template(
        "profile.html",
        user_info=user_info,
        summary_stats=summary_stats,
        transactions=transactions,
        categories=categories,
        date_from=validated_date_from,
        date_to=validated_date_to,
        active_preset=active_preset,
        today=today.strftime("%Y-%m-%d"),
        this_month_from=this_month_from.strftime("%Y-%m-%d"),
        last_3_months_from=last_3_months_from.strftime("%Y-%m-%d"),
        last_6_months_from=last_6_months_from.strftime("%Y-%m-%d")
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
