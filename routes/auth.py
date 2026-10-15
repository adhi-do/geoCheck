import os
import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from utils.mailer import send_magic_link_email

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Student login via Magic Link.
    Students cannot register manually; they enter their Roll Number or Email.
    A secure temporary single-use token is generated and emailed.
    """
    if session.get("user_id"):
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()

        if not identifier:
            flash("Please enter your Roll Number or registered Email address.", "warning")
            return redirect(url_for("auth.login"))

        conn = get_db()
        cursor = conn.cursor()

        # Query user by roll number or email (case-insensitive)
        cursor.execute("""
            SELECT * FROM users 
            WHERE LOWER(roll_number) = LOWER(?) OR LOWER(email) = LOWER(?)
            LIMIT 1
        """, (identifier, identifier))
        user = cursor.fetchone()

        if not user:
            conn.close()
            flash(
                "No registered student found with that Roll Number or Email. "
                "Please verify the details or contact your college administrator.",
                "danger"
            )
            return redirect(url_for("auth.login"))

        # Generate secure random token
        token = secrets.token_urlsafe(32)
        # 15 minutes expiration time stored as ISO 8601 string
        expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        expiry_str = expiry.isoformat()

        # Save token and expiry into SQLite users table
        cursor.execute("""
            UPDATE users 
            SET token = ?, token_expiry = ? 
            WHERE id = ?
        """, (token, expiry_str, user["id"]))
        conn.commit()
        conn.close()

        # Generate magic link URL
        magic_link = url_for("auth.verify_magic_link", token=token, _external=True)

        # Send magic link email using smtplib
        success, status_msg = send_magic_link_email(user["email"], magic_link)

        # For development / testing when SMTP password is not set:
        dev_mode = not os.getenv("MAIL_PASSWORD", "").strip()

        flash(
            f"A magic login link has been generated for {user['email']}. "
            "Please check your inbox to sign in.",
            "success"
        )

        return render_template(
            "login.html",
            magic_sent=True,
            user_email=user["email"],
            dev_magic_link=magic_link if dev_mode else None
        )

    return render_template("login.html", magic_sent=False)


@auth_bp.route("/login/verify", methods=["GET"])
def verify_magic_link():
    """
    Verifies the magic link token from the query string (e.g. /login/verify?token=...).
    Validates token existence and expiry, then starts a secure Flask session.
    """
    token = request.args.get("token", "").strip()

    if not token:
        flash("Invalid request: No verification token provided.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE token = ? LIMIT 1", (token,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        flash("Invalid or already used magic link. Please request a new one.", "danger")
        return redirect(url_for("auth.login"))

    # Verify expiration
    expiry_str = user["token_expiry"]
    is_expired = True

    if expiry_str:
        try:
            # Handle ISO formats
            expiry_dt = datetime.fromisoformat(expiry_str)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) <= expiry_dt:
                is_expired = False
        except Exception:
            is_expired = True

    if is_expired:
        # Invalidate the expired token
        cursor.execute("UPDATE users SET token = NULL, token_expiry = NULL WHERE id = ?", (user["id"],))
        conn.commit()
        conn.close()
        flash("This magic link has expired. Please request a fresh login link.", "warning")
        return redirect(url_for("auth.login"))

    # Invalidate token immediately to ensure single-use security
    cursor.execute("UPDATE users SET token = NULL, token_expiry = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()

    # Create secure Flask session
    session.clear()
    session["user_id"] = user["id"]
    session["roll_number"] = user["roll_number"]
    session["email"] = user["email"]

    flash(f"Welcome back, {user['roll_number']}! You have signed in successfully.", "success")
    return redirect(url_for("student.dashboard"))


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """
    Terminates student session and redirects to login page.
    """
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
