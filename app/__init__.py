# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")  # Loads the Config class from config.py

    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()
        models.create_default_admin(app.config)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
