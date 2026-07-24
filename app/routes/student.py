from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models import (
    Exam, ExamAttempt, StudentAnswer, 
    Question, ExamQuestion, GradeBoundary,
    Course, AuditLog, UserRole
)
from datetime import datetime
import random

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@login_required
def check_student_role():
    if current_user.role != UserRole.STUDENT:
        flash('Access denied. Student only area.', 'danger')
        return redirect(url_for('auth.login'))

@student_bp.route('/dashboard')
def dashboard():
    student = current_user.student_profile
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    now = datetime.now()
    
    upcoming_exams = Exam.query.filter(
        Exam.is_active == True,
        Exam.start_time > now
    ).order_by(Exam.start_time).limit(5).all()
    
    available_exams = Exam.query.filter(
        Exam.is_active == True,
        Exam.start_time <= now,
        Exam.end_time >= now
    ).order_by(Exam.start_time).limit(5).all()
    
    attempts = ExamAttempt.query.filter_by(student_id=student.id)\
        .order_by(ExamAttempt.start_time.desc()).limit(10).all()
    
    completed_attempts_query = ExamAttempt.query.filter(
        ExamAttempt.student_id == student.id,
        ExamAttempt.status.in_(['submitted', 'graded'])
    )
    completed_attempts = completed_attempts_query.all()
    total_exams_taken = completed_attempts_query.count()
    
    average_score = 0
    if completed_attempts:
        scores = [a.score or 0 for a in completed_attempts if a.score is not None]
        if scores:
            average_score = sum(scores) / len(scores)
    
    return render_template('student/dashboard.html',
                         student=student,
                         upcoming_exams=upcoming_exams,
                         available_exams=available_exams,
                         attempts=attempts,
                         total_exams_taken=total_exams_taken,
                         average_score=average_score)

@student_bp.route('/exams')
def exam_list():
    student = current_user.student_profile
    now = datetime.now()
    
    all_exams = Exam.query.filter_by(is_active=True).all()
    
    available_exams = []
    upcoming_exams = []
    past_exams = []
    
    for exam in all_exams:
        if exam.is_available:
            available_exams.append(exam)
        elif exam.is_upcoming:
            upcoming_exams.append(exam)
        elif exam.is_past:
            past_exams.append(exam)
    
    available_exams.sort(key=lambda x: x.start_time)
    upcoming_exams.sort(key=lambda x: x.start_time)
    past_exams.sort(key=lambda x: x.start_time, reverse=True)
    
    attempt_counts = {}
    for exam in available_exams + upcoming_exams + past_exams:
        count = ExamAttempt.query.filter_by(
            exam_id=exam.id,
            student_id=student.id,
            status='submitted'
        ).count()
        attempt_counts[exam.id] = count
    
    return render_template('student/exam_list.html',
                         available_exams=available_exams,
                         upcoming_exams=upcoming_exams,
                         past_exams=past_exams,
                         attempt_counts=attempt_counts)

@student_bp.route('/exam/<int:exam_id>/take')
@login_required  
def take_exam(exam_id):
    student = current_user.student_profile
    exam = Exam.query.get_or_404(exam_id)
    
    if not exam.is_available:
        flash('This exam is not available.', 'warning')
        return redirect(url_for('student.exam_list'))
    
    if exam.exam_questions.count() == 0:
        flash('This exam has no questions. Please contact your teacher.', 'warning')
        return redirect(url_for('student.exam_list'))
    
    attempts_count = ExamAttempt.query.filter_by(
        exam_id=exam_id,
        student_id=student.id
    ).filter(ExamAttempt.status.in_(['submitted', 'timed_out'])).count()
    
    if attempts_count >= exam.max_attempts:
        flash(f'Maximum attempts ({exam.max_attempts}) reached.', 'warning')
        return redirect(url_for('student.exam_list'))
    
    in_progress = ExamAttempt.query.filter_by(
        exam_id=exam_id,
        student_id=student.id,
        status='in_progress'
    ).first()
    
    if in_progress:
        if in_progress.time_remaining_seconds > 0:
            return redirect(url_for('student.continue_exam', attempt_id=in_progress.id))
        else:
            in_progress.status = 'timed_out'
            db.session.commit()
    
    return render_template('student/take_exam.html',
                         exam=exam,
                         attempt=None,
                         question_ids=[],
                         answered_questions=[],
                         Question=Question)

