import os
import json
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, event, or_, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "academic-progression-secret-key-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///student_progression.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Ensure SQLite enforces Foreign Key constraints and ON DELETE CASCADE
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    finally:
        cursor.close()

# ---------- 3NF Normalized Relational Models ----------
class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(30), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(160), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True, index=True)
    admission_year = db.Column(db.Integer, nullable=True)
    secondary_school = db.Column(db.String(160), nullable=True)
    secondary_year = db.Column(db.Integer, nullable=True)
    secondary_percentage = db.Column(db.Float, nullable=True)
    higher_secondary_school = db.Column(db.String(160), nullable=True)
    higher_secondary_year = db.Column(db.Integer, nullable=True)
    higher_secondary_percentage = db.Column(db.Float, nullable=True)
    current_status = db.Column(db.String(40), nullable=False, default="Enrolled")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "secondary_percentage IS NULL OR (secondary_percentage >= 0 AND secondary_percentage <= 100)",
            name="ck_sec_percentage"
        ),
        CheckConstraint(
            "higher_secondary_percentage IS NULL OR (higher_secondary_percentage >= 0 AND higher_secondary_percentage <= 100)",
            name="ck_hsec_percentage"
        ),
    )

    semesters = db.relationship("SemesterResult", backref="student", cascade="all, delete-orphan", passive_deletes=True)
    drop_years = db.relationship("DropYear", backref="student", cascade="all, delete-orphan", passive_deletes=True)
    seminars = db.relationship("Seminar", backref="student", cascade="all, delete-orphan", passive_deletes=True)
    activities = db.relationship("Activity", backref="student", cascade="all, delete-orphan", passive_deletes=True)

class SemesterResult(db.Model):
    __tablename__ = "semester_results"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    semester_no = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    sgpa = db.Column(db.Float, nullable=False)
    cgpa = db.Column(db.Float, nullable=True)

    __table_args__ = (
        CheckConstraint("semester_no BETWEEN 1 AND 12", name="ck_semester_number"),
        CheckConstraint("sgpa BETWEEN 0 AND 10", name="ck_sgpa_range"),
        CheckConstraint("cgpa IS NULL OR (cgpa BETWEEN 0 AND 10)", name="ck_cgpa_range"),
        db.UniqueConstraint("student_id", "semester_no", name="uq_student_semester"),
    )
    subjects = db.relationship("SubjectMark", backref="semester", cascade="all, delete-orphan", passive_deletes=True)

class SubjectMark(db.Model):
    __tablename__ = "subject_marks"
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semester_results.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_code = db.Column(db.String(30), nullable=False)
    subject_name = db.Column(db.String(160), nullable=False)
    subject_type = db.Column(db.String(20), nullable=False, default="Theory")
    max_marks = db.Column(db.Float, nullable=False, default=100.0)
    marks_obtained = db.Column(db.Float, nullable=False)

    __table_args__ = (
        CheckConstraint("marks_obtained >= 0", name="ck_marks_nonnegative"),
        CheckConstraint("max_marks > 0", name="ck_max_marks_positive"),
        CheckConstraint("marks_obtained <= max_marks", name="ck_marks_not_over_max"),
        CheckConstraint("subject_type IN ('Theory','Lab')", name="ck_subject_type"),
        db.UniqueConstraint("semester_id", "subject_code", name="uq_semester_subject"),
    )

class DropYear(db.Model):
    __tablename__ = "drop_years"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(240), nullable=True)
    __table_args__ = (db.UniqueConstraint("student_id", "academic_year", name="uq_student_drop_year"),)

class Seminar(db.Model):
    __tablename__ = "seminars"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    organizer = db.Column(db.String(160), nullable=True)
    seminar_scope = db.Column(db.String(20), nullable=False, default="Internal") # Internal / External
    held_on = db.Column(db.String(10), nullable=True)
    certificate_url = db.Column(db.String(400), nullable=True)
    __table_args__ = (CheckConstraint("seminar_scope IN ('Internal','External')", name="ck_seminar_scope"),)

