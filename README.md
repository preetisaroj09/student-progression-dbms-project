# Student Academic Progression and Portfolio Management System

A production-grade **College ERP & Academic Progression DBMS Mini-Project** built using Flask, SQLAlchemy ORM, Bootstrap 5, and Chart.js, featuring dual-engine support for **SQLite** (instant out-of-the-box local demo) and **PostgreSQL** (for formal academic submission and deployment), alongside optional one-way **Google Sheets** cloud synchronization.

---

## 🌟 Key Features

### 1. Modern College ERP Dashboard (`/`)
- **Real-Time Key Metrics**: Instant SQL aggregation of Total Students, Enrolled Count, Graduated Alumni, Recorded Semesters, Portfolio Events (Seminars & Activities), and Academic Gap Years.
- **Dynamic Interactive Trend Chart**: Real-time Chart.js line graph plotting semester-wise SGPA and cumulative CGPA. Includes an interactive dropdown to switch between any student in the database on the fly.
- **Recent Student Records**: Quick summary table with status badges, progression summaries, and one-click actions.
- **Academic Gap Warning Banner**: Automatically alerts administrators when a student has a recorded academic drop year.

### 2. Comprehensive Student Management (`/students`)
- **Full CRUD Operations**:
  - Add new student profiles with validation.
  - View detailed student dossier & academic timeline.
  - Edit student particulars and enrollment status.
  - Delete student records with confirmation dialog (cascading cleanly across all dependent tables).
- **Search & Filters**: Quick real-time search across student roll numbers, names, and email addresses, with filter controls by enrollment status (`Enrolled`, `Graduated`, `On Leave`, `Discontinued`).
- **Academic Qualifications Stored**:
  - Secondary School (10th) name, passing year, and percentage score.
  - Higher Secondary School / Junior College (12th / Diploma) name, passing year, and percentage score.

### 3. Academic Progression & Grade Analytics
- **Semester Results**: Semester terms (1 to 12), academic year (e.g., `2024-25`), SGPA (0.0 to 10.0), and CGPA (0.0 to 10.0).
- **Course & Lab Marks**: Segregated recording for individual **Theory** and **Lab** subjects with subject code, course name, marks obtained, and maximum marks.
- **Progression Line Charts**: High-resolution Chart.js curves displaying SGPA trajectory vs. cumulative CGPA with gap-year markers.
- **Database Constraints**: Server-side and database-level enforcement of SGPA/CGPA ranges, non-negative marks, and marks $\le$ maximum marks.

### 4. Categorized Portfolio Management
Maintained in distinct, dedicated sections in both the database and the user interface:
- **Seminars & Workshops**: Presentation/attendance title, organizer, scope (`Internal` vs. `External`), date, and clickable certificate verification links.
- **Activities & Achievements**: Title, organizer, category (`Technical` like hackathons/coding, `Co-curricular` like student chapters/debates, and `Extra-curricular` like sports/cultural events), date, and details.
- **Academic Gap / Drop Years**: Formally recorded drop years (e.g., `2023-24`) and documented reasons (e.g., medical leave, entrance exam preparation, research fellowship).

### 5. Google Sheets One-Way Cloud Synchronization
- Automatically updates a target Google Spreadsheet across 6 normalized tabs on every successful GUI create, edit, or delete:
  1. `Students`
  2. `Semesters`
  3. `Subject Marks`
  4. `Drop Years`
  5. `Seminars`
  6. `Activities`
- **Fail-Safe Fallback**: If Google API credentials or spreadsheet IDs are not configured or internet access is offline, the local database remains 100% operational, and an informative status indicator informs the user without throwing exceptions.
- Includes a manual **"Sync to Sheets Now"** button in the sidebar.

---

## 🏗️ 3NF Relational Database Architecture

