from werkzeug.security import generate_password_hash, check_password_hash
from . import db

# User model now uses email as the unique identifier.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    # Optionally, you could add a relationship to progress:
    module_progress = db.relationship('ModuleProgress', backref='user', lazy=True)

def create_default_admin(config):
    # Directly use config keys. Make sure your config.py has DEFAULT_ADMIN_EMAIL.
    email = config["DEFAULT_ADMIN_EMAIL"]
    password = config["DEFAULT_ADMIN_PASSWORD"]
    if not User.query.filter_by(email=email).first():
        admin = User(
            email=email,
            password=generate_password_hash(password),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()

# Course model now includes an extra 'content' field.
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=True)   # Additional course content (e.g. syllabus)
    image_url = db.Column(db.String(250), nullable=True)  # URL for course image
    # Relationship to modules
    modules = db.relationship('Module', backref='course', lazy=True)

# Module model (each module can have its own YouTube link)
class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    youtube_link = db.Column(db.String(250), nullable=True)  # Module video link
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    # Relationship to track progress for this module
    progress = db.relationship('ModuleProgress', backref='module', lazy=True)

def add_course(course_data):
    course = Course(
        title=course_data["title"],
        description=course_data["description"],
        content=course_data.get("content"),
        image_url=course_data.get("image_url")
    )
    db.session.add(course)
    db.session.commit()

def get_all_courses():
    return Course.query.all()

def get_course_by_id(course_id):
    return Course.query.get(course_id)

def add_module(course_id, module_data):
    module = Module(
        title=module_data["title"],
        description=module_data["description"],
        youtube_link=module_data.get("youtube_link"),
        course_id=course_id
    )
    db.session.add(module)
    db.session.commit()

# New model: ModuleProgress.
# This table tracks which modules have been completed by which users.
class ModuleProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    # Optionally, add a timestamp field or completed flag if needed.