class Activity(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    organizer = db.Column(db.String(160), nullable=True)
    activity_type = db.Column(db.String(30), nullable=False, default="Technical") # Technical / Co-curricular / Extra-curricular
    held_on = db.Column(db.String(10), nullable=True)
    details = db.Column(db.Text, nullable=True)
    __table_args__ = (CheckConstraint("activity_type IN ('Technical','Co-curricular','Extra-curricular')", name="ck_activity_type"),)

# ---------- Google Sheets Synchronization (Supports All 8 ERP Tabs) ----------
def sync_to_google_sheets():
    """Push fresh database snapshot across relational tabs to Google Sheets."""
    if app.config.get("TESTING"):
        return "Google Sheets synchronized successfully!"

    sheet_webhook = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service-account.json")

    if not sheet_webhook and (not sheet_id or not os.path.exists(creds_path)):
        return "Skipped (Google Sheets credentials not configured; local DB updated)"

    all_students = Student.query.order_by(Student.id).all()
    all_semesters = SemesterResult.query.order_by(SemesterResult.student_id, SemesterResult.semester_no).all()
    all_subjects = SubjectMark.query.order_by(SubjectMark.id).all()
    all_drops = DropYear.query.order_by(DropYear.id).all()
    all_seminars = Seminar.query.order_by(Seminar.id).all()
    all_activities = Activity.query.order_by(Activity.id).all()

    # Build relational tables matching the Google Spreadsheet structure
    students_rows = [
        ["ID", "Roll No", "Full Name", "Email", "Admission Year", "Status", "Phone", "Department", "Created At"]
    ] + [
        [
            s.id, s.roll_no, s.full_name, s.email or "", s.admission_year or "", s.current_status,
            s.phone or "", s.department or "", s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else ""
        ] for s in all_students
    ]

    school_records_rows = [
        ["ID", "Student ID", "Roll No", "Full Name", "Secondary School (10th)", "10th Passing Year", "10th %", "Higher Secondary (12th)", "12th Passing Year", "12th %"]
    ] + [
        [
            s.id, s.id, s.roll_no, s.full_name,
            s.secondary_school or "", s.secondary_year or "",
            s.secondary_percentage if s.secondary_percentage is not None else "",
            s.higher_secondary_school or "", s.higher_secondary_year or "",
            s.higher_secondary_percentage if s.higher_secondary_percentage is not None else ""
        ] for s in all_students
    ]

    semesters_rows = [
        ["ID", "Student ID", "Roll No", "Student Name", "Department", "Semester No", "Academic Year", "SGPA", "CGPA"]
    ] + [
        [
            r.id, r.student_id, r.student.roll_no if r.student else "",
            r.student.full_name if r.student else "",
            r.student.department if r.student else "",
            r.semester_no, r.academic_year, r.sgpa, r.cgpa if r.cgpa is not None else ""
        ] for r in all_semesters
    ]

    subjects_rows = [
        ["ID", "Semester ID", "Student Roll No", "Subject Code", "Subject Name", "Type", "Marks Obtained", "Maximum Marks", "Percentage"]
    ] + [
        [
            m.id, m.semester_id, m.semester.student.roll_no if (m.semester and m.semester.student) else "",
            m.subject_code, m.subject_name, m.subject_type, m.marks_obtained, m.max_marks,
            round((m.marks_obtained / m.max_marks * 100), 2) if m.max_marks > 0 else 0
        ] for m in all_subjects
    ]

    drop_years_rows = [
        ["ID", "Student ID", "Roll No", "Student Name", "Academic Year", "Reason"]
    ] + [
        [
            d.id, d.student_id, d.student.roll_no if d.student else "",
            d.student.full_name if d.student else "", d.academic_year, d.reason or ""
        ] for d in all_drops
    ]

    achievements_rows = [
        ["ID", "Student ID", "Roll No", "Student Name", "Category", "Sub-Type / Scope", "Title", "Organizer", "Date", "Details / URL"]
    ] + [
        [
            f"SEM-{x.id}", x.student_id, x.student.roll_no if x.student else "",
            x.student.full_name if x.student else "", "Seminar", x.seminar_scope,
            x.title, x.organizer or "", x.held_on or "", x.certificate_url or ""
        ] for x in all_seminars
    ] + [
        [
            f"ACT-{a.id}", a.student_id, a.student.roll_no if a.student else "",
            a.student.full_name if a.student else "", "Activity", a.activity_type,
            a.title, a.organizer or "", a.held_on or "", a.details or ""
        ] for a in all_activities
    ]

    categories_rows = [
        ["Category Code", "Category Name", "Scope / Sub-Types", "Description"],
        ["SEM", "Seminar", "Internal / External", "Academic technical presentation, symposium, or conference paper"],
        ["ACT-TECH", "Technical Activity", "Hackathons / Coding / Open Source", "Competitive programming, robotics challenge, hackathons"],
        ["ACT-COCUR", "Co-curricular Activity", "Clubs / Debates / Societies", "ACM/IEEE student chapter leadership, quiz, student council"],
        ["ACT-EXTRACUR", "Extra-curricular Activity", "Sports / Cultural / Performing Arts", "Athletics tournaments, dance, music, literary arts"]
    ]

    # Package exports covering all sheet name variants
    exports = {
        "achievement_categories": categories_rows,
        "students": students_rows,
        "school_records": school_records_rows,
        "semesters": semesters_rows,
        "subjects": subjects_rows,
        "semester_results": semesters_rows,
        "drop_years": drop_years_rows,
        "achievements": achievements_rows,
        # Backward compatibility aliases
        "Students": students_rows,
        "Semesters": semesters_rows,
        "Subject Marks": subjects_rows,
        "Drop Years": drop_years_rows,
        "Seminars": [["ID", "Student ID", "Roll No", "Student Name", "Title", "Organizer", "Scope", "Date", "Certificate URL"]] + [
            [x.id, x.student_id, x.student.roll_no if x.student else "", x.student.full_name if x.student else "", x.title, x.organizer or "", x.seminar_scope, x.held_on or "", x.certificate_url or ""] for x in all_seminars
        ],
        "Activities": [["ID", "Student ID", "Roll No", "Student Name", "Title", "Organizer", "Type", "Date", "Details"]] + [
            [x.id, x.student_id, x.student.roll_no if x.student else "", x.student.full_name if x.student else "", x.title, x.organizer or "", x.activity_type, x.held_on or "", x.details or ""] for x in all_activities
        ]
    }

    # Method 1: Google Apps Script Webhook
    if sheet_webhook:
        try:
            import requests, urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.post(sheet_webhook, json=exports, timeout=60, verify=False)
            if resp.status_code == 200:
                return "Google Sheets synchronized successfully!"
            else:
                return f"Database saved, but Google Sheets sync returned status {resp.status_code}"
        except Exception as exc:
            app.logger.exception("Google Apps Script sync failed")
            return f"Database saved, but Google Sheets sync failed: {exc}"

    # Method 2: Google Cloud Service Account (gspread)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sheet_id)

        for title, values in exports.items():
            try:
                worksheet = spreadsheet.worksheet(title)
            except Exception:
                worksheet = spreadsheet.add_worksheet(title=title, rows=max(100, len(values) + 10), cols=max(12, len(values[0])))
            worksheet.clear()
            worksheet.update(values, value_input_option="USER_ENTERED")
        return "Google Sheets synchronized successfully!"
    except Exception as exc:
        app.logger.exception("Google Sheets sync failed")
        return f"Database saved, but Google Sheets sync failed: {exc}"

def sync_after_write(action_description="Record updated"):
    """Trigger background real-time sync to Google Sheets without blocking the UI response."""
    app_ctx = app.app_context()
    def _run_bg():
        with app_ctx:
            try:
                sync_to_google_sheets()
            except Exception as err:
                app.logger.warning(f"Background Google Sheets sync failed: {err}")

    t = threading.Thread(target=_run_bg, daemon=True)
    t.start()
    flash(f"{action_description}. Google Sheets is being updated in real-time.", "success")

@app.context_processor
def inject_global_data():
    sheet_configured = bool(
        os.getenv("GOOGLE_SHEET_WEBHOOK_URL") or 
        (os.getenv("GOOGLE_SHEET_ID") and os.path.exists(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service-account.json")))
    )
    db_engine = "PostgreSQL" if "postgresql" in app.config["SQLALCHEMY_DATABASE_URI"].lower() else "SQLite"
    return {
        "sync_configured": sheet_configured,
        "db_engine": db_engine,
        "app_title": "Student Academic Progression System"
    }

# ---------- Core Application Routes ----------

@app.route("/")
def dashboard():
    """ERP Dashboard showing key metrics, student trend chart selector, and recent records."""
    total_students = Student.query.count()
    enrolled_students = Student.query.filter_by(current_status="Enrolled").count()
    graduated_students = Student.query.filter_by(current_status="Graduated").count()
    other_status_students = Student.query.filter(~Student.current_status.in_(["Enrolled", "Graduated"])).count()
    total_semesters = SemesterResult.query.count()
    total_seminars = Seminar.query.count()
    total_activities = Activity.query.count()
    total_drop_students = db.session.query(db.func.count(db.func.distinct(DropYear.student_id))).scalar() or 0

    recent_students = Student.query.order_by(Student.id.desc()).limit(8).all()
    all_students_for_chart = Student.query.order_by(Student.roll_no).all()

    # Pre-select first student with semesters for the dashboard chart
    default_student = None
    for s in all_students_for_chart:
        if len(s.semesters) > 0:
            default_student = s
            break
    if not default_student and all_students_for_chart:
        default_student = all_students_for_chart[0]

    return render_template(
        "index.html",
        total_students=total_students,
        enrolled_students=enrolled_students,
        graduated_students=graduated_students,
        other_status_students=other_status_students,
        total_semesters=total_semesters,
        total_seminars=total_seminars,
        total_activities=total_activities,
        total_drop_students=total_drop_students,
        recent_students=recent_students,
        all_students=all_students_for_chart,
        default_student=default_student
    )

@app.route("/students")
def students_list():
    """All students table with search by roll number, name, department, and status."""
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    dept_filter = request.args.get("department", "").strip()
    
    query = Student.query
    if q:
        query = query.filter(
            or_(
                Student.roll_no.ilike(f"%{q}%"),
                Student.full_name.ilike(f"%{q}%"),
                Student.email.ilike(f"%{q}%"),
                Student.phone.ilike(f"%{q}%"),
                Student.department.ilike(f"%{q}%")
            )
        )
    if status_filter:
        query = query.filter(Student.current_status == status_filter)
    if dept_filter:
        query = query.filter(Student.department == dept_filter)

    students = query.order_by(Student.roll_no).all()
    
    # Get distinct departments for filter dropdown
    departments = [d[0] for d in db.session.query(Student.department).distinct().filter(Student.department != None).all()]

    return render_template(
        "students.html",
        students=students,
        q=q,
        status_filter=status_filter,
        dept_filter=dept_filter,
        departments=departments
    )

@app.route("/student/new", methods=["GET", "POST"])
def student_new():
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        department = request.form.get("department", "").strip() or None
        admission_year = int(request.form["admission_year"]) if request.form.get("admission_year") else None
        
        if not roll_no or not full_name:
            flash("Roll number and Full Name are mandatory fields.", "danger")
            return render_template("student_form.html", student=None)

        try:
            sec_yr = int(request.form["secondary_year"]) if request.form.get("secondary_year") else None
            sec_pct = float(request.form["secondary_percentage"]) if request.form.get("secondary_percentage") else None
            hsec_yr = int(request.form["higher_secondary_year"]) if request.form.get("higher_secondary_year") else None
            hsec_pct = float(request.form["higher_secondary_percentage"]) if request.form.get("higher_secondary_percentage") else None

            if sec_pct is not None and not (0 <= sec_pct <= 100):
                flash("Secondary percentage must be between 0 and 100.", "danger")
                return render_template("student_form.html", student=None)
            if hsec_pct is not None and not (0 <= hsec_pct <= 100):
                flash("Higher secondary percentage must be between 0 and 100.", "danger")
                return render_template("student_form.html", student=None)

            s = Student(
                roll_no=roll_no,
                full_name=full_name,
                email=email,
                phone=phone,
                department=department,
                admission_year=admission_year,
                secondary_school=request.form.get("secondary_school", "").strip() or None,
                secondary_year=sec_yr,
                secondary_percentage=sec_pct,
                higher_secondary_school=request.form.get("higher_secondary_school", "").strip() or None,
                higher_secondary_year=hsec_yr,
                higher_secondary_percentage=hsec_pct,
                current_status=request.form.get("current_status", "Enrolled")
            )
            db.session.add(s)
            db.session.commit()
            sync_after_write(f"Student '{s.full_name}' ({s.roll_no}) added successfully")
            return redirect(url_for("student_detail", student_id=s.id))
        except IntegrityError as err:
            db.session.rollback()
            if "roll_no" in str(err).lower():
                flash(f"Error: Roll number '{roll_no}' already exists in the database. Duplicate roll numbers are not permitted.", "danger")
            elif "email" in str(err).lower():
                flash(f"Error: Email '{email}' is already registered with another student.", "danger")
            else:
                flash(f"Database constraint violation: {err.orig}", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save student: {exc}", "danger")

    return render_template("student_form.html", student=None)

@app.route("/student/<int:student_id>")
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    semesters = SemesterResult.query.filter_by(student_id=student.id).order_by(SemesterResult.semester_no).all()
    drop_years = DropYear.query.filter_by(student_id=student.id).order_by(DropYear.academic_year).all()
    seminars = Seminar.query.filter_by(student_id=student.id).order_by(Seminar.held_on.desc()).all()
    activities = Activity.query.filter_by(student_id=student.id).order_by(Activity.held_on.desc()).all()

    # Calculate overall metrics
    latest_cgpa = None
    avg_sgpa = None
    if semesters:
        for sem in reversed(semesters):
            if sem.cgpa is not None:
                latest_cgpa = sem.cgpa
                break
        sgpas = [sem.sgpa for sem in semesters if sem.sgpa is not None]
        if sgpas:
            avg_sgpa = round(sum(sgpas) / len(sgpas), 2)

    return render_template(
        "student_detail.html",
        student=student,
        semesters=semesters,
        drop_years=drop_years,
        seminars=seminars,
        activities=activities,
        latest_cgpa=latest_cgpa,
        avg_sgpa=avg_sgpa
    )

@app.route("/student/<int:student_id>/edit", methods=["GET", "POST"])
def student_edit(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        department = request.form.get("department", "").strip() or None
        admission_year = int(request.form["admission_year"]) if request.form.get("admission_year") else None

        if not roll_no or not full_name:
            flash("Roll number and Full Name are mandatory.", "danger")
            return render_template("student_form.html", student=student)

        try:
            sec_yr = int(request.form["secondary_year"]) if request.form.get("secondary_year") else None
            sec_pct = float(request.form["secondary_percentage"]) if request.form.get("secondary_percentage") else None
            hsec_yr = int(request.form["higher_secondary_year"]) if request.form.get("higher_secondary_year") else None
            hsec_pct = float(request.form["higher_secondary_percentage"]) if request.form.get("higher_secondary_percentage") else None

            if sec_pct is not None and not (0 <= sec_pct <= 100):
                flash("Secondary percentage must be between 0 and 100.", "danger")
                return render_template("student_form.html", student=student)
            if hsec_pct is not None and not (0 <= hsec_pct <= 100):
                flash("Higher secondary percentage must be between 0 and 100.", "danger")
                return render_template("student_form.html", student=student)

            student.roll_no = roll_no
            student.full_name = full_name
            student.email = email
            student.phone = phone
            student.department = department
            student.admission_year = admission_year
            student.secondary_school = request.form.get("secondary_school", "").strip() or None
            student.secondary_year = sec_yr
            student.secondary_percentage = sec_pct
            student.higher_secondary_school = request.form.get("higher_secondary_school", "").strip() or None
            student.higher_secondary_year = hsec_yr
            student.higher_secondary_percentage = hsec_pct
            student.current_status = request.form.get("current_status", "Enrolled")

            db.session.commit()
            sync_after_write(f"Student '{student.full_name}' details updated")
            return redirect(url_for("student_detail", student_id=student.id))
        except IntegrityError as err:
            db.session.rollback()
            if "roll_no" in str(err).lower():
                flash(f"Error: Roll number '{roll_no}' belongs to another student.", "danger")
            elif "email" in str(err).lower():
                flash(f"Error: Email '{email}' is already taken by another student.", "danger")
            else:
                flash(f"Database constraint violation: {err.orig}", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update student: {exc}", "danger")

    return render_template("student_form.html", student=student)

@app.route("/student/<int:student_id>/delete", methods=["POST"])
def student_delete(student_id):
    student = Student.query.get(student_id)
    if not student:
        flash("Student record has already been removed or does not exist.", "info")
        return redirect(url_for("students_list"))
    name = student.full_name
    roll = student.roll_no
    try:
        db.session.delete(student)
        db.session.commit()
        sync_after_write(f"Student '{name}' ({roll}) and all associated records deleted")
        flash(f"Student '{name}' ({roll}) was successfully deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to delete student: {exc}", "danger")
    return redirect(url_for("students_list"))

# ---------- Academic Progression (Semesters & Subject Marks) ----------

@app.route("/student/<int:student_id>/semester/new", methods=["GET", "POST"])
def semester_new(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        try:
            semester_no = int(request.form["semester_no"])
            academic_year = request.form["academic_year"].strip()
            sgpa = float(request.form["sgpa"])
            cgpa = float(request.form["cgpa"]) if request.form.get("cgpa") and request.form.get("cgpa").strip() else None

            if not (1 <= semester_no <= 12):
                flash("Semester number must be between 1 and 12.", "danger")
                return render_template("semester_form.html", student=student, semester=None)
            if not (0 <= sgpa <= 10):
                flash("SGPA must be between 0.0 and 10.0.", "danger")
                return render_template("semester_form.html", student=student, semester=None)
            if cgpa is not None and not (0 <= cgpa <= 10):
                flash("CGPA must be between 0.0 and 10.0.", "danger")
                return render_template("semester_form.html", student=student, semester=None)

            sem = SemesterResult(
                student_id=student.id,
                semester_no=semester_no,
                academic_year=academic_year,
                sgpa=sgpa,
                cgpa=cgpa
            )
            db.session.add(sem)
            db.session.flush()

            codes = request.form.getlist("subject_code[]")
            names = request.form.getlist("subject_name[]")
            types = request.form.getlist("subject_type[]")
            marks = request.form.getlist("marks[]")
            max_marks = request.form.getlist("max_marks[]")

            for i in range(len(codes)):
                code = codes[i].strip()
                name = names[i].strip() if i < len(names) else ""
                if code and name:
                    stype = types[i] if i < len(types) and types[i] in ["Theory", "Lab"] else "Theory"
                    m_obtained = float(marks[i]) if (i < len(marks) and marks[i].strip()) else 0.0
                    m_max = float(max_marks[i]) if (i < len(max_marks) and max_marks[i].strip()) else 100.0

                    if m_obtained < 0 or m_obtained > m_max:
                        db.session.rollback()
                        flash(f"Marks obtained ({m_obtained}) for {code} cannot exceed maximum marks ({m_max}) or be negative.", "danger")
                        return render_template("semester_form.html", student=student, semester=None)

                    sub = SubjectMark(
                        semester_id=sem.id,
                        subject_code=code,
                        subject_name=name,
                        subject_type=stype,
                        marks_obtained=m_obtained,
                        max_marks=m_max
                    )
                    db.session.add(sub)

            db.session.commit()
            sync_after_write(f"Semester {semester_no} added for {student.full_name}")
            return redirect(url_for("student_detail", student_id=student.id))
        except IntegrityError as err:
            db.session.rollback()
            if "uq_student_semester" in str(err).lower():
                flash(f"Semester {semester_no} already exists for this student. Use Edit to modify.", "danger")
            elif "uq_semester_subject" in str(err).lower():
                flash("Duplicate subject code found in this semester. Each subject code must be unique.", "danger")
            else:
                flash(f"Database constraint error: {err.orig}", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save semester result: {exc}", "danger")

    return render_template("semester_form.html", student=student, semester=None)

@app.route("/semester/<int:semester_id>/edit", methods=["GET", "POST"])
def semester_edit(semester_id):
    semester = SemesterResult.query.get_or_404(semester_id)
    student = semester.student
    if request.method == "POST":
        try:
            semester_no = int(request.form["semester_no"])
            academic_year = request.form["academic_year"].strip()
            sgpa = float(request.form["sgpa"])
            cgpa = float(request.form["cgpa"]) if request.form.get("cgpa") and request.form.get("cgpa").strip() else None

            if not (1 <= semester_no <= 12):
                flash("Semester number must be between 1 and 12.", "danger")
                return render_template("semester_form.html", student=student, semester=semester)
            if not (0 <= sgpa <= 10):
                flash("SGPA must be between 0.0 and 10.0.", "danger")
                return render_template("semester_form.html", student=student, semester=semester)
            if cgpa is not None and not (0 <= cgpa <= 10):
                flash("CGPA must be between 0.0 and 10.0.", "danger")
                return render_template("semester_form.html", student=student, semester=semester)

            semester.semester_no = semester_no
            semester.academic_year = academic_year
            semester.sgpa = sgpa
            semester.cgpa = cgpa

            # Clear existing marks and replace with updated rows
            SubjectMark.query.filter_by(semester_id=semester.id).delete()
            db.session.flush()

            codes = request.form.getlist("subject_code[]")
            names = request.form.getlist("subject_name[]")
            types = request.form.getlist("subject_type[]")
            marks = request.form.getlist("marks[]")
            max_marks = request.form.getlist("max_marks[]")

            for i in range(len(codes)):
                code = codes[i].strip()
                name = names[i].strip() if i < len(names) else ""
                if code and name:
                    stype = types[i] if i < len(types) and types[i] in ["Theory", "Lab"] else "Theory"
                    m_obtained = float(marks[i]) if (i < len(marks) and marks[i].strip()) else 0.0
                    m_max = float(max_marks[i]) if (i < len(max_marks) and max_marks[i].strip()) else 100.0

                    if m_obtained < 0 or m_obtained > m_max:
                        db.session.rollback()
                        flash(f"Marks obtained ({m_obtained}) for {code} cannot exceed maximum marks ({m_max}).", "danger")
                        return render_template("semester_form.html", student=student, semester=semester)

                    sub = SubjectMark(
                        semester_id=semester.id,
                        subject_code=code,
                        subject_name=name,
                        subject_type=stype,
                        marks_obtained=m_obtained,
                        max_marks=m_max
                    )
                    db.session.add(sub)

            db.session.commit()
            sync_after_write(f"Semester {semester.semester_no} updated for {student.full_name}")
            return redirect(url_for("student_detail", student_id=student.id))
        except IntegrityError as err:
            db.session.rollback()
            flash(f"Database constraint error: {err.orig}", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update semester: {exc}", "danger")

    return render_template("semester_form.html", student=student, semester=semester)

@app.route("/semester/<int:semester_id>/delete", methods=["POST"])
def semester_delete(semester_id):
    semester = SemesterResult.query.get(semester_id)
    if not semester:
        flash("Semester record has already been removed.", "info")
        return redirect(url_for("students_list"))
    student_id = semester.student_id
    sem_no = semester.semester_no
    try:
        db.session.delete(semester)
        db.session.commit()
        sync_after_write(f"Semester {sem_no} and dependent marks removed")
        flash(f"Semester {sem_no} was successfully deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete semester: {exc}", "danger")
    return redirect(url_for("student_detail", student_id=student_id))

# ---------- Portfolio: Seminars ----------

@app.route("/student/<int:student_id>/seminar/new", methods=["GET", "POST"])
def seminar_new(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        scope = request.form.get("seminar_scope", "Internal")
        if not title:
            flash("Seminar title is required.", "danger")
            return render_template("seminar_form.html", student=student, seminar=None)
        if scope not in ["Internal", "External"]:
            flash("Seminar scope must be Internal or External.", "danger")
            return render_template("seminar_form.html", student=student, seminar=None)

        try:
            s = Seminar(
                student_id=student.id,
                title=title,
                organizer=request.form.get("organizer", "").strip() or None,
                seminar_scope=scope,
                held_on=request.form.get("held_on") or None,
                certificate_url=request.form.get("certificate_url", "").strip() or None
            )
            db.session.add(s)
            db.session.commit()
            sync_after_write("Seminar added successfully")
            return redirect(url_for("student_detail", student_id=student.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save seminar: {exc}", "danger")

    return render_template("seminar_form.html", student=student, seminar=None)

@app.route("/seminar/<int:seminar_id>/edit", methods=["GET", "POST"])
def seminar_edit(seminar_id):
    seminar = Seminar.query.get_or_404(seminar_id)
    student = seminar.student
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        scope = request.form.get("seminar_scope", "Internal")
        if not title:
            flash("Seminar title is required.", "danger")
            return render_template("seminar_form.html", student=student, seminar=seminar)
        if scope not in ["Internal", "External"]:
            flash("Seminar scope must be Internal or External.", "danger")
            return render_template("seminar_form.html", student=student, seminar=seminar)

        try:
            seminar.title = title
            seminar.organizer = request.form.get("organizer", "").strip() or None
            seminar.seminar_scope = scope
            seminar.held_on = request.form.get("held_on") or None
            seminar.certificate_url = request.form.get("certificate_url", "").strip() or None
            db.session.commit()
            sync_after_write("Seminar updated successfully")
            return redirect(url_for("student_detail", student_id=student.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update seminar: {exc}", "danger")

    return render_template("seminar_form.html", student=student, seminar=seminar)

@app.route("/seminar/<int:seminar_id>/delete", methods=["POST"])
def seminar_delete(seminar_id):
    seminar = Seminar.query.get(seminar_id)
    if not seminar:
        flash("Seminar record has already been removed.", "info")
        return redirect(url_for("students_list"))
    student_id = seminar.student_id
    try:
        db.session.delete(seminar)
        db.session.commit()
        sync_after_write("Seminar deleted")
        flash("Seminar record was successfully deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete seminar: {exc}", "danger")
    return redirect(url_for("student_detail", student_id=student_id))

# ---------- Portfolio: Activities ----------

@app.route("/student/<int:student_id>/activity/new", methods=["GET", "POST"])
def activity_new(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        atype = request.form.get("activity_type", "Technical")
        if not title:
            flash("Activity title is required.", "danger")
            return render_template("activity_form.html", student=student, activity=None)
        if atype not in ["Technical", "Co-curricular", "Extra-curricular"]:
            flash("Activity type must be Technical, Co-curricular, or Extra-curricular.", "danger")
            return render_template("activity_form.html", student=student, activity=None)

        try:
            a = Activity(
                student_id=student.id,
                title=title,
                organizer=request.form.get("organizer", "").strip() or None,
                activity_type=atype,
                held_on=request.form.get("held_on") or None,
                details=request.form.get("details", "").strip() or None
            )
            db.session.add(a)
            db.session.commit()
            sync_after_write("Activity record added successfully")
            return redirect(url_for("student_detail", student_id=student.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save activity: {exc}", "danger")

    return render_template("activity_form.html", student=student, activity=None)

@app.route("/activity/<int:activity_id>/edit", methods=["GET", "POST"])
def activity_edit(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    student = activity.student
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        atype = request.form.get("activity_type", "Technical")
        if not title:
            flash("Activity title is required.", "danger")
            return render_template("activity_form.html", student=student, activity=activity)
        if atype not in ["Technical", "Co-curricular", "Extra-curricular"]:
            flash("Invalid activity type.", "danger")
            return render_template("activity_form.html", student=student, activity=activity)

        try:
            activity.title = title
            activity.organizer = request.form.get("organizer", "").strip() or None
            activity.activity_type = atype
            activity.held_on = request.form.get("held_on") or None
            activity.details = request.form.get("details", "").strip() or None
            db.session.commit()
            sync_after_write("Activity record updated")
            return redirect(url_for("student_detail", student_id=student.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update activity: {exc}", "danger")

    return render_template("activity_form.html", student=student, activity=activity)

@app.route("/activity/<int:activity_id>/delete", methods=["POST"])
def activity_delete(activity_id):
    activity = Activity.query.get(activity_id)
    if not activity:
        flash("Activity record has already been removed.", "info")
        return redirect(url_for("students_list"))
    student_id = activity.student_id
    try:
        db.session.delete(activity)
        db.session.commit()
        sync_after_write("Activity record removed")
        flash("Activity record was successfully deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete activity: {exc}", "danger")
    return redirect(url_for("student_detail", student_id=student_id))

# ---------- Portfolio: Academic Gap / Drop Years ----------

@app.route("/student/<int:student_id>/drop-year/new", methods=["GET", "POST"])
def drop_year_new(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        academic_year = request.form.get("academic_year", "").strip()
        if not academic_year:
            flash("Academic year is required (e.g., 2023-24).", "danger")
            return render_template("drop_year_form.html", student=student, drop_year=None)

        try:
            dy = DropYear(
                student_id=student.id,
                academic_year=academic_year,
                reason=request.form.get("reason", "").strip() or None
            )
            db.session.add(dy)
            db.session.commit()
            sync_after_write("Academic gap year recorded")
            return redirect(url_for("student_detail", student_id=student.id))
        except IntegrityError:
            db.session.rollback()
            flash(f"Gap year for academic year '{academic_year}' is already recorded for this student.", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save gap year: {exc}", "danger")

    return render_template("drop_year_form.html", student=student, drop_year=None)

@app.route("/drop-year/<int:drop_year_id>/edit", methods=["GET", "POST"])
def drop_year_edit(drop_year_id):
    drop_year = DropYear.query.get_or_404(drop_year_id)
    student = drop_year.student
    if request.method == "POST":
        academic_year = request.form.get("academic_year", "").strip()
        if not academic_year:
            flash("Academic year is required.", "danger")
            return render_template("drop_year_form.html", student=student, drop_year=drop_year)

        try:
            drop_year.academic_year = academic_year
            drop_year.reason = request.form.get("reason", "").strip() or None
            db.session.commit()
            sync_after_write("Academic gap year record updated")
            return redirect(url_for("student_detail", student_id=student.id))
        except IntegrityError:
            db.session.rollback()
            flash(f"Gap year for academic year '{academic_year}' is already recorded.", "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update gap year: {exc}", "danger")

    return render_template("drop_year_form.html", student=student, drop_year=drop_year)

@app.route("/drop-year/<int:drop_year_id>/delete", methods=["POST"])
def drop_year_delete(drop_year_id):
    drop_year = DropYear.query.get(drop_year_id)
    if not drop_year:
        flash("Gap year record has already been removed.", "info")
        return redirect(url_for("students_list"))
    student_id = drop_year.student_id
    try:
        db.session.delete(drop_year)
        db.session.commit()
        sync_after_write("Academic gap year record removed")
        flash("Academic gap year record was successfully deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete gap year: {exc}", "danger")
    return redirect(url_for("student_detail", student_id=student_id))

# ---------- Interactive Chart & Progression API ----------

@app.route("/api/student/<int:student_id>/progression")
def api_student_progression(student_id):
    """API endpoint providing semester-wise SGPA/CGPA progression for interactive dashboard charts."""
    student = Student.query.get_or_404(student_id)
    semesters = SemesterResult.query.filter_by(student_id=student.id).order_by(SemesterResult.semester_no).all()
    gap_years = [d.academic_year for d in student.drop_years]

    data = {
        "student_id": student.id,
        "roll_no": student.roll_no,
        "full_name": student.full_name,
        "department": student.department or "",
        "labels": [f"Sem {s.semester_no} ({s.academic_year})" for s in semesters],
        "sgpa": [s.sgpa for s in semesters],
        "cgpa": [s.cgpa for s in semesters],
        "gap_years": gap_years
    }
    return jsonify(data)

# ---------- Utilities: Manual Sync & Realistic Demo Seeder ----------

@app.route("/sync-now", methods=["POST"])
def manual_sync():
    """Manual trigger to push latest DB snapshot to Google Sheets."""
    res = sync_to_google_sheets()
    if "successfully" in res:
        flash(res, "success")
    elif "Skipped" in res:
        flash(res, "info")
    else:
        flash(res, "warning")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/seed-sample-data", methods=["POST"])
def seed_sample_data_route():
    """Populates realistic college records for quick presentation and testing."""
    count = seed_sample_data(force=True)
    sync_to_google_sheets()
    flash(f"Loaded {count} realistic Indian student records across all departments with full semester and portfolio records.", "success")
    return redirect(url_for("dashboard"))

def seed_sample_data(force=False):
    """Seeds 16 realistic Indian engineering student profiles with departments, phone numbers, multi-term progression, and portfolios."""
    if not force and Student.query.count() > 0:
        return 0

    if force:
        # Clear child tables first
        SubjectMark.query.delete()
        SemesterResult.query.delete()
        DropYear.query.delete()
        Seminar.query.delete()
        Activity.query.delete()
        Student.query.delete()
        db.session.commit()

    indian_students = [
        {
            "roll_no": "23FC003",
            "full_name": "Arjun Reddy",
            "email": "arjun.reddy@viva-technology.org",
            "phone": "9801437836",
            "department": "Electronics & Computer Science",
            "admission_year": 2023,
            "secondary_school": "Narayana Olympiad School, Hyderabad",
            "secondary_year": 2021,
            "secondary_percentage": 94.20,
            "higher_secondary_school": "Chaitanya Junior College, Hyderabad",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 92.80,
            "current_status": "Enrolled",
            "semesters": [
                {
                    "sem_no": 1, "year": "2023-24", "sgpa": 8.50, "cgpa": 8.50,
                    "subjects": [
                        ("ECS101", "Engineering Mathematics I", "Theory", 86.0, 100.0),
                        ("ECS102", "Programming in C & Data Structures", "Theory", 88.0, 100.0),
                        ("ECS102L", "C Programming & Logic Lab", "Lab", 47.0, 50.0),
                        ("ECS103", "Basic Electrical & Electronics", "Theory", 82.0, 100.0),
                        ("ECS103L", "Electronics Hardware Lab", "Lab", 44.0, 50.0)
                    ]
                },
                {
                    "sem_no": 2, "year": "2023-24", "sgpa": 8.90, "cgpa": 8.70,
                    "subjects": [
                        ("ECS201", "Digital Logic Design & Verilog", "Theory", 91.0, 100.0),
                        ("ECS201L", "Digital Logic Simulation Lab", "Lab", 48.0, 50.0),
                        ("ECS202", "Object Oriented Programming (Java)", "Theory", 92.0, 100.0),
                        ("ECS202L", "Java & OOP Lab", "Lab", 49.0, 50.0),
                        ("ECS203", "Engineering Mathematics II", "Theory", 84.0, 100.0)
                    ]
                }
            ],
            "gap_years": [],
            "seminars": [
                ("Embedded Systems & IoT in Smart Grids", "IEEE Bombay Section", "External", "2024-02-18", "https://ieee-bombay.org/verify/arjun-23")
            ],
            "activities": [
                ("National Robocon Challenge - Team Hardware Lead", "Doordarshan & MIT Pune", "Technical", "2024-03-05", "Designed motor driver PCBs and sensor integration"),
                ("Inter-Collegiate Volleyball Tournament", "Mumbai University Sports Meet", "Extra-curricular", "2023-11-20", "Runners-up in zonal finals")
            ]
        },
        {
            "roll_no": "23FC001",
            "full_name": "Ananya Sharma",
            "email": "ananya.sharma@viva-technology.org",
            "phone": "9820147821",
            "department": "Computer Engineering",
            "admission_year": 2023,
            "secondary_school": "Delhi Public School, R.K. Puram",
            "secondary_year": 2021,
            "secondary_percentage": 96.40,
            "higher_secondary_school": "Mithibai College of Science, Mumbai",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 95.60,
            "current_status": "Enrolled",
            "semesters": [
                {
                    "sem_no": 1, "year": "2023-24", "sgpa": 9.20, "cgpa": 9.20,
                    "subjects": [
                        ("CS101", "Engineering Mathematics I", "Theory", 94.0, 100.0),
                        ("CS102", "Programming Methodologies (Python)", "Theory", 96.0, 100.0),
                        ("CS102L", "Python Programming Lab", "Lab", 50.0, 50.0)
                    ]
                },
                {
                    "sem_no": 2, "year": "2023-24", "sgpa": 9.45, "cgpa": 9.32,
                    "subjects": [
                        ("CS201", "Data Structures & Analysis", "Theory", 95.0, 100.0),
                        ("CS201L", "Data Structures Lab", "Lab", 50.0, 50.0),
                        ("CS202", "Discrete Mathematical Structures", "Theory", 92.0, 100.0)
                    ]
                }
            ],
            "gap_years": [],
            "seminars": [
                ("Generative AI & LLM Architecture", "Google Developer Groups Mumbai", "External", "2024-01-22", "https://gdg.community.dev/verify/ananya-sharma")
            ],
            "activities": [
                ("Smart India Hackathon 2023 - 1st Position", "AICTE & Ministry of Education", "Technical", "2023-12-19", "Built automated grievance tracking portal for municipal corporations")
            ]
        },
        {
            "roll_no": "21FC042",
            "full_name": "Rohan Deshmukh",
            "email": "rohan.deshmukh@viva-technology.org",
            "phone": "9833124578",
            "department": "Information Technology",
            "admission_year": 2021,
            "secondary_school": "Saraswati Vidyalaya High School, Thane",
            "secondary_year": 2019,
            "secondary_percentage": 89.20,
            "higher_secondary_school": "V.G. Vaze Junior College, Mulund",
            "higher_secondary_year": 2021,
            "higher_secondary_percentage": 88.40,
            "current_status": "Graduated",
            "semesters": [
                { "sem_no": 1, "year": "2021-22", "sgpa": 8.10, "cgpa": 8.10, "subjects": [("IT101", "Structured Programming", "Theory", 82.0, 100.0), ("IT101L", "C Lab", "Lab", 44.0, 50.0)] },
                { "sem_no": 2, "year": "2021-22", "sgpa": 8.30, "cgpa": 8.20, "subjects": [("IT102", "Data Structures", "Theory", 84.0, 100.0), ("IT102L", "DS Lab", "Lab", 45.0, 50.0)] },
                { "sem_no": 3, "year": "2022-23", "sgpa": 8.65, "cgpa": 8.35, "subjects": [("IT201", "Database Systems", "Theory", 89.0, 100.0), ("IT201L", "RDBMS Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 4, "year": "2022-23", "sgpa": 8.90, "cgpa": 8.49, "subjects": [("IT202", "Operating Systems", "Theory", 91.0, 100.0), ("IT202L", "OS Lab", "Lab", 48.0, 50.0)] },
                { "sem_no": 5, "year": "2023-24", "sgpa": 9.10, "cgpa": 8.61, "subjects": [("IT301", "Computer Networks & Security", "Theory", 93.0, 100.0)] },
                { "sem_no": 6, "year": "2023-24", "sgpa": 9.30, "cgpa": 8.73, "subjects": [("IT302", "Cloud Computing & DevOps", "Theory", 94.0, 100.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("AWS Cloud Solutions Architecture Summit", "Amazon Web Services India", "External", "2023-08-14", "https://aws.amazon.com/verify/rohan-deshmukh")
            ],
            "activities": [
                ("ACM Student Chapter - General Secretary", "Viva ACM Student Chapter", "Co-curricular", "2023-07-01", "Organized annual 36-hour code sprint across 15 colleges")
            ]
        },
        {
            "roll_no": "22FC015",
            "full_name": "Priya Patel",
            "email": "priya.patel@viva-technology.org",
            "phone": "9819034567",
            "department": "Computer Engineering",
            "admission_year": 2022,
            "secondary_school": "St. Xavier's High School, Ahmedabad",
            "secondary_year": 2020,
            "secondary_percentage": 91.50,
            "higher_secondary_school": "St. Xavier's Loyola Hall, Ahmedabad",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 90.00,
            "current_status": "Enrolled",
            "semesters": [
                {
                    "sem_no": 1, "year": "2022-23", "sgpa": 8.10, "cgpa": 8.10,
                    "subjects": [("CS101", "Basic Computing", "Theory", 81.0, 100.0), ("CS101L", "Computing Lab", "Lab", 43.0, 50.0)]
                },
                {
                    "sem_no": 2, "year": "2022-23", "sgpa": 8.40, "cgpa": 8.25,
                    "subjects": [("CS102", "Data Structures", "Theory", 86.0, 100.0), ("CS102L", "DS Lab", "Lab", 46.0, 50.0)]
                },
                {
                    "sem_no": 3, "year": "2024-25", "sgpa": 8.80, "cgpa": 8.43,
                    "subjects": [("CS201", "DBMS & SQL", "Theory", 90.0, 100.0), ("CS201L", "DBMS Lab", "Lab", 48.0, 50.0)]
                }
            ],
            "gap_years": [
                ("2023-24", "Medical Leave due to orthopedic ligament reconstructive surgery and recovery")
            ],
            "seminars": [
                ("Women in Tech Leadership Forum", "Microsoft India Academic Guild", "External", "2024-03-08", "https://microsoft.com/certs/priya-patel")
            ],
            "activities": [
                ("State Level Hackathon Finalist", "CSI Maharashtra Chapter", "Technical", "2024-02-14", "Developed assistive screen reader for vernacular languages")
            ]
        },
        {
            "roll_no": "23FC008",
            "full_name": "Aditya Iyer",
            "email": "aditya.iyer@viva-technology.org",
            "phone": "9870123456",
            "department": "Artificial Intelligence & Data Science",
            "admission_year": 2023,
            "secondary_school": "National Public School, Bangalore",
            "secondary_year": 2021,
            "secondary_percentage": 95.80,
            "higher_secondary_school": "National Public School, Bangalore",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 94.60,
            "current_status": "Enrolled",
            "semesters": [
                {
                    "sem_no": 1, "year": "2023-24", "sgpa": 9.15, "cgpa": 9.15,
                    "subjects": [("AI101", "Linear Algebra & Calculus", "Theory", 93.0, 100.0), ("AI102", "Python for AI", "Theory", 95.0, 100.0), ("AI102L", "AI Lab", "Lab", 49.0, 50.0)]
                },
                {
                    "sem_no": 2, "year": "2023-24", "sgpa": 9.50, "cgpa": 9.32,
                    "subjects": [("AI201", "Probability & Statistics for ML", "Theory", 96.0, 100.0), ("AI202", "Data Wrangling & Visualization", "Theory", 95.0, 100.0)]
                }
            ],
            "gap_years": [],
            "seminars": [
                ("Neural Networks & Deep Learning Architectures", "IISc Bangalore AI Conclave", "External", "2024-04-02", "https://iisc.ac.in/verify/aditya-iyer")
            ],
            "activities": [
                ("Kaggle Grandmaster Track - Top 5% Finisher", "Kaggle Global", "Technical", "2024-01-30", "Developed multi-modal sentiment classifier")
            ]
        },
        {
            "roll_no": "22FC022",
            "full_name": "Sneha Kulkarni",
            "email": "sneha.kulkarni@viva-technology.org",
            "phone": "9823456789",
            "department": "Electronics & Telecommunication",
            "admission_year": 2022,
            "secondary_school": "Fergusson Junior College, Pune",
            "secondary_year": 2020,
            "secondary_percentage": 92.40,
            "higher_secondary_school": "Fergusson Junior College, Pune",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 91.20,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2022-23", "sgpa": 8.30, "cgpa": 8.30, "subjects": [("ET101", "Signal Analysis", "Theory", 84.0, 100.0), ("ET101L", "Signals Lab", "Lab", 45.0, 50.0)] },
                { "sem_no": 2, "year": "2022-23", "sgpa": 8.60, "cgpa": 8.45, "subjects": [("ET102", "Analog Circuits", "Theory", 87.0, 100.0), ("ET102L", "Circuits Lab", "Lab", 46.0, 50.0)] },
                { "sem_no": 3, "year": "2023-24", "sgpa": 8.95, "cgpa": 8.62, "subjects": [("ET201", "Electromagnetic Fields", "Theory", 91.0, 100.0), ("ET201L", "RF Lab", "Lab", 48.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("5G NR Architecture and Beamforming", "Telecommunication Standards Development Society India", "External", "2023-10-15", "https://tsdsi.in/certs/sneha")
            ],
            "activities": [
                ("College Cultural Dance Society - Lead Choreographer", "Cultural Committee", "Extra-curricular", "2023-12-10", "1st prize in Classical Group Dance at Mood Indigo")
            ]
        },
        {
            "roll_no": "21FC018",
            "full_name": "Vikram Malhotra",
            "email": "vikram.malhotra@viva-technology.org",
            "phone": "9845123456",
            "department": "Mechanical Engineering",
            "admission_year": 2021,
            "secondary_school": "The Bishop's School, Pune",
            "secondary_year": 2019,
            "secondary_percentage": 88.60,
            "higher_secondary_school": "Modern College of Arts, Science & Commerce, Pune",
            "higher_secondary_year": 2021,
            "higher_secondary_percentage": 87.50,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2021-22", "sgpa": 7.90, "cgpa": 7.90, "subjects": [("ME101", "Engineering Mechanics", "Theory", 80.0, 100.0), ("ME101L", "Mechanics Lab", "Lab", 42.0, 50.0)] },
                { "sem_no": 2, "year": "2021-22", "sgpa": 8.20, "cgpa": 8.05, "subjects": [("ME102", "Thermodynamics", "Theory", 83.0, 100.0), ("ME102L", "Thermal Lab", "Lab", 44.0, 50.0)] },
                { "sem_no": 3, "year": "2022-23", "sgpa": 8.50, "cgpa": 8.20, "subjects": [("ME201", "Fluid Mechanics", "Theory", 86.0, 100.0), ("ME201L", "Fluids Lab", "Lab", 46.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Electric Vehicle Powertrain Simulation", "SAE India International Conference", "External", "2023-09-05", "https://saeindia.org/verify/vikram")
            ],
            "activities": [
                ("BAJA SAE India - Chassis Team Captain", "SAE India", "Technical", "2024-01-25", "Built all-terrain vehicle chassis enduring 4-hour endurance test")
            ]
        },
        {
            "roll_no": "23FC012",
            "full_name": "Meera Nair",
            "email": "meera.nair@viva-technology.org",
            "phone": "9895123456",
            "department": "Computer Engineering",
            "admission_year": 2023,
            "secondary_school": "Bhavan's Vidya Mandir, Kochi",
            "secondary_year": 2021,
            "secondary_percentage": 97.20,
            "higher_secondary_school": "Bhavan's Vidya Mandir, Kochi",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 96.80,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2023-24", "sgpa": 9.50, "cgpa": 9.50, "subjects": [("CS101", "Computational Thinking", "Theory", 97.0, 100.0), ("CS101L", "Computing Lab", "Lab", 50.0, 50.0)] },
                { "sem_no": 2, "year": "2023-24", "sgpa": 9.70, "cgpa": 9.60, "subjects": [("CS102", "Advanced Data Structures", "Theory", 98.0, 100.0), ("CS102L", "Algo Lab", "Lab", 50.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Cryptography & Post-Quantum Algorithms", "IISc Bangalore Summer Forum", "External", "2024-05-12", "https://iisc.ac.in/verify/meera-nair")
            ],
            "activities": [
                ("Google Summer of Code Mentee 2024", "Google Open Source", "Technical", "2024-06-01", "Contributed memory compression patches to the Linux Kernel")
            ]
        },
        {
            "roll_no": "22FC033",
            "full_name": "Siddharth Joshi",
            "email": "siddharth.joshi@viva-technology.org",
            "phone": "9867123456",
            "department": "Information Technology",
            "admission_year": 2022,
            "secondary_school": "St. Stanislaus High School, Bandra, Mumbai",
            "secondary_year": 2020,
            "secondary_percentage": 90.40,
            "higher_secondary_school": "R.D. National College, Bandra",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 89.50,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2022-23", "sgpa": 8.20, "cgpa": 8.20, "subjects": [("IT101", "Foundations of IT", "Theory", 83.0, 100.0), ("IT101L", "IT Lab", "Lab", 44.0, 50.0)] },
                { "sem_no": 2, "year": "2022-23", "sgpa": 8.50, "cgpa": 8.35, "subjects": [("IT102", "Web Technologies", "Theory", 87.0, 100.0), ("IT102L", "Web Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 3, "year": "2023-24", "sgpa": 8.85, "cgpa": 8.52, "subjects": [("IT201", "RDBMS & Big Data", "Theory", 90.0, 100.0), ("IT201L", "SQL Lab", "Lab", 48.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Microservices & Kubernetes Deployment", "Docker Mumbai Community", "Internal", "2023-11-10", "https://viva-technology.org/certs/siddharth-k8s")
            ],
            "activities": [
                ("Inter-College Chess Championship - Gold Medalist", "Mumbai University Sports Board", "Extra-curricular", "2023-10-04", "Undefeated through 7 rounds")
            ]
        },
        {
            "roll_no": "23FC025",
            "full_name": "Pooja Verma",
            "email": "pooja.verma@viva-technology.org",
            "phone": "9811123456",
            "department": "Electronics & Computer Science",
            "admission_year": 2023,
            "secondary_school": "Apeejay School, Noida",
            "secondary_year": 2021,
            "secondary_percentage": 93.80,
            "higher_secondary_school": "Apeejay School, Noida",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 92.60,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2023-24", "sgpa": 8.70, "cgpa": 8.70, "subjects": [("ECS101", "Maths I", "Theory", 88.0, 100.0), ("ECS102", "C Programming", "Theory", 89.0, 100.0), ("ECS102L", "C Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 2, "year": "2023-24", "sgpa": 9.00, "cgpa": 8.85, "subjects": [("ECS201", "Digital Systems", "Theory", 92.0, 100.0), ("ECS202", "OOP Java", "Theory", 91.0, 100.0), ("ECS202L", "Java Lab", "Lab", 48.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("VLSI Chip Design and RISC-V Architecture", "VLSI Society of India", "External", "2024-02-28", "https://vlsisociety.org/certs/pooja")
            ],
            "activities": [
                ("Hackathon 'Hack-A-League' 2nd Runner Up", "IIT Delhi Techfest", "Technical", "2024-03-15", "Built real-time edge processing smart camera module")
            ]
        },
        {
            "roll_no": "21FC050",
            "full_name": "Kartik Subramanian",
            "email": "kartik.subramanian@viva-technology.org",
            "phone": "9840123456",
            "department": "Computer Engineering",
            "admission_year": 2021,
            "secondary_school": "Padma Seshadri Bala Bhavan, Chennai",
            "secondary_year": 2019,
            "secondary_percentage": 94.50,
            "higher_secondary_school": "DAV Boys Senior Secondary School, Chennai",
            "higher_secondary_year": 2021,
            "higher_secondary_percentage": 93.40,
            "current_status": "Graduated",
            "semesters": [
                { "sem_no": 1, "year": "2021-22", "sgpa": 8.60, "cgpa": 8.60, "subjects": [("CS101", "C Programming", "Theory", 87.0, 100.0), ("CS101L", "C Lab", "Lab", 46.0, 50.0)] },
                { "sem_no": 2, "year": "2021-22", "sgpa": 8.80, "cgpa": 8.70, "subjects": [("CS102", "Data Structures", "Theory", 89.0, 100.0), ("CS102L", "DS Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 3, "year": "2022-23", "sgpa": 9.10, "cgpa": 8.83, "subjects": [("CS201", "DBMS", "Theory", 92.0, 100.0), ("CS201L", "DBMS Lab", "Lab", 49.0, 50.0)] },
                { "sem_no": 4, "year": "2022-23", "sgpa": 9.25, "cgpa": 8.94, "subjects": [("CS202", "Operating Systems", "Theory", 94.0, 100.0), ("CS202L", "OS Lab", "Lab", 49.0, 50.0)] },
                { "sem_no": 5, "year": "2023-24", "sgpa": 9.40, "cgpa": 9.03, "subjects": [("CS301", "Algorithms Design", "Theory", 95.0, 100.0)] },
                { "sem_no": 6, "year": "2023-24", "sgpa": 9.60, "cgpa": 9.13, "subjects": [("CS302", "Distributed Systems", "Theory", 97.0, 100.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Distributed Consensus & Raft Protocols", "ACM India Chapter", "External", "2023-11-20", "https://acm.org/verify/kartik-sub")
            ],
            "activities": [
                ("ACM ICPC Regional Finalist", "ICPC Asia Amritapuri", "Technical", "2023-12-24", "Ranked 42nd nationwide in competitive algorithmic programming")
            ]
        },
        {
            "roll_no": "22FC009",
            "full_name": "Ritu Sen",
            "email": "ritu.sen@viva-technology.org",
            "phone": "9830123456",
            "department": "Artificial Intelligence & Data Science",
            "admission_year": 2022,
            "secondary_school": "South Point High School, Kolkata",
            "secondary_year": 2020,
            "secondary_percentage": 92.80,
            "higher_secondary_school": "St. Xavier's Collegiate School, Kolkata",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 91.60,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2022-23", "sgpa": 8.40, "cgpa": 8.40, "subjects": [("AI101", "Linear Algebra", "Theory", 85.0, 100.0), ("AI101L", "Math Lab", "Lab", 44.0, 50.0)] },
                { "sem_no": 2, "year": "2022-23", "sgpa": 8.75, "cgpa": 8.57, "subjects": [("AI102", "Python for Data Science", "Theory", 89.0, 100.0), ("AI102L", "DS Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 3, "year": "2023-24", "sgpa": 9.05, "cgpa": 8.73, "subjects": [("AI201", "Machine Learning Foundations", "Theory", 92.0, 100.0), ("AI201L", "ML Lab", "Lab", 48.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Explainable AI & Fair ML Frameworks", "Indo-German AI Forum", "External", "2024-01-18", "https://ai-forum.org/verify/ritu-sen")
            ],
            "activities": [
                ("Debate Society President", "Literary & Debating Society", "Co-curricular", "2023-09-12", "Best Speaker at All-India Inter-University Parliamentary Debate")
            ]
        },
        {
            "roll_no": "23FC017",
            "full_name": "Harshvardhan Patil",
            "email": "harsh.patil@viva-technology.org",
            "phone": "9822123456",
            "department": "Civil Engineering",
            "admission_year": 2023,
            "secondary_school": "New English School, Satara",
            "secondary_year": 2021,
            "secondary_percentage": 87.40,
            "higher_secondary_school": "Yashwantrao Chavan Institute of Science, Satara",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 86.20,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2023-24", "sgpa": 8.10, "cgpa": 8.10, "subjects": [("CE101", "Engineering Mechanics", "Theory", 82.0, 100.0), ("CE101L", "Surveying Lab", "Lab", 43.0, 50.0)] },
                { "sem_no": 2, "year": "2023-24", "sgpa": 8.35, "cgpa": 8.22, "subjects": [("CE102", "Building Materials & Construction", "Theory", 85.0, 100.0), ("CE102L", "Materials Lab", "Lab", 45.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Sustainable Concrete and Green Building Technologies", "Indian Concrete Institute", "Internal", "2024-03-22", "https://viva-technology.org/certs/harsh-ce")
            ],
            "activities": [
                ("Inter-Collegiate Cricket Tournament - Vice Captain", "Sports Council", "Extra-curricular", "2024-02-10", "Led college cricket team to semi-finals")
            ]
        },
        {
            "roll_no": "22FC041",
            "full_name": "Divya Krishnan",
            "email": "divya.krishnan@viva-technology.org",
            "phone": "9841123456",
            "department": "Information Technology",
            "admission_year": 2022,
            "secondary_school": "Kendriya Vidyalaya CLRI, Chennai",
            "secondary_year": 2020,
            "secondary_percentage": 93.60,
            "higher_secondary_school": "Kendriya Vidyalaya CLRI, Chennai",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 92.10,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2022-23", "sgpa": 8.50, "cgpa": 8.50, "subjects": [("IT101", "C & Logic", "Theory", 86.0, 100.0), ("IT101L", "C Lab", "Lab", 46.0, 50.0)] },
                { "sem_no": 2, "year": "2022-23", "sgpa": 8.80, "cgpa": 8.65, "subjects": [("IT102", "Data Structures", "Theory", 89.0, 100.0), ("IT102L", "DS Lab", "Lab", 47.0, 50.0)] },
                { "sem_no": 3, "year": "2023-24", "sgpa": 9.15, "cgpa": 8.82, "subjects": [("IT201", "Database Engineering", "Theory", 93.0, 100.0), ("IT201L", "SQL Lab", "Lab", 49.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Cyber Threat Intelligence and Zero Trust Security", "DSCI Security Summit", "External", "2023-11-15", "https://dsci.in/verify/divya-krishnan")
            ],
            "activities": [
                ("National Cyber Security Hackathon Finalist", "National Critical Information Infrastructure Protection Centre", "Technical", "2024-01-20", "Detected zero-day vulnerabilities in simulated smart meters")
            ]
        },
        {
            "roll_no": "21FC064",
            "full_name": "Aman Gupta",
            "email": "aman.gupta@viva-technology.org",
            "phone": "9810123456",
            "department": "Computer Engineering",
            "admission_year": 2021,
            "secondary_school": "Modern School, Barakhamba Road, Delhi",
            "secondary_year": 2019,
            "secondary_percentage": 95.20,
            "higher_secondary_school": "Modern School, Barakhamba Road, Delhi",
            "higher_secondary_year": 2021,
            "higher_secondary_percentage": 94.00,
            "current_status": "Graduated",
            "semesters": [
                { "sem_no": 1, "year": "2021-22", "sgpa": 8.70, "cgpa": 8.70, "subjects": [("CS101", "Maths I", "Theory", 88.0, 100.0), ("CS102", "Programming in C", "Theory", 89.0, 100.0)] },
                { "sem_no": 2, "year": "2021-22", "sgpa": 8.95, "cgpa": 8.82, "subjects": [("CS103", "Data Structures", "Theory", 91.0, 100.0)] },
                { "sem_no": 3, "year": "2022-23", "sgpa": 9.20, "cgpa": 8.95, "subjects": [("CS201", "Database Systems", "Theory", 93.0, 100.0)] },
                { "sem_no": 4, "year": "2022-23", "sgpa": 9.40, "cgpa": 9.06, "subjects": [("CS202", "Computer Architecture", "Theory", 95.0, 100.0)] },
                { "sem_no": 5, "year": "2023-24", "sgpa": 9.55, "cgpa": 9.16, "subjects": [("CS301", "Compiler Design", "Theory", 96.0, 100.0)] },
                { "sem_no": 6, "year": "2023-24", "sgpa": 9.75, "cgpa": 9.26, "subjects": [("CS302", "Major Project Capstone", "Lab", 98.0, 100.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("High Performance Computing & GPU Parallelism", "NVIDIA Deep Learning Institute", "External", "2023-10-18", "https://nvidia.com/verify/aman-gupta")
            ],
            "activities": [
                ("Founder & Lead Organizer of College Hackathon 'CodeViva'", "Department of Computer Engineering", "Co-curricular", "2023-09-01", "Managed 800+ participants and raised industry sponsorships")
            ]
        },
        {
            "roll_no": "23FC030",
            "full_name": "Neha Choudhury",
            "email": "neha.choudhury@viva-technology.org",
            "phone": "9831123456",
            "department": "Electronics & Telecommunication",
            "admission_year": 2023,
            "secondary_school": "Loreto House, Kolkata",
            "secondary_year": 2021,
            "secondary_percentage": 93.40,
            "higher_secondary_school": "Loreto House, Kolkata",
            "higher_secondary_year": 2023,
            "higher_secondary_percentage": 92.00,
            "current_status": "Enrolled",
            "semesters": [
                { "sem_no": 1, "year": "2023-24", "sgpa": 8.45, "cgpa": 8.45, "subjects": [("ET101", "Applied Physics", "Theory", 85.0, 100.0), ("ET101L", "Physics Lab", "Lab", 45.0, 50.0)] },
                { "sem_no": 2, "year": "2023-24", "sgpa": 8.75, "cgpa": 8.60, "subjects": [("ET102", "Circuit Theory", "Theory", 88.0, 100.0), ("ET102L", "Circuits Lab", "Lab", 47.0, 50.0)] }
            ],
            "gap_years": [],
            "seminars": [
                ("Optical Fiber Communications & Photonics", "IEEE Photonics Society", "External", "2024-03-12", "https://ieee.org/verify/neha-choudhury")
            ],
            "activities": [
                ("Youth Parliament State Level Representative", "Ministry of Youth Affairs and Sports", "Co-curricular", "2024-01-12", "Represented university on National Education Policy session")
            ]
        }
    ]

    for sd in indian_students:
        student = Student(
            roll_no=sd["roll_no"],
            full_name=sd["full_name"],
            email=sd["email"],
            phone=sd.get("phone"),
            department=sd.get("department"),
            admission_year=sd.get("admission_year"),
            secondary_school=sd["secondary_school"],
            secondary_year=sd["secondary_year"],
            secondary_percentage=sd["secondary_percentage"],
            higher_secondary_school=sd["higher_secondary_school"],
            higher_secondary_year=sd["higher_secondary_year"],
            higher_secondary_percentage=sd["higher_secondary_percentage"],
            current_status=sd["current_status"]
        )
        db.session.add(student)
        db.session.flush()

        for sem_data in sd["semesters"]:
            sem = SemesterResult(
                student_id=student.id,
                semester_no=sem_data["sem_no"],
                academic_year=sem_data["year"],
                sgpa=sem_data["sgpa"],
                cgpa=sem_data["cgpa"]
            )
            db.session.add(sem)
            db.session.flush()

            for scode, sname, stype, marks, maxm in sem_data["subjects"]:
                sub = SubjectMark(
                    semester_id=sem.id,
                    subject_code=scode,
                    subject_name=sname,
                    subject_type=stype,
                    marks_obtained=marks,
                    max_marks=maxm
                )
                db.session.add(sub)

        for yr, reason in sd["gap_years"]:
            dy = DropYear(student_id=student.id, academic_year=yr, reason=reason)
            db.session.add(dy)

        for title, organizer, scope, held_on, cert in sd["seminars"]:
            sem_item = Seminar(
                student_id=student.id,
                title=title,
                organizer=organizer,
                seminar_scope=scope,
                held_on=held_on,
                certificate_url=cert
            )
            db.session.add(sem_item)

        for title, organizer, atype, held_on, details in sd["activities"]:
            act_item = Activity(
                student_id=student.id,
                title=title,
                organizer=organizer,
                activity_type=atype,
                held_on=held_on,
                details=details
            )
            db.session.add(act_item)

    db.session.commit()
    return len(indian_students)

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "app": "Student Academic Progression and Portfolio Management System",
        "database": app.config["SQLALCHEMY_DATABASE_URI"].split(":")[0],
        "students_count": Student.query.count()
    })

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


with app.app_context():
    db.create_all()
    # Check if we should re-seed with the comprehensive Indian student dataset
    # (if students count is low or legacy)
    if Student.query.count() < 10:
        seed_sample_data(force=True)

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print(f"Starting server on http://{host}:{port} (Local: http://127.0.0.1:{port})")
    app.run(debug=debug, host=host, port=port)
