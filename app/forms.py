from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, EmailField,
    FormField, FileField, HiddenField,
    TextAreaField, SelectField, FieldList,
    IntegerField, FloatField, BooleanField,
    DateTimeField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords do not match')
    ])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher')
    ], validators=[DataRequired()])
    
    admission_number = StringField('Admission Number', validators=[Optional()])
    class_level = StringField('Class Level', validators=[Optional()])
    staff_id = StringField('Staff ID', validators=[Optional()])

class CourseForm(FlaskForm):
    course_code = StringField('Course Code', validators=[
        DataRequired(), 
        Length(min=2, max=20, message='Course code must be between 2 and 20 characters')
    ])
    course_name = StringField('Course Name', validators=[
        DataRequired(), 
        Length(min=3, max=255, message='Course name must be between 3 and 255 characters')
    ])
    description = TextAreaField('Description', validators=[Optional()])
    class_level = StringField('Class Level', validators=[
        DataRequired(),
        Length(max=50)
    ])
    semester = SelectField('Semester', choices=[
        ('First', 'First Semester'),
        ('Second', 'Second Semester'),
        ('Summer', 'Summer Session')
    ], validators=[DataRequired()])
    session_year = StringField('Session Year', validators=[
        DataRequired(),
        Length(max=20, message='Session year must be less than 20 characters')
    ], default='2025/2026')
    is_active = BooleanField('Active', default=True)

class ExamForm(FlaskForm):
    course_id = SelectField('Course', validators=[DataRequired()], coerce=int)
    exam_title = StringField('Exam Title', validators=[DataRequired(), Length(max=255)])
    exam_type = SelectField('Exam Type', choices=[
        ('test', 'Quiz'),
        ('exam', 'Final')
    ], validators=[DataRequired()])
    duration_minutes = IntegerField('Duration (minutes)', validators=[
        DataRequired(),
        NumberRange(min=1, max=180, message='Duration must be between 1 and 180 minutes')
    ])
    start_time = DateTimeField('Start Time', validators=[DataRequired()], format='%Y-%m-%dT%H:%M')
    end_time = DateTimeField('End Time', validators=[DataRequired()], format='%Y-%m-%dT%H:%M')
    instructions = TextAreaField('Instructions')
    is_active = BooleanField('Active', default=True)
    randomize_questions = BooleanField('Randomize Questions', default=False)
    show_results_immediately = BooleanField('Show Results Immediately', default=False)
    max_attempts = IntegerField('Max Attempts', default=1, validators=[NumberRange(min=1, max=10)])
    passing_score = FloatField('Passing Score (%)', default=50.0, validators=[NumberRange(min=0, max=100)])

class QuestionForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[Optional()])
    question_text = TextAreaField('Question', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False')
    ], validators=[DataRequired()])
    difficulty_level = SelectField('Difficulty', choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], default='medium')
    points = FloatField('Points', default=1.0, validators=[NumberRange(min=0.5)])
    correct_answer = StringField('Correct Answer', validators=[DataRequired()])
    explanation = TextAreaField('Explanation (Optional)')
    options = StringField('Options (comma separated for MCQs)', validators=[Optional()])
    media_url = StringField('Media URL (Optional)')
    is_active = BooleanField('Active', default=True)

class EditQuestionForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    question_text = TextAreaField('Question', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False')
    ], validators=[DataRequired()])
    difficulty_level = SelectField('Difficulty', choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], default='medium')
    points = FloatField('Points', default=1.0, validators=[NumberRange(min=0.5)])
    correct_answer = StringField('Correct Answer', validators=[DataRequired()])
    explanation = TextAreaField('Explanation (Optional)')
    options = StringField('Options (comma separated for MCQs)', validators=[Optional()])
    media_url = StringField('Media URL (Optional)')
    is_active = BooleanField('Active', default=True)

class QuestionOptionForm(FlaskForm):
    option_text = StringField('Option', validators=[DataRequired()])
    is_correct = BooleanField('Correct Answer')

class GradeBoundaryForm(FlaskForm):
    min_score = FloatField('Minimum Score', validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_score = FloatField('Maximum Score', validators=[DataRequired(), NumberRange(min=0, max=100)])
    letter_grade = StringField('Letter Grade', validators=[DataRequired(), Length(max=5)])
    remark = StringField('Remark', validators=[Optional(), Length(max=100)])
    