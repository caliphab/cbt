from app import db
from app.models import UserRole, Teacher, Course, Exam, Question, ExamQuestion, ExamAttempt, StudentAnswer, GradeBoundary
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.forms import CourseForm, ExamForm,  QuestionForm, EditQuestionForm, GradeBoundaryForm
from datetime import datetime, timedelta

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.before_request
@login_required
def check_teacher_role():
    if current_user.role != UserRole.TEACHER:
        flash('Access denied. Teacher only area.', 'danger')
        return redirect(url_for('auth.login'))

@teacher_bp.route('/dashboard')
def dashboard():
    teacher = current_user.teacher_profile
    
    courses_query = teacher.courses
    courses = courses_query.all()
    total_courses = courses_query.count()
    
    course_ids = [c.id for c in courses]
    total_exams = Exam.query.filter(Exam.course_id.in_(course_ids)).count() if course_ids else 0
    
    total_questions = Question.query.filter_by(teacher_id=teacher.id).count()
    
    recent_exams = Exam.query.filter(
        Exam.course_id.in_(course_ids)
    ).order_by(Exam.created_at.desc()).limit(10).all() if course_ids else []
    
    return render_template('teacher/dashboard.html',
                         teacher=teacher,
                         courses=courses,
                         total_courses=total_courses,
                         total_exams=total_exams,
                         total_questions=total_questions,
                         recent_exams=recent_exams)

@teacher_bp.route('/courses')
def courses():
    teacher = current_user.teacher_profile
    courses = teacher.courses.order_by(Course.created_at.desc()).all()
    return render_template('teacher/courses.html', courses=courses)

@teacher_bp.route('/course/<int:course_id>')
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    teacher = current_user.teacher_profile
    
    if course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    exams = course.exams.order_by(Exam.created_at.desc()).all()
    
    questions = course.questions.order_by(Question.created_at.desc()).limit(20).all()
    
    return render_template('teacher/view_course.html',
                         course=course,
                         exams=exams,
                         questions=questions)

