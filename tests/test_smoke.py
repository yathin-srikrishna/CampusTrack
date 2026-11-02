"""Basic application smoke tests. Install requirements before running pytest."""
import os
import tempfile
import unittest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import College, User, Role, Student


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-only-secret-key-not-for-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_ROOT = tempfile.mkdtemp(prefix="placement-test-")


class AppSmokeTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            college = College(code="TEST01", name="Test College", official_email="office@example.test")
            db.session.add(college)
            db.session.flush()
            admin = User(username="admin@test.example", college_id=college.id, role=Role.COLLEGE_ADMIN.value)
            admin.set_password("Test-password-12345")
            db.session.add(admin)
            student_user = User(username="STU001", college_id=college.id, role=Role.STUDENT.value)
            student_user.set_password("Student-password-12345")
            db.session.add(student_user)
            db.session.flush()
            db.session.add(Student(college_id=college.id, user_id=student_user.id, roll_no="STU001", full_name="Sample Student", email="sample.student@example.test"))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_home_is_public(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get("/auth/login")
        self.assertEqual(response.status_code, 200)

    def test_student_can_login_with_roll_number(self):
        response = self.client.post("/auth/login", data={
            "username": "STU001", "password": "Student-password-12345"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sample Student", response.data)

    def test_student_can_login_with_email(self):
        response = self.client.post("/auth/login", data={
            "username": "SAMPLE.STUDENT@example.test", "password": "Student-password-12345"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sample Student", response.data)


if __name__ == "__main__":
    unittest.main()
