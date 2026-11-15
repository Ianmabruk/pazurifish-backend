import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///pazurifish.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'development-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'development-jwt-secret')
    JSON_SORT_KEYS = False