@student_bp.route('/exam/start/<int:exam_id>', methods=['POST'])
@login_required  
def start_exam(exam_id):
    try:
        student = current_user.student_profile
        if not student:
            return jsonify({'error': 'Student profile not found'}), 400
        
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        if not exam.is_available:
            return jsonify({'error': 'Exam is not available at this time.'}), 400
        
        if exam.exam_questions.count() == 0:
            return jsonify({'error': 'This exam has no questions.'}), 400
        
        existing = ExamAttempt.query.filter_by(
            exam_id=exam_id,
            student_id=student.id,
            status='in_progress'
        ).first()
        
        if existing:
            return jsonify({
                'success': True,
                'attempt_id': existing.id,
                'redirect': url_for('student.continue_exam', attempt_id=existing.id)
            })
        
        attempts_count = ExamAttempt.query.filter_by(
            exam_id=exam_id,
            student_id=student.id,
            status='submitted'
        ).count()
        
        if attempts_count >= exam.max_attempts:
            return jsonify({
                'error': f'Maximum attempts ({exam.max_attempts}) reached.'
            }), 400
        
        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=student.id,
            attempt_number=attempts_count + 1,
            status='in_progress',
            start_time=datetime.now()
        )

        db.session.add(attempt)
        db.session.flush()
                
        exam_questions = exam.exam_questions.order_by(ExamQuestion.question_order).all()
        
        if exam.randomize_questions:
            question_list = list(exam_questions)
            random.shuffle(question_list)
        else:
            question_list = exam_questions
        
        session[f'exam_{exam.id}_questions'] = [eq.question_id for eq in question_list]
        
        db.session.commit()
        
        audit = AuditLog(
            user_id=current_user.id,
            action='START_EXAM',
            exam_id=exam_id,
            details={'attempt_id': attempt.id},
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'attempt_id': attempt.id,
            'redirect': url_for('student.continue_exam', attempt_id=attempt.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/exam/continue/<int:attempt_id>')
@login_required
def continue_exam(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    student = current_user.student_profile
    
    if attempt.student_id != student.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if attempt.status != 'in_progress':
        flash('This attempt has already been completed.', 'info')
        return redirect(url_for('student.view_result', attempt_id=attempt.id))
    
    if attempt.time_remaining_seconds <= 0:
        attempt.status = 'timed_out'
        db.session.commit()
        flash('Time is up! Your exam has been submitted.', 'warning')
        return redirect(url_for('student.view_result', attempt_id=attempt.id))
    
    exam = attempt.exam
    
    question_ids = session.get(f'exam_{exam.id}_questions', [])
    
    if not question_ids:
        exam_questions = exam.exam_questions.order_by(ExamQuestion.question_order).all()
        question_ids = [eq.question_id for eq in exam_questions]
    
    answered_questions = [ans.question_id for ans in attempt.answers]
    
    return render_template('student/take_exam.html',
                         exam=exam,
                         attempt=attempt,
                         question_ids=question_ids,
                         answered_questions=answered_questions,
                         Question=Question)

@student_bp.route('/exam/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    try:
        data = request.get_json()
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        selected_answer = data.get('selected_answer')
        time_spent = data.get('time_spent', 0)
        
        attempt = ExamAttempt.query.get_or_404(attempt_id)
        
        if attempt.student_id != current_user.student_profile.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if attempt.status != 'in_progress':
            return jsonify({'error': 'Exam already submitted'}), 400
        
        question = Question.query.get_or_404(question_id)
        
        answer = StudentAnswer.query.filter_by(
            attempt_id=attempt_id,
            question_id=question_id
        ).first()
        
        if not answer:
            answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                time_spent_seconds=0
            )
            db.session.add(answer)

        answer.selected_answer = selected_answer
        answer.time_spent_seconds = (answer.time_spent_seconds or 0) + time_spent
        
        if question.question_type != 'essay':
            if question.question_type == 'multiple_choice':
                answer.is_correct = selected_answer == question.correct_answer
            elif question.question_type == 'true_false':
                answer.is_correct = selected_answer.lower() == question.correct_answer.lower()
            elif question.question_type == 'fill_blank':
                answer.is_correct = selected_answer.lower().strip() == question.correct_answer.lower().strip()
            
            answer.points_awarded = question.points if answer.is_correct else 0
        
        answer.answered_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/exam/submit/<int:attempt_id>', methods=['POST'])
@login_required
def submit_exam(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    student = current_user.student_profile
    
    if attempt.student_id != student.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if attempt.status != 'in_progress':
        return jsonify({'error': 'Exam already submitted'}), 400
    
    try:
        attempt.end_time = datetime.now()
        attempt.status = 'submitted'
        
        answers = attempt.answers.all()
        total_score = sum(a.points_awarded or 0 for a in answers)
        total_possible = sum(eq.weight for eq in attempt.exam.exam_questions)
        
        attempt.score = total_score
        attempt.total_score = total_possible
        
        if total_possible > 0:
            percentage = (total_score / total_possible) * 100
            
            grade_boundary = GradeBoundary.query.filter(
                GradeBoundary.exam_id == attempt.exam_id,
                GradeBoundary.min_score <= percentage,
                GradeBoundary.max_score >= percentage
            ).first()
            
            if grade_boundary:
                attempt.grade = grade_boundary.letter_grade
                attempt.remark = grade_boundary.remark
        
        db.session.commit()
        
        audit = AuditLog(
            user_id=current_user.id,
            action='SUBMIT_EXAM',
            exam_id=attempt.exam_id,
            details={'attempt_id': attempt.id, 'score': attempt.score},
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Exam submitted successfully!', 'success')
        
        return jsonify({
            'success': True,
            'redirect': url_for('student.dashboard')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/result/<int:attempt_id>')
@login_required  
def view_result(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    student = current_user.student_profile
    
    if attempt.student_id != student.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    exam = attempt.exam
    answers = attempt.answers.all()
    
    return render_template('student/results.html',
                         attempt=attempt,
                         exam=exam,
                         answers=answers)

@student_bp.route('/exam/save_progress', methods=['POST'])
@login_required
def save_progress():
    try:
        data = request.get_json()
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        selected_answer = data.get('selected_answer')
        time_spent = data.get('time_spent', 0)
        
        attempt = ExamAttempt.query.get_or_404(attempt_id)
        
        if attempt.student_id != current_user.student_profile.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if attempt.status != 'in_progress':
            return jsonify({'error': 'Exam already submitted'}), 400
        
        answer = StudentAnswer.query.filter_by(
            attempt_id=attempt_id,
            question_id=question_id
        ).first()
        
        if not answer:
            answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id
            )
            db.session.add(answer)
        
        answer.selected_answer = selected_answer
        answer.time_spent_seconds += time_spent
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/exam/<int:exam_id>/retake', methods=['POST'])
@login_required
def retake_exam(exam_id):
    try:
        student = current_user.student_profile
        exam = Exam.query.get_or_404(exam_id)
        
        if not exam.is_available:
            return jsonify({'error': 'Exam is not available'}), 400
        
        if exam.exam_questions.count() == 0:
            return jsonify({'error': 'This exam has no questions'}), 400
        
        attempts_count = ExamAttempt.query.filter_by(
            exam_id=exam_id,
            student_id=student.id,
            status='submitted'
        ).count()
        
        if attempts_count >= exam.max_attempts:
            return jsonify({'error': f'Maximum attempts ({exam.max_attempts}) reached'}), 400
        
        ExamAttempt.query.filter_by(
            exam_id=exam_id,
            student_id=student.id,
            status='in_progress'
        ).delete()
        
        db.session.commit()
        
        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=student.id,
            attempt_number=attempts_count + 1,
            ip_address=request.remote_addr,
            browser_info=request.headers.get('User-Agent'),
            status='in_progress',
            start_time=datetime.now()
        )
        
        db.session.add(attempt)
        db.session.flush()
        
        exam_questions = exam.exam_questions.order_by(ExamQuestion.question_order).all()
        question_list = list(exam_questions)
        if exam.randomize_questions:
            random.shuffle(question_list)
        
        session[f'exam_{exam.id}_questions'] = [eq.question_id for eq in question_list]
        
        db.session.commit()
        
        audit = AuditLog(
            user_id=current_user.id,
            action='RETAKE_EXAM',
            exam_id=exam_id,
            details={'attempt_id': attempt.id, 'attempt_number': attempt.attempt_number},
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'attempt_id': attempt.id,
            'redirect': url_for('student.continue_exam', attempt_id=attempt.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/log_activity', methods=['POST'])
@login_required
def log_activity():
    try:
        data = request.get_json()
        action = data.get('action')
        exam_id = data.get('exam_id')
        attempt_id = data.get('attempt_id')
        
        audit = AuditLog(
            user_id=current_user.id,
            action=action,
            exam_id=exam_id,
            details={'attempt_id': attempt_id},
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500