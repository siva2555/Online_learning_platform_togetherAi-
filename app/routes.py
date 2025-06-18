import json
import requests
from flask import jsonify
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from .models import (
    User, add_course, get_all_courses, get_course_by_id, add_module,
    ModuleProgress, Module
)
from .ai import generate_quiz
from . import db

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    return render_template("dashboard.html")

@main_bp.route("/progress")
def progress():
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    
    user_id = session.get("user_id")
    courses = get_all_courses()
    progress_data = {}
    for course in courses:
        total_modules = len(course.modules)
        completed_modules = sum(
            1 for module in course.modules 
            if ModuleProgress.query.filter_by(user_id=user_id, module_id=module.id).first()
        )
        progress_percentage = int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
        progress_data[course.id] = progress_percentage
    return render_template("progress.html", courses=courses, progress_data=progress_data)

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(email=email).first():
            error = "Email already exists"
        else:
            new_user = User(
                email=email,
                password=generate_password_hash(password),
                role="user"
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("main.login"))
    return render_template("register.html", error=error)

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["logged_in"] = True
            session["email"] = email
            session["role"] = user.role
            session["user_id"] = user.id  # For progress tracking
            return redirect(url_for("main.dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

@main_bp.route("/courses", methods=["GET", "POST"])
def courses():
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("Only admin users can add courses.")
            return redirect(url_for("main.courses"))
        course_data = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "content": request.form.get("content"),  # Detailed course content
            "image_url": request.form.get("image_url")
        }
        add_course(course_data)
        return redirect(url_for("main.courses"))
    else:
        courses_list = get_all_courses()
        return render_template("courses.html", courses=courses_list)

@main_bp.route("/course/<int:course_id>")
def course_detail(course_id):
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    course = get_course_by_id(course_id)
    if not course:
        return "Course not found", 404
    # Calculate progress for this course
    user_id = session.get("user_id")
    total_modules = len(course.modules)
    completed_modules = sum(
        1 for module in course.modules 
        if ModuleProgress.query.filter_by(user_id=user_id, module_id=module.id).first()
    )
    progress = int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
    return render_template("course_detail.html", course=course, progress=progress)

@main_bp.route("/course/<int:course_id>/module/add", methods=["GET", "POST"])
def add_module_route(course_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Only admin users can add modules.")
        return redirect(url_for("main.login"))
    course = get_course_by_id(course_id)
    if not course:
        return "Course not found", 404
    if request.method == "POST":
        module_data = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "youtube_link": request.form.get("youtube_link")
        }
        add_module(course_id, module_data)
        return redirect(url_for("main.course_detail", course_id=course_id))
    return render_template("add_module.html", course=course)

@main_bp.route("/course/<int:course_id>/module/<int:module_id>/edit", methods=["GET", "POST"])
def edit_module(course_id, module_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Only admin users can edit modules.")
        return redirect(url_for("main.login"))
    course = get_course_by_id(course_id)
    if not course:
        return "Course not found", 404
    module = Module.query.get(module_id)
    if not module:
        return "Module not found", 404
    if request.method == "POST":
        module.title = request.form.get("title")
        module.description = request.form.get("description")
        module.youtube_link = request.form.get("youtube_link")
        db.session.commit()
        flash("Module updated successfully.")
        return redirect(url_for("main.course_detail", course_id=course_id))
    return render_template("edit_module.html", course=course, module=module)

@main_bp.route("/course/<int:course_id>/module/<int:module_id>/delete", methods=["POST"])
def delete_module(course_id, module_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Only admin users can delete modules.")
        return redirect(url_for("main.login"))
    module = Module.query.get(module_id)
    if not module:
        flash("Module not found.")
        return redirect(url_for("main.course_detail", course_id=course_id))
    db.session.delete(module)
    db.session.commit()
    flash("Module deleted successfully.")
    return redirect(url_for("main.course_detail", course_id=course_id))

@main_bp.route("/course/<int:course_id>/module/<int:module_id>/complete", methods=["POST"])
def complete_module(course_id, module_id):
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    user_id = session.get("user_id")
    progress = ModuleProgress.query.filter_by(user_id=user_id, module_id=module_id).first()
    if not progress:
        new_progress = ModuleProgress(user_id=user_id, module_id=module_id)
        db.session.add(new_progress)
        db.session.commit()
        flash("Module marked as completed.")
    else:
        flash("Module already marked as completed.")
    return redirect(url_for("main.course_detail", course_id=course_id))

# Global quiz route (site-wide)
@main_bp.route("/quiz", methods=["GET", "POST"])
def quiz():
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    # GET: Render a prompt form for global quiz generation
    if request.method == "GET":
        return render_template("quiz_prompt.html")
    # POST: Distinguish between prompt submission and quiz answer submission.
    prompt = request.form.get("prompt", "").strip()
    if prompt:
        quiz_data = generate_quiz(prompt)
        print("Raw quiz data:", quiz_data)
        if not quiz_data:
            flash("No quiz data received from the AI.")
            return redirect(url_for("main.dashboard"))
        try:
            quiz_json = json.loads(quiz_data)
        except Exception as e:
            flash(f"Error parsing quiz data: {str(e)}")
            return redirect(url_for("main.dashboard"))
        session["quiz"] = quiz_json
        return render_template("quiz.html", quiz=quiz_json)
    else:
        quiz = session.get("quiz")
        if not quiz:
            flash("Quiz not found. Please try again.")
            return redirect(url_for("main.quiz"))
        user_answers = request.form  # e.g., {"question_0": "A", ...}
        score = 0
        total = len(quiz.get("questions", []))
        results = []
        for i, question in enumerate(quiz.get("questions", [])):
            q_key = f"question_{i}"
            user_answer = user_answers.get(q_key)
            correct_answer = question.get("answer")
            if user_answer == correct_answer:
                score += 1
            results.append({
                "question": question.get("question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "correct": user_answer == correct_answer
            })
        return render_template("quiz_result.html", score=score, total=total, results=results)
@main_bp.route("/resume-builder")
def resume_builder():
    return render_template("resume_builder.html")
@main_bp.route("/course/<int:course_id>/module/<int:module_id>/ai_quiz", methods=["GET", "POST"])
def ai_module_quiz(course_id, module_id):
    if not session.get("logged_in"):
        return redirect(url_for("main.login"))
    module = Module.query.get(module_id)
    course = get_course_by_id(course_id)
    if not module or not course:
        flash("Module or course not found.")
        return redirect(url_for("main.course_detail", course_id=course_id))
    if request.method == "GET":
        ai_prompt = (
            f"Generate a multiple-choice quiz in JSON format about the module titled '{module.title}'. "
            f"Module description: {module.description}. "
            "The JSON should have a key 'questions' containing 3 questions. "
            "Each question must be an object with keys 'question', 'options' (a list of 4 options), "
            "and 'answer' (the letter corresponding to the correct option, e.g., 'A'). "
            "Return only the JSON and nothing else."
        )
        quiz_data = generate_quiz(ai_prompt)
        print("Raw module quiz data:", quiz_data)
        if not quiz_data:
            flash("No quiz data received from the AI.")
            return redirect(url_for("main.course_detail", course_id=course_id))
        try:
            quiz_json = json.loads(quiz_data)
        except Exception as e:
            flash(f"Error parsing quiz data: {str(e)}")
            return redirect(url_for("main.course_detail", course_id=course_id))
        session["module_quiz"] = quiz_json
        return render_template("module_quiz.html", course=course, module=module, quiz=quiz_json)
    else:
        quiz = session.get("module_quiz")
        if not quiz:
            flash("Quiz not found. Please try again.")
            return redirect(url_for("main.ai_module_quiz", course_id=course_id, module_id=module_id))
        user_answers = request.form
        score = 0
        total = len(quiz.get("questions", []))
        results = []
        for i, question in enumerate(quiz.get("questions", [])):
            q_key = f"question_{i}"
            user_answer = user_answers.get(q_key)
            correct_answer = question.get("answer")
            if user_answer == correct_answer:
                score += 1
            results.append({
                "question": question.get("question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "correct": user_answer == correct_answer
            })
        return render_template("module_quiz_result.html", score=score, total=total, results=results, course=course, module=module)

# Route for admin-created module quiz (admin creates a quiz manually)
@main_bp.route("/course/<int:course_id>/module/<int:module_id>/admin_quiz", methods=["GET", "POST"])
def admin_module_quiz(course_id, module_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Only admin users can access the admin quiz feature.")
        return redirect(url_for("main.login"))
    course = get_course_by_id(course_id)
    module = Module.query.get(module_id)
    if not course or not module:
        flash("Module or course not found.")
        return redirect(url_for("main.course_detail", course_id=course_id))
    if request.method == "GET":
        # Render a form for admin to create a quiz manually (or via prompt)
        return render_template("admin_quiz_prompt.html", course=course, module=module)
    else:
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            flash("Please enter a prompt for the quiz.")
            return redirect(url_for("main.admin_module_quiz", course_id=course_id, module_id=module_id))
        quiz_data = generate_quiz(prompt)
        print("Raw admin quiz data:", quiz_data)
        if not quiz_data:
            flash("No quiz data received from the AI.")
            return redirect(url_for("main.course_detail", course_id=course_id))
        try:
            quiz_json = json.loads(quiz_data)
        except Exception as e:
            flash(f"Error parsing quiz data: {str(e)}")
            return redirect(url_for("main.course_detail", course_id=course_id))
        session["module_quiz"] = quiz_json
        flash("Admin quiz created successfully!")
        return redirect(url_for("main.attempt_module_quiz", course_id=course_id, module_id=module_id))
@main_bp.route("/course/<int:course_id>/module/<int:module_id>/attempt", methods=["GET", "POST"])
def attempt_module_quiz(course_id, module_id):
    return redirect(url_for("main.ai_module_quiz", course_id=course_id, module_id=module_id))
