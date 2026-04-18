# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly — A Flask-based personal expense tracker web application using the MVT (Model-View-Template) pattern with SQLite.

## Commands

```bash
# Run the application
python expense-tracker/app.py

# Run tests
pytest

# Install dependencies
pip install -r expense-tracker/requirements.txt
```

## Architecture

```
expense-tracker/
├── app.py              # Flask app: routes + view functions
├── database/
│   └── db.py           # Database layer (sqlite3 connection, init_db, seed_db)
├── static/
│   ├── css/style.css   # Styling (earthy palette, responsive breakpoints at 900px/600px)
│   └── js/main.js      # Frontend JavaScript
└── templates/
    ├── base.html       # Base layout with navbar, footer, Jinja2 blocks
    ├── landing.html    # Homepage
    ├── login.html      # Login page
    └── register.html   # Registration page
```

## Key Patterns

- **Template inheritance**: All pages extend `base.html` using `{% block content %}`
- **URL generation**: Use `url_for('route_name')` instead of hardcoded paths
- **Database**: Plain sqlite3 (no ORM); `db.py` should export `get_db()`, `init_db()`, `seed_db()`
- **Dynamic routes**: `/expenses/<int:id>/edit` captures path parameters

## Current State

Implemented: Landing page, login page, register page (UI only)
Placeholders: `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`
