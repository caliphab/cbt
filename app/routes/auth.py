from app import db
from app.models import User, Student, Teacher, UserRole
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import LoginForm, RegistrationForm
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard' if current_user.role == UserRole.STUDENT else 'teacher.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.now()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            flash('Login successful!', 'success')
            if user.role == UserRole.STUDENT:
                return redirect(url_for('student.dashboard'))
            elif user.role == UserRole.TEACHER:
                return redirect(url_for('teacher.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))        
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form)
        
        user = User(
            email=form.email.data,
            full_name=form.full_name.data,
            role=UserRole(form.role.data)
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.flush()
        
        if user.role == UserRole.STUDENT:
            student = Student(
                user_id=user.id,
                admission_number=form.admission_number.data,
                class_level=form.class_level.data
            )
            db.session.add(student)
        elif user.role == UserRole.TEACHER:
            teacher = Teacher(
                user_id=user.id,
                staff_id=form.staff_id.data
            )
            db.session.add(teacher)
        
        db.session.commit()
        
        flash('Registration successful!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Log out successful!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)