The schema is normalized to **Third Normal Form (3NF)**:
- **`students`**: Primary key `id`, unique `roll_no`, `full_name`, unique `email`, secondary school attributes, higher secondary attributes, `current_status`, `created_at`.
- **`semester_results`**: Primary key `id`, foreign key `student_id` referencing `students(id)` with `ON DELETE CASCADE`, `semester_no`, `academic_year`, `sgpa`, `cgpa`. Unique constraint on `(student_id, semester_no)`.
- **`subject_marks`**: Primary key `id`, foreign key `semester_id` referencing `semester_results(id)` with `ON DELETE CASCADE`, `subject_code`, `subject_name`, `subject_type`, `marks_obtained`, `max_marks`. Unique constraint on `(semester_id, subject_code)`.
- **`drop_years`**: Primary key `id`, foreign key `student_id` referencing `students(id)` with `ON DELETE CASCADE`, `academic_year`, `reason`. Unique constraint on `(student_id, academic_year)`.
- **`seminars`**: Primary key `id`, foreign key `student_id` referencing `students(id)` with `ON DELETE CASCADE`, `title`, `organizer`, `seminar_scope`, `held_on`, `certificate_url`.
- **`activities`**: Primary key `id`, foreign key `student_id` referencing `students(id)` with `ON DELETE CASCADE`, `title`, `organizer`, `activity_type`, `held_on`, `details`.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.15)
- Internet connection (for CDN assets Bootstrap 5 and Chart.js)

### Installation & Execution (Windows)
```powershell
# Navigate into the project folder
cd "c:\Users\Preeti Saroj\OneDrive\Desktop\student_progression_dbms_project"

# Create a virtual environment
py -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt

# Start the application
python app.py
```

### Installation & Execution (macOS / Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

*Note: On clean first startup, the application automatically seeds realistic engineering student records complete with multiple semesters, theory & lab marks, seminars, activities, and gap years so the dashboard is immediately demonstrable.*

---

## 🐘 PostgreSQL Setup (For Submission / Production)

1. Create a database in PostgreSQL:
   ```sql
   CREATE DATABASE student_progression;
   ```
2. Configure the connection URL in `.env`:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/student_progression
   ```
3. Start the application (`python app.py`). SQLAlchemy will create the normalized schema automatically.
4. Alternatively, execute `schema.sql` directly using `psql`:
   ```bash
   psql -U postgres -d student_progression -f schema.sql
   ```

---

## 📊 Google Sheets Cloud Integration Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** under *IAM & Admin* > *Service Accounts*.
4. Generate a JSON Key for the service account and save it as `service-account.json` in the project root directory.
5. Create a new Google Spreadsheet and copy its Spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
6. Share the Google Spreadsheet with the service account email (found in `client_email` inside the JSON key) as **Editor**.
7. In `.env`, set:
   ```env
   GOOGLE_SHEET_ID=your_spreadsheet_id_here
   GOOGLE_SERVICE_ACCOUNT_JSON=service-account.json
   ```
8. Restart `app.py`. The top navbar will display **Active Sync**, and every create, edit, and delete operation will refresh the 6 spreadsheet tabs automatically.

---

## 🧪 Automated Test Suite

A comprehensive test suite covering all CRUD operations, database constraint validations, cascading deletions, and progression JSON APIs is included in `test_system.py`.

Run the automated test suite with:
```bash
python -m unittest test_system.py
```
Expected output:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.58s

OK
```

---

## 🛡️ Constraints & Error Handling Matrix

| Constraint | Database Level | Application Level | User Feedback |
| :--- | :--- | :--- | :--- |
| **Roll Number Uniqueness** | `UNIQUE` constraint | Pre-save verification | Flash alert: Duplicate roll number rejected |
| **Email Uniqueness** | `UNIQUE` constraint | Nullable unique check | Flash alert: Email already registered |
| **Semester Number Range** | `CHECK (1 TO 12)` | Min/Max input validation | Flash alert: Semester must be between 1 and 12 |
| **SGPA & CGPA Range** | `CHECK (0.0 TO 10.0)` | Step 0.01 validation | Flash alert: Grade point must be between 0.0 and 10.0 |
| **Marks Integrity** | `CHECK (0 <= marks <= max)` | Form bound validation | Flash alert: Marks obtained cannot exceed maximum marks |
| **Subject Type** | `CHECK IN ('Theory','Lab')` | Strict select options | Flash alert: Invalid subject type |
| **Seminar Scope** | `CHECK IN ('Internal','External')` | Controlled dropdown | Flash alert: Scope must be Internal or External |
| **Activity Category** | `CHECK IN ('Technical','Co-curricular','Extra-curricular')` | Controlled dropdown | Flash alert: Controlled category requirement |
| **Cascading Deletions** | `ON DELETE CASCADE` | ORM `cascade="all, delete-orphan"` | Deleting student or semester cascades cleanly without orphaned rows |
