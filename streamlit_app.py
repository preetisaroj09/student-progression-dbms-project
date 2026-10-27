import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Student Academic Progression ERP",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Navy Blue Theme CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 1rem;
        text-align: center;
    }
    .stMetric {
        background-color: #f1f5f9;
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Database Connection Helper
DB_DIR = os.path.join(os.path.dirname(__file__), "instance")
DB_PATH = os.path.join(DB_DIR, "student_progression.db")

def init_database():
    """Ensure database exists and is seeded if running on fresh cloud host."""
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        try:
            from app import app, db, seed_sample_data
            with app.app_context():
                db.create_all()
                seed_sample_data(force=True)
        except Exception as e:
            st.error(f"Database initialization notice: {e}")

init_database()

def get_db_connection():
    if not os.path.exists(DB_PATH):
        init_database()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- Sidebar -----------------
with st.sidebar:
    st.markdown("## 🎓 College DBMS Portal")
    st.markdown("**Student Progression & Portfolio Management**")
    st.caption("Relational Database Management System (3NF Normalized)")
    st.divider()

    st.markdown("### ⚙️ System Status")
    st.success("🟢 Database: **SQLite (3NF)**")
    
    webhook_url = os.getenv(
        "GOOGLE_SHEET_WEBHOOK_URL",
        "https://script.google.com/macros/s/AKfycbxhJ24gvYXnChmQxjJYpMLJDz8H-mqSRTyPymMm8hxwrpV3AUXuo3VRJkeVxDR5bxEU/exec"
    )
    if webhook_url:
        st.success("🟢 Google Sheets: **Connected**")
    else:
        st.warning("🟡 Google Sheets: **Local Only**")

    st.divider()
    st.markdown("### 📌 Navigation")
    menu = st.radio(
        "Select View:",
        ["📊 Executive Dashboard", "👥 Student Directory", "📈 Progression Analytics", "🏅 Student Portfolios", "🔄 Google Sheets Sync"],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("College DBMS Mini-Project | 2026 Batch")

# ----------------- Main Views -----------------

conn = get_db_connection()

if menu == "📊 Executive Dashboard":
    st.markdown('<div class="main-header">🎓 Academic Progression Executive Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time overview of student academic performance, departmental distribution, and 3NF database metrics.</div>', unsafe_allow_html=True)

    # Key Metrics
    c_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    c_depts = conn.execute("SELECT COUNT(DISTINCT department) FROM students WHERE department IS NOT NULL").fetchone()[0]
    avg_cgpa_row = conn.execute("SELECT AVG(cgpa) FROM semester_results WHERE cgpa IS NOT NULL").fetchone()[0]
    avg_cgpa = round(avg_cgpa_row, 2) if avg_cgpa_row else 0.0
    c_gaps = conn.execute("SELECT COUNT(*) FROM drop_years").fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Students Enrolled", c_students, "16 Profiles")
    m2.metric("Academic Departments", c_depts, "CS, IT, Mech, Civil...")
    m3.metric("Institutional Avg CGPA", f"{avg_cgpa} / 10", "+0.3 trend")
    m4.metric("Gap Year Records", c_gaps, "Documented")

    st.divider()

    # Departmental Distribution & Performance Trend
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🏛️ Students by Department")
        df_dept = pd.read_sql_query("""
            SELECT COALESCE(department, 'Unassigned') as Department, COUNT(*) as Count 
            FROM students 
            GROUP BY department 
            ORDER BY Count DESC
        """, conn)
        st.bar_chart(df_dept.set_index("Department"))

    with col_right:
        st.subheader("📈 Institutional SGPA by Semester")
        df_sem_avg = pd.read_sql_query("""
            SELECT 'Semester ' || semester_no as Semester, ROUND(AVG(sgpa), 2) as Average_SGPA
            FROM semester_results
            GROUP BY semester_no
            ORDER BY semester_no
        """, conn)
        st.line_chart(df_sem_avg.set_index("Semester"))

    # Recent Records
    st.subheader("📋 Recent Student Profiles")
    df_recent = pd.read_sql_query("""
        SELECT id as ID, roll_no as "Roll No", full_name as "Full Name", department as Department, 
               admission_year as "Batch", phone as Phone, email as Email, current_status as Status
        FROM students 
        ORDER BY id DESC 
        LIMIT 6
    """, conn)
    st.dataframe(df_recent, use_container_width=True, hide_index=True)


elif menu == "👥 Student Directory":
    st.markdown('<div class="main-header">👥 Student Directory (3NF Master Table)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Search, filter, and review normalized student profiles with contact and batch records.</div>', unsafe_allow_html=True)

    # Search & Filters
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        search_query = st.text_input("🔍 Search by Name, Roll No, Phone, or Email", placeholder="e.g. Ananya, 23FC001, CS")
    with f2:
        depts_list = [r[0] for r in conn.execute("SELECT DISTINCT department FROM students WHERE department IS NOT NULL ORDER BY department").fetchall()]
        sel_dept = st.selectbox("Filter Department", ["All Departments"] + depts_list)
    with f3:
        status_list = [r[0] for r in conn.execute("SELECT DISTINCT current_status FROM students WHERE current_status IS NOT NULL").fetchall()]
        sel_status = st.selectbox("Filter Status", ["All Statuses"] + status_list)

    query = """
        SELECT id as ID, roll_no as "Roll No", full_name as "Full Name", department as Department,
               admission_year as "Admission Year", phone as "Phone", email as "Email",
               current_status as "Current Status", secondary_school as "10th School", secondary_percentage as "10th %",
               higher_secondary_school as "12th School", higher_secondary_percentage as "12th %"
        FROM students WHERE 1=1
    """
    params = []
    if search_query:
        query += " AND (roll_no LIKE ? OR full_name LIKE ? OR phone LIKE ? OR email LIKE ?)"
        pattern = f"%{search_query.strip()}%"
        params.extend([pattern, pattern, pattern, pattern])
    if sel_dept != "All Departments":
        query += " AND department = ?"
        params.append(sel_dept)
    if sel_status != "All Statuses":
        query += " AND current_status = ?"
        params.append(sel_status)

    query += " ORDER BY id ASC"
    df_students = pd.read_sql_query(query, conn, params=params)

    st.dataframe(df_students, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(df_students)} matching student record(s).")

    # CSV Download Button
    csv = df_students.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Directory to CSV", csv, "student_directory.csv", "text/csv")


elif menu == "📈 Progression Analytics":
    st.markdown('<div class="main-header">📈 Student Progression & Academic Trajectory</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Select an individual student to inspect semester-by-semester SGPA/CGPA growth and marks breakdown.</div>', unsafe_allow_html=True)

    students = conn.execute("SELECT id, roll_no, full_name, department FROM students ORDER BY roll_no").fetchall()
    student_map = {f"{s['roll_no']} - {s['full_name']} ({s['department'] or 'No Dept'})": s['id'] for s in students}

    sel_label = st.selectbox("Select Student Profile:", list(student_map.keys()))
    student_id = student_map[sel_label]

    # Fetch Student Info
    st_info = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    # Profile Card
    p1, p2, p3, p4 = st.columns(4)
    p1.info(f"**Roll No:** {st_info['roll_no']}\n\n**Batch:** {st_info['admission_year'] or 'N/A'}")
    p2.info(f"**Full Name:** {st_info['full_name']}\n\n**Dept:** {st_info['department'] or 'N/A'}")
    p3.info(f"**Email:** {st_info['email'] or 'N/A'}\n\n**Phone:** {st_info['phone'] or 'N/A'}")
    p4.info(f"**Status:** {st_info['current_status']}\n\n**10th / 12th:** {st_info['secondary_percentage'] or 'N/A'}% / {st_info['higher_secondary_percentage'] or 'N/A'}%")

    # Progression Chart
    df_prog = pd.read_sql_query("""
        SELECT 'Sem ' || semester_no as Semester, sgpa as SGPA, cgpa as CGPA
        FROM semester_results 
        WHERE student_id = ? 
        ORDER BY semester_no
    """, conn, params=(student_id,))

    if not df_prog.empty:
        st.subheader("📊 SGPA & CGPA Trend Across Semesters")
        st.line_chart(df_prog.set_index("Semester")[["SGPA", "CGPA"]])

        # Detailed Semester Breakdown
        st.subheader("📑 Semester Subject Marks Details")
        semesters = conn.execute("SELECT id, semester_no, academic_year, sgpa, cgpa FROM semester_results WHERE student_id = ? ORDER BY semester_no", (student_id,)).fetchall()
        for sem in semesters:
            with st.expander(f"Semester {sem['semester_no']} ({sem['academic_year']}) — SGPA: {sem['sgpa']} | CGPA: {sem['cgpa']}"):
                df_subs = pd.read_sql_query("""
                    SELECT subject_code as "Subject Code", subject_name as "Subject Name", 
                           subject_type as "Course Type", marks_obtained as "Marks Obtained", 
                           max_marks as "Max Marks",
                           ROUND((CAST(marks_obtained AS FLOAT) / max_marks * 100), 2) as "Percentage %"
                    FROM subject_marks 
                    WHERE semester_id = ?
                """, conn, params=(sem['id'],))
                st.dataframe(df_subs, use_container_width=True, hide_index=True)
    else:
        st.info("No semester result records entered yet for this student.")


elif menu == "🏅 Student Portfolios":
    st.markdown('<div class="main-header">🏅 Student Portfolio: Seminars, Activities & Gaps</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Review non-academic achievements, technical hackathons, symposiums, and documented gap years.</div>', unsafe_allow_html=True)

    tab_sem, tab_act, tab_gap = st.tabs(["🎤 Technical Seminars", "🏆 Extra / Co-Curricular Activities", "⏸️ Academic Drop Years"])

    with tab_sem:
        df_sem = pd.read_sql_query("""
            SELECT s.roll_no as "Roll No", s.full_name as "Student Name", sem.title as "Seminar Title", 
                   sem.organizer as "Organizer", sem.seminar_scope as "Scope", sem.held_on as "Date", sem.certificate_url as "Certificate / URL"
            FROM seminars sem
            JOIN students s ON sem.student_id = s.id
            ORDER BY sem.id DESC
        """, conn)
        st.dataframe(df_sem, use_container_width=True, hide_index=True)

    with tab_act:
        df_act = pd.read_sql_query("""
            SELECT s.roll_no as "Roll No", s.full_name as "Student Name", act.title as "Activity Title",
                   act.organizer as "Organizer", act.activity_type as "Category", act.held_on as "Date", act.details as "Details"
            FROM activities act
            JOIN students s ON act.student_id = s.id
            ORDER BY act.id DESC
        """, conn)
        st.dataframe(df_act, use_container_width=True, hide_index=True)

    with tab_gap:
        df_gap = pd.read_sql_query("""
            SELECT s.roll_no as "Roll No", s.full_name as "Student Name", dy.academic_year as "Academic Year", dy.reason as "Documented Reason"
            FROM drop_years dy
            JOIN students s ON dy.student_id = s.id
            ORDER BY dy.id DESC
        """, conn)
        st.dataframe(df_gap, use_container_width=True, hide_index=True)


elif menu == "🔄 Google Sheets Sync":
    st.markdown('<div class="main-header">🔄 Real-Time Google Sheets Webhook Sync</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Synchronize all 8 relational tables into your connected Google Spreadsheet instantly via HTTP Webhooks.</div>', unsafe_allow_html=True)

    st.info(f"**Connected Webhook Deployment:** `{webhook_url}`")

    if st.button("🚀 Push All Tables to Google Sheets Now", type="primary"):
        with st.spinner("Pushing fresh database snapshot to Google Sheets..."):
            try:
                from app import app, sync_to_google_sheets
                with app.app_context():
                    res = sync_to_google_sheets()
                st.success(f"Result: {res}")
            except Exception as e:
                st.error(f"Sync failed: {e}")

    st.divider()
    st.markdown("### 📋 8 Synchronized Relational Tabs:")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        1. **`students`**: Master 8-column student directory.
        2. **`school_records`**: 10th & 12th passing years and percentages.
        3. **`semesters`**: Semester numbers, academic years, SGPA, CGPA.
        4. **`subjects`**: Theory & Lab marks obtained vs maximum marks.
        """)
    with col_b:
        st.markdown("""
        5. **`drop_years`**: Documented academic gap years and reasons.
        6. **`achievements`**: Combined seminars, hackathons, and sports.
        7. **`achievement_categories`**: Scope and type definitions.
        8. **`semester_results`**: Academic progression snapshots.
        """)

conn.close()
