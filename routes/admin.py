import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/setup", methods=["GET", "POST"])
def setup():
    """
    Admin & College geofence configuration page.
    Allows configuring admin email, college name, GPS coordinates, and acceptable radius.
    """
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        admin_email = request.form.get("admin_email", "").strip()
        college_name = request.form.get("college_name", "").strip()
        
        try:
            latitude = float(request.form.get("latitude", 0))
            longitude = float(request.form.get("longitude", 0))
            radius_meters = float(request.form.get("radius_meters", 100))
        except (ValueError, TypeError):
            flash("Invalid coordinates or radius entered. Please enter valid numbers.", "danger")
            conn.close()
            return redirect(url_for("admin.setup"))

        if not admin_email or not college_name:
            flash("Admin email and College name are required.", "danger")
            conn.close()
            return redirect(url_for("admin.setup"))

        # Maintain single-row configuration
        cursor.execute("DELETE FROM admin_settings")
        cursor.execute("""
            INSERT INTO admin_settings (admin_email, college_name, latitude, longitude, radius_meters)
            VALUES (?, ?, ?, ?, ?)
        """, (admin_email, college_name, latitude, longitude, radius_meters))
        conn.commit()
        conn.close()

        flash("College geofence settings saved successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    cursor.execute("SELECT * FROM admin_settings LIMIT 1")
    settings = cursor.fetchone()
    conn.close()

    return render_template("admin_setup.html", settings=settings)


@admin_bp.route("/dashboard", methods=["GET"])
@admin_bp.route("/", methods=["GET"])
def dashboard():
    """
    Admin dashboard displaying:
    - College configuration status and geofence parameters
    - CSV upload form for students.csv
    - Registered students list with today's attendance status and total attendance count
    """
    conn = get_db()
    cursor = conn.cursor()

    # Retrieve current admin/college settings
    cursor.execute("SELECT * FROM admin_settings LIMIT 1")
    settings = cursor.fetchone()

    # Today's date string YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")

    # Retrieve students with their attendance for today and total attendance count
    cursor.execute("""
        SELECT 
            u.id,
            u.roll_number,
            u.email,
            (SELECT status FROM attendance WHERE user_id = u.id AND date = ? LIMIT 1) AS today_status,
            (SELECT COUNT(*) FROM attendance WHERE user_id = u.id AND status = 'Present') AS total_attended
        FROM users u
        ORDER BY u.roll_number ASC
    """, (today,))
    students = cursor.fetchall()

    total_students = len(students)
    today_present = sum(1 for s in students if s["today_status"] == "Present")

    conn.close()

    return render_template(
        "admin_dashboard.html",
        settings=settings,
        students=students,
        total_students=total_students,
        today_present=today_present,
        today=today
    )


@admin_bp.route("/upload-students", methods=["POST"])
def upload_students():
    """
    Handles CSV upload for student batch registration.
    CSV format expected:
      Column 1 = rollnumber
      Column 2 = email_id
    Gracefully handles headers, whitespace, and existing duplicates (insert/update).
    """
    if "students_file" not in request.files:
        flash("No file part found in upload request.", "danger")
        return redirect(url_for("admin.dashboard"))

    file = request.files["students_file"]

    if file.filename == "":
        flash("Please select a CSV file to upload.", "warning")
        return redirect(url_for("admin.dashboard"))

    if not (file.filename.lower().endswith(".csv") or file.mimetype in ("text/csv", "application/vnd.ms-excel", "text/plain")):
        flash("Invalid file format. Please upload a .csv file.", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        # Decode stream using utf-8-sig to automatically strip UTF-8 BOM if present
        content = file.stream.read().decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(content))

        conn = get_db()
        cursor = conn.cursor()

        total_processed = 0
        added_count = 0
        updated_count = 0
        skipped_count = 0

        for row_index, row in enumerate(reader, start=1):
            if not row or all(field.strip() == "" for field in row):
                continue  # Skip blank lines

            if len(row) < 2:
                skipped_count += 1
                continue

            roll_number = row[0].strip()
            email = row[1].strip()

            # Skip header row if present
            if row_index == 1 and (
                roll_number.lower().startswith("roll")
                or "email" in email.lower()
                or "@" not in email
            ):
                continue

            if not roll_number or not email:
                skipped_count += 1
                continue

            total_processed += 1

            # Check if student exists by roll number
            cursor.execute("SELECT id, roll_number, email FROM users WHERE roll_number = ?", (roll_number,))
            existing_by_roll = cursor.fetchone()

            # Check if student exists by email
            cursor.execute("SELECT id, roll_number, email FROM users WHERE email = ?", (email,))
            existing_by_email = cursor.fetchone()

            if existing_by_roll:
                # Update email for this roll number
                cursor.execute(
                    "UPDATE users SET email = ? WHERE id = ?",
                    (email, existing_by_roll["id"])
                )
                updated_count += 1
            elif existing_by_email:
                # Update roll number for this existing email
                cursor.execute(
                    "UPDATE users SET roll_number = ? WHERE id = ?",
                    (roll_number, existing_by_email["id"])
                )
                updated_count += 1
            else:
                # Insert brand new student record
                cursor.execute(
                    "INSERT INTO users (roll_number, email) VALUES (?, ?)",
                    (roll_number, email)
                )
                added_count += 1

        conn.commit()
        conn.close()

        flash(
            f"CSV processing complete: {added_count} student(s) added, "
            f"{updated_count} updated, {skipped_count} skipped.",
            "success"
        )
    except Exception as e:
        flash(f"Error parsing CSV file: {str(e)}", "danger")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete-student/<int:student_id>", methods=["POST"])
def delete_student(student_id: int):
    """
    Optional helper to remove a student from the system.
    Also removes corresponding attendance records.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE user_id = ?", (student_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    flash("Student removed successfully.", "info")
    return redirect(url_for("admin.dashboard"))