@teacher_bp.route('/course/create', methods=['GET', 'POST'])
def create_course():
    teacher = current_user.teacher_profile
    form = CourseForm()
    
    if form.validate_on_submit():
        existing = Course.query.filter_by(course_code=form.course_code.data).first()
        if existing:
            flash('A course with this code already exists. Please use a different code.', 'danger')
            return render_template('teacher/create_course.html', form=form)
        
        course = Course(
            course_code=form.course_code.data.upper(),
            course_name=form.course_name.data,
            description=form.description.data,
            teacher_id=teacher.id,
            class_level=form.class_level.data,
            semester=form.semester.data,
            session_year=form.session_year.data,
            is_active=form.is_active.data
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Course "{course.course_name}" created successfully!', 'success')
        return redirect(url_for('teacher.courses'))
    
    return render_template('teacher/create_course.html', form=form)

@teacher_bp.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    teacher = current_user.teacher_profile
    
    if course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = CourseForm(obj=course)
    
    if form.validate_on_submit():
        if form.course_code.data != course.course_code:
            existing = Course.query.filter_by(course_code=form.course_code.data).first()
            if existing:
                flash('A course with this code already exists. Please use a different code.', 'danger')
                return render_template('teacher/edit_course.html', form=form, course=course)
        
        course.course_code = form.course_code.data.upper()
        course.course_name = form.course_name.data
        course.description = form.description.data
        course.class_level = form.class_level.data
        course.semester = form.semester.data
        course.session_year = form.session_year.data
        course.is_active = form.is_active.data
        
        db.session.commit()
        
        flash(f'Course "{course.course_name}" updated successfully!', 'success')
        return redirect(url_for('teacher.view_course', course_id=course.id))
    
    return render_template('teacher/edit_course.html', form=form, course=course)

@teacher_bp.route('/course/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    teacher = current_user.teacher_profile
    
    if course.teacher_id != teacher.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if course.exams.count() > 0:
        return jsonify({
            'error': 'Cannot delete course with existing exams. Delete the exams first.'
        }), 400
    
    course_name = course.course_name
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course "{course_name}" deleted successfully.', 'success')
    return jsonify({'success': True})

@teacher_bp.route('/exams')
def exams():
    teacher = current_user.teacher_profile
    course_ids = [c.id for c in teacher.courses.all()]
    exams = Exam.query.filter(Exam.course_id.in_(course_ids)).order_by(Exam.created_at.desc()).all() if course_ids else []
    return render_template('teacher/exams.html', exams=exams)

@teacher_bp.route('/exam/create', methods=['GET', 'POST'])
def create_exam():
    teacher = current_user.teacher_profile
    
    courses = teacher.courses.all()
    
    if not courses:
        flash('You need to create a course before creating an exam.', 'warning')
        return redirect(url_for('teacher.courses'))
    
    form = ExamForm()
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in courses]
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                local_start = form.start_time.data
                local_end = form.end_time.data
                
                exam = Exam(
                    course_id=form.course_id.data,
                    exam_title=form.exam_title.data,
                    exam_type=form.exam_type.data,
                    duration_minutes=form.duration_minutes.data,
                    start_time=local_start,
                    end_time=local_end,
                    instructions=form.instructions.data,
                    is_active=form.is_active.data,
                    randomize_questions=form.randomize_questions.data,
                    show_results_immediately=form.show_results_immediately.data,
                    max_attempts=form.max_attempts.data,
                    passing_score=form.passing_score.data,
                    created_by=teacher.id
                )
                
                db.session.add(exam)
                db.session.commit()
                
                flash(f'Exam "{exam.exam_title}" created successfully!', 'success')
                return redirect(url_for('teacher.manage_exam', exam_id=exam.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating exam: {str(e)}', 'danger')
        else:
            flash('Please fix the errors in the form.', 'danger')
    
    return render_template('teacher/create_exam.html', form=form)

@teacher_bp.route('/exam/<int:exam_id>')
def manage_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    teacher = current_user.teacher_profile
    
    if exam.course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    questions = exam.exam_questions.order_by(ExamQuestion.question_order).all()
    
    return render_template('teacher/manage_exam.html', exam=exam, questions=questions, timedelta=timedelta)

@teacher_bp.route('/exam/<int:exam_id>/delete', methods=['POST'])
@login_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    teacher = current_user.teacher_profile
    
    if exam.course.teacher_id != teacher.id:
        flash('Access denied. You do not own this exam.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    try:
        exam_title = exam.exam_title
        
        for attempt in exam.attempts:
            StudentAnswer.query.filter_by(attempt_id=attempt.id).delete()
        
        ExamAttempt.query.filter_by(exam_id=exam.id).delete()        
        ExamQuestion.query.filter_by(exam_id=exam.id).delete()
        
        db.session.delete(exam)
        db.session.commit()
        
        flash(f'Exam "{exam_title}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting exam: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.exams'))

@teacher_bp.route('/exam/<int:exam_id>/add_question', methods=['GET', 'POST'])
def add_question(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    teacher = current_user.teacher_profile
    
    if exam.course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = QuestionForm()
    
    form.course_id.choices = [(exam.course_id, f"{exam.course.course_code} - {exam.course.course_name}")]
    form.course_id.data = exam.course_id 
    form.course_id.render_kw = {'readonly': True}
    
    if form.validate_on_submit():
        question = Question(
            course_id=exam.course_id,
            teacher_id=teacher.id,
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            difficulty_level=form.difficulty_level.data,
            points=form.points.data,
            correct_answer=form.correct_answer.data,
            explanation=form.explanation.data,
            media_url=form.media_url.data,
            is_active=True
        )
        
        if form.question_type.data == 'multiple_choice' and form.options.data:
            options = [opt.strip() for opt in form.options.data.split(',')]
            question.options = options
        
        db.session.add(question)
        db.session.flush()
        
        max_order = db.session.query(db.func.max(ExamQuestion.question_order))\
            .filter(ExamQuestion.exam_id == exam.id).scalar() or 0
        
        exam_question = ExamQuestion(
            exam_id=exam.id,
            question_id=question.id,
            question_order=max_order + 1,
            weight=form.points.data
        )
        
        db.session.add(exam_question)
        db.session.commit()
        
        flash('Question added successfully!', 'success')
        return redirect(url_for('teacher.manage_exam', exam_id=exam.id))
    
    return render_template('teacher/add_question.html', form=form, exam=exam)

@teacher_bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    teacher = current_user.teacher_profile
    
    if question.teacher_id != teacher.id:
        flash('Access denied. You do not own this question.', 'danger')
        return redirect(url_for('teacher.question_bank'))
    
    form = EditQuestionForm(obj=question)
    courses = teacher.courses.all()
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in courses]
    
    if question.options:
        form.options.data = ', '.join(question.options)
    
    if form.validate_on_submit():
        try:
            question.course_id = form.course_id.data
            question.question_text = form.question_text.data
            question.question_type = form.question_type.data
            question.difficulty_level = form.difficulty_level.data
            question.points = form.points.data
            question.correct_answer = form.correct_answer.data
            question.explanation = form.explanation.data
            question.media_url = form.media_url.data
            question.is_active = form.is_active.data
            
            if form.question_type.data == 'multiple_choice' and form.options.data:
                options = [opt.strip() for opt in form.options.data.split(',')]
                question.options = options
            else:
                question.options = None
            
            db.session.commit()
            flash('Question updated successfully!', 'success')
            return redirect(url_for('teacher.question_bank'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating question: {str(e)}', 'danger')
    
    return render_template('teacher/edit_question.html', form=form, question=question)

@teacher_bp.route('/question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    teacher = current_user.teacher_profile
    
    if question.teacher_id != teacher.id:
        return jsonify({'error': 'Access denied. You do not own this question.'}), 403
    
    try:
        exam_count = ExamQuestion.query.filter_by(question_id=question.id).count()
        
        if exam_count > 0:
            return jsonify({
                'error': f'Cannot delete question. It is used in {exam_count} exam(s). Remove it from exams first.'
            }), 400
        
        db.session.delete(question)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Question deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teacher_bp.route('/question/<int:question_id>/toggle', methods=['POST'])
@login_required
def toggle_question(question_id):
    question = Question.query.get_or_404(question_id)
    teacher = current_user.teacher_profile
    
    if question.teacher_id != teacher.id:
        return jsonify({'error': 'Access denied'}), 403
    
    question.is_active = not question.is_active
    db.session.commit()
    
    status = 'activated' if question.is_active else 'deactivated'
    return jsonify({
        'success': True, 
        'is_active': question.is_active,
        'message': f'Question {status}'
    })

@teacher_bp.route('/exam/<int:exam_id>/results')
def exam_results(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    teacher = current_user.teacher_profile
    
    if exam.course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    attempts = ExamAttempt.query.filter_by(exam_id=exam_id)\
        .filter(ExamAttempt.status.in_(['submitted', 'graded']))\
        .order_by(ExamAttempt.score.desc()).all()
    
    total_attempts = len(attempts)
    avg_score = 0
    max_score = 0
    min_score = 0
    pass_count = 0
    
    if total_attempts > 0:
        scores = [a.score or 0 for a in attempts]
        avg_score = sum(scores) / total_attempts
        max_score = max(scores)
        min_score = min(scores)
        pass_count = sum(1 for a in attempts if a.grade and a.grade != 'F')
    
    return render_template('teacher/results.html',
                         exam=exam,
                         attempts=attempts,
                         total_attempts=total_attempts,
                         avg_score=avg_score,
                         max_score=max_score,
                         min_score=min_score,
                         pass_count=pass_count)

@teacher_bp.route('/exam/<int:exam_id>/grades', methods=['GET', 'POST'])
def manage_grades(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    teacher = current_user.teacher_profile
    
    if exam.course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = GradeBoundaryForm()
    
    if form.validate_on_submit():
        boundary = GradeBoundary(
            course_id=exam.course_id,
            exam_id=exam.id,
            min_score=form.min_score.data,
            max_score=form.max_score.data,
            letter_grade=form.letter_grade.data,
            remark=form.remark.data
        )
        db.session.add(boundary)
        db.session.commit()
        flash('Grade boundary added!', 'success')
        return redirect(url_for('teacher.manage_grades', exam_id=exam.id))
    
    boundaries = GradeBoundary.query.filter_by(exam_id=exam.id).all()
    return render_template('teacher/grades.html', exam=exam, form=form, boundaries=boundaries)

@teacher_bp.route('/questions/bank')
def question_bank():
    teacher = current_user.teacher_profile
    questions = Question.query.filter_by(teacher_id=teacher.id).order_by(Question.created_at.desc()).all()
    return render_template('teacher/question_bank.html', questions=questions)

@teacher_bp.route('/questions/create', methods=['GET', 'POST'])
def create_question():
    teacher = current_user.teacher_profile
    form = QuestionForm()
    
    courses = teacher.courses.all()
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in courses]
    
    for c in courses:
        print(f"  - Course ID: {c.id}, Code: {c.course_code}")
    
    if form.validate_on_submit():
        print(f"DEBUG: Form submitted - course_id: {form.course_id.data}")
        print(f"DEBUG: Question text: {form.question_text.data}")
        
        if not form.course_id.data:
            flash('Please select a course for this question.', 'danger')
            return render_template('teacher/create_question.html', form=form)
        
        course = Course.query.get(form.course_id.data)
        if not course:
            flash('Selected course does not exist.', 'danger')
            return render_template('teacher/create_question.html', form=form)
                
        question = Question(
            course_id=form.course_id.data, 
            teacher_id=teacher.id,
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            difficulty_level=form.difficulty_level.data,
            points=form.points.data,
            correct_answer=form.correct_answer.data,
            explanation=form.explanation.data,
            media_url=form.media_url.data,
            is_active=True
        )
        
        if form.question_type.data == 'multiple_choice' and form.options.data:
            options = [opt.strip() for opt in form.options.data.split(',')]
            question.options = options
        
        try:
            db.session.add(question)
            db.session.commit()
            flash('Question created successfully!', 'success')
            return redirect(url_for('teacher.question_bank'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating question: {str(e)}', 'danger')
    
    return render_template('teacher/create_question.html', form=form)