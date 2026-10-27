-- ====================================================================
-- PostgreSQL 3NF Relational Schema Reference
-- Student Academic Progression and Portfolio Management System
-- ====================================================================

-- 1. Students Table
CREATE TABLE IF NOT EXISTS students (
  id BIGSERIAL PRIMARY KEY,
  roll_no VARCHAR(30) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) UNIQUE,
  phone VARCHAR(20),
  department VARCHAR(100),
  admission_year INTEGER,
  secondary_school VARCHAR(160),
  secondary_year INTEGER,
  secondary_percentage NUMERIC(5,2) CHECK (secondary_percentage IS NULL OR (secondary_percentage >= 0 AND secondary_percentage <= 100)),
  higher_secondary_school VARCHAR(160),
  higher_secondary_year INTEGER,
  higher_secondary_percentage NUMERIC(5,2) CHECK (higher_secondary_percentage IS NULL OR (higher_secondary_percentage >= 0 AND higher_secondary_percentage <= 100)),
  current_status VARCHAR(40) NOT NULL DEFAULT 'Enrolled',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Semester Results Table (1:N with students)
CREATE TABLE IF NOT EXISTS semester_results (
  id BIGSERIAL PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  semester_no INTEGER NOT NULL CHECK (semester_no BETWEEN 1 AND 12),
  academic_year VARCHAR(20) NOT NULL,
  sgpa NUMERIC(4,2) NOT NULL CHECK (sgpa BETWEEN 0 AND 10),
  cgpa NUMERIC(4,2) CHECK (cgpa IS NULL OR (cgpa BETWEEN 0 AND 10)),
  CONSTRAINT uq_student_semester UNIQUE(student_id, semester_no)
);

-- 3. Individual Subject & Lab Marks (1:N with semester_results)
CREATE TABLE IF NOT EXISTS subject_marks (
  id BIGSERIAL PRIMARY KEY,
  semester_id BIGINT NOT NULL REFERENCES semester_results(id) ON DELETE CASCADE,
  subject_code VARCHAR(30) NOT NULL,
  subject_name VARCHAR(160) NOT NULL,
  subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN ('Theory','Lab')),
  max_marks NUMERIC(7,2) NOT NULL CHECK (max_marks > 0),
  marks_obtained NUMERIC(7,2) NOT NULL CHECK (marks_obtained >= 0 AND marks_obtained <= max_marks),
  CONSTRAINT uq_semester_subject UNIQUE(semester_id, subject_code)
);

-- 4. Academic Gap / Drop Years (1:N with students)
CREATE TABLE IF NOT EXISTS drop_years (
  id BIGSERIAL PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  academic_year VARCHAR(20) NOT NULL,
  reason VARCHAR(240),
  CONSTRAINT uq_student_drop_year UNIQUE(student_id, academic_year)
);

-- 5. Seminars & Workshops (1:N with students)
CREATE TABLE IF NOT EXISTS seminars (
  id BIGSERIAL PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  title VARCHAR(180) NOT NULL,
  organizer VARCHAR(160),
  seminar_scope VARCHAR(20) NOT NULL CHECK (seminar_scope IN ('Internal','External')),
  held_on DATE,
  certificate_url VARCHAR(400)
);

-- 6. Activities (Technical, Co-curricular, Extra-curricular) (1:N with students)
CREATE TABLE IF NOT EXISTS activities (
  id BIGSERIAL PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  title VARCHAR(180) NOT NULL,
  organizer VARCHAR(160),
  activity_type VARCHAR(30) NOT NULL CHECK (activity_type IN ('Technical','Co-curricular','Extra-curricular')),
  held_on DATE,
  details TEXT
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_students_roll_no ON students(roll_no);
CREATE INDEX IF NOT EXISTS idx_students_full_name ON students(full_name);
CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);
CREATE INDEX IF NOT EXISTS idx_semester_student ON semester_results(student_id);
CREATE INDEX IF NOT EXISTS idx_subject_semester ON subject_marks(semester_id);
CREATE INDEX IF NOT EXISTS idx_drop_student ON drop_years(student_id);
CREATE INDEX IF NOT EXISTS idx_seminar_student ON seminars(student_id);
CREATE INDEX IF NOT EXISTS idx_activity_student ON activities(student_id);
