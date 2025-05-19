import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Base configuration for database
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    # Specific upload folders for different types of content
    UPLOAD_FOLDER_AVATARS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'avatars')
    UPLOAD_FOLDER_BLOCKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'blocks')
    UPLOAD_FOLDER_LECTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'lectures')
    UPLOAD_FOLDER_SECTIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'sections')
    UPLOAD_FOLDER_CONTACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'contacts')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size

    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.mail.ru')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'MAIL_DEFAULT_SENDER')
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False
    PREFERRED_URL_SCHEME = 'https'
    # Site configuration
    SITE_NAME = 'Биолекторий МГУ'
    BASE_URL = os.environ.get('BASE_URL')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True

    # Определение URL базы данных для среды разработки
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    # Определение URL базы данных для продакшн-среды
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,

}
