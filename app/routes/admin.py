from app import db
from app.models import User, Student, Teacher, Course, Exam, Question, ExamAttempt, StudentAnswer, ExamQuestion, UserRole
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def check_admin_role():
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin only area.', 'danger')
        return redirect(url_for('auth.login'))

@admin_bp.route('/dashboard')
def dashboard():
    total_users = User.query.count()
    total_admins = User.query.filter_by(role=UserRole.ADMIN).count()
    total_teachers = Teacher.query.count()
    total_students = Student.query.count()

    total_courses = Course.query.count()
    total_exams = Exam.query.count()
    total_questions = Question.query.count()
    

    total_attempts = ExamAttempt.query.count()
    completed_attempts = ExamAttempt.query.filter(
        ExamAttempt.status.in_(['submitted', 'graded'])
    ).count()

    avg_score = db.session.query(func.avg(ExamAttempt.score))\
        .filter(ExamAttempt.status.in_(['submitted', 'graded']))\
        .scalar() or 0
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_exams = Exam.query.order_by(Exam.created_at.desc()).limit(10).all()
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_teachers=total_teachers,
        total_admins=total_admins,
        total_courses=total_courses,
        total_exams=total_exams,
        total_questions=total_questions,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        avg_score=avg_score,
        recent_users=recent_users,
        recent_exams=recent_exams
    )

@admin_bp.route('/users')
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/courses')
def courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)

@admin_bp.route('/exams')
def exams():
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams)

@admin_bp.route('/system/stats')
def system_stats():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    users_by_day = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago)\
     .group_by(func.date(User.created_at))\
     .order_by(func.date(User.created_at))\
     .all()
    
    attempts_by_status = db.session.query(
        ExamAttempt.status,
        func.count(ExamAttempt.id).label('count')
    ).group_by(ExamAttempt.status).all()
    
    return render_template(
        'admin/stats.html',
        users_by_day=users_by_day,
        attempts_by_status=attempts_by_status
    )

@admin_bp.route('/settings')
def settings():
    return render_template('admin/settings.html')

@admin_bp.route('/user/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    if user.role == UserRole.ADMIN and user.is_active:
        if user.email == "exampleadmin@gmail.com":
            flash('You are not allowed to perform this action', 'danger')
            return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status} successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)    
    
    if user.id == current_user.id:
        flash('You cannot delete yourself', 'danger')
        return redirect(url_for('admin.users'))

    if user.email == "exampleadmin@gmail.com":
        flash('You are not allowed to perform this action', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        if user.student_profile:
            db.session.delete(user.student_profile)
        if user.teacher_profile:
            db.session.delete(user.teacher_profile)
        
        db.session.delete(user)
        db.session.commit()
        
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/promote', methods=['POST'])
def promote_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.email == "exampleadmin@gmail.com":
        flash('You are not allowed to perform this action', 'danger')
        return redirect(url_for('admin.users'))
    
    if user.role == UserRole.ADMIN:
        flash('User is already an admin', 'warning')
        return redirect(url_for('admin.users')) 
    
    if user.role != UserRole.TEACHER:
        flash('Only Teachers account can be promoted', 'warning')
        return redirect(url_for('admin.users'))
    
    user.role = UserRole.ADMIN
    db.session.commit()
    
    flash(f'{user.full_name} is now an admin!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/demote', methods=['POST'])
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot demote your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    if user.role != UserRole.ADMIN:
        flash('User is not an admin', 'warning')
        return redirect(url_for('admin.users'))
    
    
    if user.email == "exampleadmin@gmail.com":
        flash('You are not allowed to perform this action', 'danger')
        return redirect(url_for('admin.users'))
    
    user.role = UserRole.TEACHER
    db.session.commit()
    
    flash(f'{user.full_name} demoted to Teacher', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/course/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    try:
        if course.exams.count() > 0:
            flash('Cannot delete course with existing exams. Delete the exams first.', 'danger')
            return redirect(url_for('admin.courses'))
        
        db.session.delete(course)
        db.session.commit()
        
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
    
    return redirect(url_for('admin.courses'))

@admin_bp.route('/exam/<int:exam_id>/delete', methods=['POST'])
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    
    try:
        for attempt in exam.attempts:
            StudentAnswer.query.filter_by(attempt_id=attempt.id).delete()
        ExamAttempt.query.filter_by(exam_id=exam.id).delete()
        ExamQuestion.query.filter_by(exam_id=exam.id).delete()
        
        db.session.delete(exam)
        db.session.commit()
        
        flash('Exam deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting exam: {str(e)}', 'danger')
    
    return redirect(url_for('admin.exams'))