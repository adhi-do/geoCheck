from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from database import get_db
from utils.geo import haversine_distance

student_bp = Blueprint("student", __name__, url_prefix="/student")

def login_required(f):
    """Decorator to protect student routes requiring an active session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in with your Roll Number or Email to access your dashboard.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route("/dashboard", methods=["GET"])
@student_bp.route("/", methods=["GET"])
@login_required
def dashboard():
    """
    Student dashboard displaying:
    - Student details (Roll number, Email)
    - College geofence overview
    - Today's attendance status & Mark Attendance action
    - Student's personal attendance history
    """
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Get student record
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        session.clear()
        flash("Student account could not be found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    # Get college admin settings
    cursor.execute("SELECT * FROM admin_settings LIMIT 1")
    settings = cursor.fetchone()

    # Check today's attendance
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ? LIMIT 1", (user_id, today))
    today_attendance = cursor.fetchone()

    # Get attendance history
    cursor.execute("""
        SELECT id, date, status 
        FROM attendance 
        WHERE user_id = ? 
        ORDER BY date DESC, id DESC 
        LIMIT 60
    """, (user_id,))
    history = cursor.fetchall()

    # Total days attended
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE user_id = ? AND status = 'Present'", (user_id,))
    total_present_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "student_dashboard.html",
        user=user,
        settings=settings,
        today=today,
        today_attendance=today_attendance,
        history=history,
        total_present_count=total_present_count
    )


@student_bp.route("/mark-attendance", methods=["POST"])
@login_required
def mark_attendance():
    """
    API endpoint for geolocation verification and attendance marking.
    Receives JSON { latitude: float, longitude: float }.
    Calculates Haversine distance from college center point.
    If within allowed radius: records 'Present' in SQLite attendance table.
    If outside: rejects attendance with detailed distance feedback.
    """
    user_id = session.get("user_id")
    data = request.get_json(silent=True) or {}

    lat_raw = data.get("latitude")
    lon_raw = data.get("longitude")

    if lat_raw is None or lon_raw is None:
        return jsonify({
            "success": False,
            "message": "Missing GPS coordinates in request."
        }), 400

    try:
        student_lat = float(lat_raw)
        student_lon = float(lon_raw)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid coordinates format."
        }), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin_settings LIMIT 1")
    settings = cursor.fetchone()

    if not settings:
        conn.close()
        return jsonify({
            "success": False,
            "message": "College geolocation settings have not been configured by an administrator yet."
        }), 400

    college_lat = float(settings["latitude"])
    college_lon = float(settings["longitude"])
    allowed_radius = float(settings["radius_meters"])
    college_name = settings["college_name"]

    # Calculate distance using pure Python Haversine formula
    distance_meters = haversine_distance(student_lat, student_lon, college_lat, college_lon)
    distance_rounded = round(distance_meters, 1)

    today = datetime.now().strftime("%Y-%m-%d")

    if distance_meters <= allowed_radius:
        # Check if already recorded for today
        cursor.execute("SELECT id, status FROM attendance WHERE user_id = ? AND date = ?", (user_id, today))
        existing_record = cursor.fetchone()

        if existing_record:
            cursor.execute(
                "UPDATE attendance SET status = 'Present' WHERE id = ?",
                (existing_record["id"],)
            )
            success_msg = (
                f"Attendance updated! You are verified inside {college_name} "
                f"({distance_rounded}m from center). Status: Present."
            )
        else:
            cursor.execute(
                "INSERT INTO attendance (user_id, date, status) VALUES (?, ?, 'Present')",
                (user_id, today)
            )
            success_msg = (
                f"Attendance marked successfully! You are verified inside {college_name} "
                f"({distance_rounded}m from center). Status: Present."
            )

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": success_msg,
            "distance": distance_rounded,
            "radius": allowed_radius,
            "date": today,
            "status": "Present"
        })
    else:
        conn.close()
        diff = round(distance_meters - allowed_radius, 1)
        rejection_msg = (
            f"Attendance Rejected: You are {distance_rounded}m away from {college_name}, "
            f"which is {diff}m outside the acceptable radius of {allowed_radius}m."
        )
        return jsonify({
            "success": False,
            "message": rejection_msg,
            "distance": distance_rounded,
            "radius": allowed_radius
        }), 200
