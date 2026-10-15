import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from database import init_db, get_db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key-workbase")

# Initialize SQLite database on startup
init_db()

# Register modular blueprints
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.student import student_bp

app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)

@app.route("/")
def index():
    """
    Root entry point.
    If college geofence settings are not yet configured, routes to Admin Setup.
    Otherwise, routes to Admin Dashboard.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admin_settings LIMIT 1")
    settings = cursor.fetchone()
    conn.close()

    if not settings:
        return redirect(url_for("admin.setup"))
    return redirect(url_for("admin.dashboard"))


@app.route("/dashboard")
def student_dashboard_redirect():
    """Convenience alias pointing directly to student dashboard."""
    return redirect(url_for("student.dashboard"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host="127.0.0.1", port=port)
