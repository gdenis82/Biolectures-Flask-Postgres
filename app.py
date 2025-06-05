import os
import re
import spacy
from langdetect import detect
import traceback
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config


# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()


# Загружаем spaCy модели один раз
nlp_ru = spacy.load("ru_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

# Function to initialize roles
def init_roles():
    from models import Role
    """Initialize standard roles if they don't exist"""
    # Start with a clean session state
    db.session.rollback()

    # Ensure role data is properly encoded
    roles = {
        'admin': 'Administrator with full access',
        'editor': 'Editor with content management access',
        'user': 'Regular user with limited access',
        'lecturer': 'Lecturer who conducts lectures'
    }

    # Process each role in a separate transaction
    for role_name, description in roles.items():
        try:
            # Ensure role name and description are properly encoded
            safe_role_name = role_name.encode('ascii', 'ignore').decode('ascii')
            safe_description = description.encode('ascii', 'ignore').decode('ascii')

            print(f"Processing role: {safe_role_name}")

            # Start a fresh transaction for each role
            db.session.begin_nested()

            try:
                # Try to query for the role by name
                role = None
                try:
                    role = Role.query.filter_by(name=safe_role_name).first()
                except UnicodeDecodeError as e:
                    print(f"UnicodeDecodeError during query for role {safe_role_name}: {str(e)}")
                    # Continue with role creation

                if role is None:
                    # Role doesn't exist, create it
                    role = Role(name=safe_role_name, description=safe_description)
                    db.session.add(role)
                    db.session.commit()
                    print(f"Created role: {safe_role_name}")
                else:
                    print(f"Role already exists: {safe_role_name}")
                    db.session.commit()
            except UnicodeDecodeError as e:
                # Handle specific encoding errors
                print(f"UnicodeDecodeError processing role {safe_role_name}: {str(e)}")
                db.session.rollback()

                # Try direct creation without querying
                try:
                    # Create a new transaction
                    db.session.begin_nested()

                    # Create the role directly
                    role = Role(name=safe_role_name, description=safe_description)
                    db.session.add(role)
                    db.session.commit()
                    print(f"Created role directly: {safe_role_name}")
                except Exception as inner_e:
                    print(f"Failed to create role {safe_role_name}: {str(inner_e)}")
                    db.session.rollback()
            except Exception as e:
                print(f"Error processing role {safe_role_name}: {str(e)}")
                db.session.rollback()
        except Exception as e:
            print(f"Transaction error for role {role_name}: {str(e)}")
            db.session.rollback()

    # Final rollback to ensure clean state
    db.session.rollback()

def init_auth_menu_items():
    """Initialize authentication menu items if they don't exist"""
    from models.models import MenuItem

    try:
        # Remove login and register menu items if they exist
        # since they are now hardcoded in the template
        login_item = MenuItem.query.filter_by(name='Вход').first()
        if login_item:
            db.session.delete(login_item)
            print("Removed login menu item")

        register_item = MenuItem.query.filter_by(name='Регистрация').first()
        if register_item:
            db.session.delete(register_item)
            print("Removed register menu item")

        # Commit changes
        db.session.commit()
        print("Authentication menu items initialized successfully")
    except Exception as e:
        print(f"Error initializing authentication menu items: {str(e)}")
        db.session.rollback()

def create_app(config_name=None):
    """Application factory function"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Ensure the upload folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_AVATARS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_BLOCKS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_LECTURES'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_SECTIONS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_CONTACTS'], exist_ok=True)

    # Initialize database and roles
    try:
        with app.app_context():
            db.create_all()
            init_roles()
            init_auth_menu_items()

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        # Continue with application startup even if initialization fails
        traceback.print_exc()

    # Register blueprints
    from auth.views import auth_bp
    app.register_blueprint(auth_bp)

    from views.main import user_bp
    app.register_blueprint(user_bp)

    from admin.views import admin_bp
    app.register_blueprint(admin_bp)

    # Setup admin
    from admin.views import init_admin
    init_admin(app)

    from textgen.plugin import textgen_bp
    app.register_blueprint(textgen_bp)


    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    @app.context_processor
    def inject_menu_items():
        """Inject menu items into all templates"""
        try:
            # Get all active menu items
            from models.models import MenuItem
            menu_items = MenuItem.query.filter_by(is_active=True, parent_id=None).order_by(MenuItem.order).all()

            # Filter admin menu items if user is not admin, editor, or lecturer with admin access
            from flask import session
            if 'is_admin' not in session and 'is_editor' not in session:
                # Check if user is a lecturer with admin access
                from models.models import User
                show_admin = False
                if 'user_id' in session and 'is_lecturer' in session:
                    user = User.query.get(session['user_id'])
                    if user and user.can_access_admin:
                        show_admin = True

                if not show_admin:
                    menu_items = [item for item in menu_items if item.name != 'Админ панель']

            return {'menu_items': menu_items}
        except Exception as e:
            print(f"Error injecting menu items: {str(e)}")
            return {'menu_items': []}

    @app.template_filter('commas')
    def replace_spaces_with_commas(text):
        if not text:
            return ''

        # Автоопределение языка
        try:
            lang = detect(text)
        except:
            lang = 'ru'  # fallback по умолчанию

        # Выбор модели
        nlp = nlp_ru if lang == 'ru' else nlp_en
        doc = nlp(text)

        # Части речи, которые нужно исключить
        excluded_pos = {
            'ADP',  # предлоги
            'CCONJ',  # сочинительные союзы
            'SCONJ',  # подчинительные союзы
            'PRON',  # местоимения
            'PART',  # частицы (типа бы, же, ли)
            'DET',  # определители (this, that, etc.)
            'INTJ'  # междометия
        }

        # Фильтруем токены
        words = [token.text for token in doc if token.pos_ not in excluded_pos and token.is_alpha]

        return ', '.join(words)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
