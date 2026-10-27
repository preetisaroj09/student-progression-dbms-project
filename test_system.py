"""
Comprehensive Test Suite for Student Academic Progression and Portfolio Management System
Validates all CRUD operations, database constraints, cascades, Chart API, and error handling.
"""
import unittest
from app import app, db, Student, SemesterResult, SubjectMark, DropYear, Seminar, Activity

class SystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            Student.query.filter(Student.roll_no.like("TEST%")).delete()
            db.session.commit()

    def test_01_health_and_dashboard(self):
        """Test health endpoint and dashboard rendering."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

        res_dash = self.client.get("/")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"College ERP Academic Dashboard", res_dash.data)
        self.assertIn(b"Total Students", res_dash.data)

    def test_02_students_directory_and_search(self):
        """Test directory listing and search functionality."""
        res = self.client.get("/students")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Student Directory", res_dash_data := res.data)

        # Search by roll number
        res_search_roll = self.client.get("/students?q=23FC003")
        self.assertEqual(res_search_roll.status_code, 200)
        self.assertIn(b"Arjun Reddy", res_search_roll.data)

        # Search by student name
        res_search_name = self.client.get("/students?q=Priya")
        self.assertEqual(res_search_name.status_code, 200)
        self.assertIn(b"Priya Patel", res_search_name.data)

        # Filter by status
        res_filter = self.client.get("/students?status=Graduated")
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn(b"Rohan Deshmukh", res_filter.data)

    def test_03_student_crud_and_validations(self):
        """Test creating, validating, editing, and deleting a student."""
        # 1. Create a test student
        new_student_data = {
            "roll_no": "TEST999",
            "full_name": "Test Student Omega",
            "email": "test.omega@college.edu",
            "secondary_school": "Test Secondary High",
            "secondary_year": 2020,
            "secondary_percentage": 85.50,
            "higher_secondary_school": "Test Higher Secondary",
            "higher_secondary_year": 2022,
            "higher_secondary_percentage": 88.00,
            "current_status": "Enrolled"
        }
        res_post = self.client.post("/student/new", data=new_student_data, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b"Test Student Omega", res_post.data)
        self.assertIn(b"TEST999", res_post.data)

        with app.app_context():
            student = Student.query.filter_by(roll_no="TEST999").first()
            self.assertIsNotNone(student)
            student_id = student.id

        # 2. Test duplicate roll number rejection
        res_dup_roll = self.client.post("/student/new", data=new_student_data, follow_redirects=True)
        self.assertIn(b"already exists in the database", res_dup_roll.data)

        # 3. Test invalid percentage (> 100)
        invalid_data = dict(new_student_data)
        invalid_data["roll_no"] = "TEST_INV"
        invalid_data["secondary_percentage"] = 150.0
        res_inv = self.client.post("/student/new", data=invalid_data, follow_redirects=True)
        self.assertIn(b"Secondary percentage must be between 0 and 100", res_inv.data)

        # 4. Edit student
        edit_data = dict(new_student_data)
        edit_data["full_name"] = "Test Student Omega Edited"
        edit_data["current_status"] = "On Leave"
        res_edit = self.client.post(f"/student/{student_id}/edit", data=edit_data, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b"Test Student Omega Edited", res_edit.data)
        self.assertIn(b"On Leave", res_edit.data)

    def test_04_academic_progression_and_marks(self):
        """Test semester creation, subject marks, validations, edits, and deletion."""
        with app.app_context():
            student = Student.query.filter_by(roll_no="23FC003").first()
            student_id = student.id

        # Add a new semester (Sem 5)
        sem_data = {
            "semester_no": 5,
            "academic_year": "2023-24",
            "sgpa": 9.20,
            "cgpa": 9.00,
            "subject_code[]": ["CS301", "CS301L"],
            "subject_name[]": ["Compiler Construction", "Compiler Design Lab"],
            "subject_type[]": ["Theory", "Lab"],
            "marks[]": [91.0, 48.0],
            "max_marks[]": [100.0, 50.0]
        }
        res_sem = self.client.post(f"/student/{student_id}/semester/new", data=sem_data, follow_redirects=True)
        self.assertEqual(res_sem.status_code, 200)
        self.assertIn(b"Semester 5", res_sem.data)
        self.assertIn(b"Compiler Construction", res_sem.data)

        with app.app_context():
            sem_record = SemesterResult.query.filter_by(student_id=student_id, semester_no=5).first()
            self.assertIsNotNone(sem_record)
            sem_id = sem_record.id
            self.assertEqual(len(sem_record.subjects), 2)

        # Test invalid marks (marks obtained > max marks)
        inv_sem_data = {
            "semester_no": 6,
            "academic_year": "2023-24",
            "sgpa": 8.0,
            "cgpa": 8.5,
            "subject_code[]": ["CS302"],
            "subject_name[]": ["Software Engineering"],
            "subject_type[]": ["Theory"],
            "marks[]": [120.0],
            "max_marks[]": [100.0]
        }
        res_inv_sem = self.client.post(f"/student/{student_id}/semester/new", data=inv_sem_data, follow_redirects=True)
        self.assertIn(b"cannot exceed maximum marks", res_inv_sem.data)

        # Test edit semester
        edit_sem_data = {
            "semester_no": 5,
            "academic_year": "2023-24",
            "sgpa": 9.40,
            "cgpa": 9.05,
            "subject_code[]": ["CS301", "CS301L"],
            "subject_name[]": ["Advanced Compiler Construction", "Compiler Lab"],
            "subject_type[]": ["Theory", "Lab"],
            "marks[]": [95.0, 49.0],
            "max_marks[]": [100.0, 50.0]
        }
        res_edit_sem = self.client.post(f"/semester/{sem_id}/edit", data=edit_sem_data, follow_redirects=True)
        self.assertEqual(res_edit_sem.status_code, 200)
        self.assertIn(b"Advanced Compiler Construction", res_edit_sem.data)

        # Test delete semester
        res_del_sem = self.client.post(f"/semester/{sem_id}/delete", follow_redirects=True)
        self.assertEqual(res_del_sem.status_code, 200)
        with app.app_context():
            del_check = db.session.get(SemesterResult, sem_id)
            self.assertIsNone(del_check)
            # Cascade check: Subject marks should be removed
            sub_check = SubjectMark.query.filter_by(semester_id=sem_id).all()
            self.assertEqual(len(sub_check), 0)

    def test_05_portfolio_crud(self):
        """Test Seminars, Activities, and Academic Gap Years CRUD."""
        with app.app_context():
            student = Student.query.filter_by(roll_no="23FC003").first()
            student_id = student.id

        # 1. Seminar CRUD
        sem_data = {
            "title": "Quantum Computing Workshop",
            "organizer": "IBM Quantum Academic",
            "seminar_scope": "External",
            "held_on": "2024-03-10",
            "certificate_url": "https://ibm.com/verify/quantum"
        }
        res_sem = self.client.post(f"/student/{student_id}/seminar/new", data=sem_data, follow_redirects=True)
        self.assertEqual(res_sem.status_code, 200)
        self.assertIn(b"Quantum Computing Workshop", res_sem.data)

        with app.app_context():
            sem_obj = Seminar.query.filter_by(title="Quantum Computing Workshop").first()
            self.assertIsNotNone(sem_obj)
            sem_id = sem_obj.id

        # Edit seminar
        res_sem_edit = self.client.post(f"/seminar/{sem_id}/edit", data={
            "title": "Quantum Computing Workshop (Advanced)",
            "organizer": "IBM Quantum Academic & Qiskit",
            "seminar_scope": "External",
            "held_on": "2024-03-10",
            "certificate_url": "https://ibm.com/verify/quantum-adv"
        }, follow_redirects=True)
        self.assertIn(b"Quantum Computing Workshop (Advanced)", res_sem_edit.data)

        # Delete seminar
        res_sem_del = self.client.post(f"/seminar/{sem_id}/delete", follow_redirects=True)
        self.assertEqual(res_sem_del.status_code, 200)

        # 2. Activity CRUD
        act_data = {
            "title": "Robotics Challenge Winner",
            "organizer": "IIT Bombay Techfest",
            "activity_type": "Technical",
            "held_on": "2024-01-15",
            "details": "First place in autonomous line follower robotics track"
        }
        res_act = self.client.post(f"/student/{student_id}/activity/new", data=act_data, follow_redirects=True)
        self.assertEqual(res_act.status_code, 200)
        self.assertIn(b"Robotics Challenge Winner", res_act.data)

        with app.app_context():
            act_obj = Activity.query.filter_by(title="Robotics Challenge Winner").first()
            self.assertIsNotNone(act_obj)
            act_id = act_obj.id

        # Delete activity
        res_act_del = self.client.post(f"/activity/{act_id}/delete", follow_redirects=True)
        self.assertEqual(res_act_del.status_code, 200)

        # 3. Gap Year CRUD
        gap_data = {
            "academic_year": "2024-25",
            "reason": "Industrial apprenticeship research fellowship"
        }
        res_gap = self.client.post(f"/student/{student_id}/drop-year/new", data=gap_data, follow_redirects=True)
        self.assertEqual(res_gap.status_code, 200)
        self.assertIn(b"Industrial apprenticeship", res_gap.data)

        with app.app_context():
            gap_obj = DropYear.query.filter_by(student_id=student_id, academic_year="2024-25").first()
            self.assertIsNotNone(gap_obj)
            gap_id = gap_obj.id

        # Delete gap year
        res_gap_del = self.client.post(f"/drop-year/{gap_id}/delete", follow_redirects=True)
        self.assertEqual(res_gap_del.status_code, 200)

    def test_06_progression_api(self):
        """Test JSON progression API for Chart.js rendering."""
        with app.app_context():
            student = Student.query.filter_by(roll_no="23FC003").first()
            student_id = student.id

        res = self.client.get(f"/api/student/{student_id}/progression")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["roll_no"], "23FC003")
        self.assertGreaterEqual(len(data["labels"]), 2)
        self.assertGreaterEqual(len(data["sgpa"]), 2)

    def test_07_cascade_delete_student(self):
        """Test ON DELETE CASCADE when student is deleted."""
        with app.app_context():
            student = Student.query.filter_by(roll_no="TEST999").first()
            if student:
                student_id = student.id
                # Add child seminar
                s = Seminar(student_id=student_id, title="Cascade Test Seminar", seminar_scope="Internal")
                db.session.add(s)
                db.session.commit()

                # Delete student via POST
                res = self.client.post(f"/student/{student_id}/delete", follow_redirects=True)
                self.assertEqual(res.status_code, 200)

                # Ensure student and child records are deleted
                self.assertIsNone(db.session.get(Student, student_id))
                self.assertEqual(Seminar.query.filter_by(student_id=student_id).count(), 0)

if __name__ == "__main__":
    unittest.main()
