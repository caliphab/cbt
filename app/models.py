from flask_login import UserMixin
from app import db, login_manager
from enum import Enum
from datetime import datetime, timedelta

class UserRole(Enum):
    STUDENT = 'student'
    TEACHER = 'teacher'
    ADMIN = 'admin'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    login_status = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    class_level = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100))
    exam_status = db.Column(db.Boolean, default=True)

    exam_attempts = db.relationship('ExamAttempt', backref='student', lazy='dynamic')
    
    def __repr__(self):
        return f'<Student {self.admission_number}>'

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    staff_id = db.Column(db.String(50), unique=True, nullable=False)
    
    courses = db.relationship('Course', backref='teacher', lazy='dynamic')
    questions = db.relationship('Question', backref='teacher', lazy='dynamic')
    
    def __repr__(self):
        return f'<Teacher {self.staff_id}>'

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    class_level = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(20))
    session_year = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    exams = db.relationship('Exam', backref='course', lazy='dynamic')
    questions = db.relationship('Question', backref='course', lazy='dynamic')
    
    def __repr__(self):
        return f'<Course {self.course_code}>'

class Exam(db.Model):
    __tablename__ = 'exams'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    exam_title = db.Column(db.String(255), nullable=False)
    exam_type = db.Column(db.Enum('test', 'exam'), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    instructions = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    randomize_questions = db.Column(db.Boolean, default=False)
    show_results_immediately = db.Column(db.Boolean, default=False)
    max_attempts = db.Column(db.Integer, default=1)
    passing_score = db.Column(db.Float, default=50.0)
    created_by = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    exam_questions = db.relationship('ExamQuestion', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    attempts = db.relationship('ExamAttempt', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    grade_boundaries = db.relationship('GradeBoundary', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def total_questions(self):
        return self.exam_questions.count()
    
    @property
    def is_available(self):
        now = datetime.now()        
        
        return (self.is_active and 
                self.start_time <= now <= self.end_time)
    
    @property
    def is_upcoming(self):
        now = datetime.now()
        return self.is_active and self.start_time > now
    
    @property
    def is_past(self):
        now = datetime.now()
        return self.end_time < now
    
    @property
    def status(self):
        if not self.is_active:
            return 'not available'
        if self.is_available:
            return 'available'
        if self.is_upcoming:
            return 'upcoming'
        if self.is_past:
            return 'ended'
        return 'not available'
    
    def __repr__(self):
        return f'<Exam {self.exam_title}>'

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum('multiple_choice', 'true_false'), nullable=False)
    difficulty_level = db.Column(db.Enum('easy', 'medium', 'hard'), default='medium')
    points = db.Column(db.Float, default=1.0)
    options = db.Column(db.JSON)
    correct_answer = db.Column(db.String(255), nullable=False)
    explanation = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    
    exam_questions = db.relationship('ExamQuestion', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    student_answers = db.relationship('StudentAnswer', backref='question', lazy='dynamic')
    
    def __repr__(self):
        return f'<Question {self.id}>'

class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question_order = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, default=1.0)
    
    __table_args__ = (
        db.UniqueConstraint('exam_id', 'question_id', name='unique_exam_question'),
    )

class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.Enum('in_progress', 'submitted', 'timed_out', 'graded'), default='in_progress')
    attempt_number = db.Column(db.Integer, default=1)
    score = db.Column(db.Float)
    total_score = db.Column(db.Float)
    grade = db.Column(db.String(5))
    
    answers = db.relationship('StudentAnswer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('exam_id', 'student_id', 'attempt_number', name='unique_attempt'),
    )
    
    @property
    def time_remaining_seconds(self):
        if self.status != 'in_progress':
            return 0
        exam = Exam.query.get(self.exam_id)
        end_time = self.start_time + timedelta(minutes=exam.duration_minutes)
        remaining = (end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def __repr__(self):
        return f'<ExamAttempt {self.id} - {self.status}>'

class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_answer = db.Column(db.String(255))
    is_correct = db.Column(db.Boolean)
    points_awarded = db.Column(db.Float, default=0)
    time_spent_seconds = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='unique_attempt_question'),
    )  

class GradeBoundary(db.Model):
    __tablename__ = 'grade_boundaries'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=True)
    min_score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False)
    letter_grade = db.Column(db.String(5), nullable=False)
    remark = db.Column(db.String(100))
    
    __table_args__ = (
        db.UniqueConstraint('exam_id', 'letter_grade', name='unique_grade_per_exam'),
    )

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    
    user = db.relationship('User', backref='audit_logs')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))