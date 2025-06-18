# config.py
import os

class Config:
    SECRET_KEY = "your_secret_key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.getcwd(), "learning_platform.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_ADMIN_EMAIL = "admin@example.com"  
    DEFAULT_ADMIN_PASSWORD = "admin123"
    GEN_AI_API_KEY = "aa63a8029651d71488538435a7471144d8128f8c0383b423443fdffd1172fc57"
