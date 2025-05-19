from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from datetime import datetime, timedelta

from app import db
from models.models import User, Role
from utils import send_confirmation_email, send_password_reset_email, generate_token

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Form classes
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 120)])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. Please register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

# Decorator for requiring login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for requiring admin role
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = User.query.get(session['user_id'])
        if not user or not user.has_role('admin'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function

# Decorator for requiring admin or editor role
def admin_or_editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = User.query.get(session['user_id'])
        if not user or (not user.has_role('admin') and not user.has_role('editor') and not (user.has_role('lecturer') and user.can_access_admin)):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function

# Decorator for requiring lecturer role
def lecturer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = User.query.get(session['user_id'])
        if not user or not user.has_role('lecturer'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function

# Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data):
            flash('Неверное имя пользователя или пароль', 'danger')
            return redirect(url_for('auth.login'))

        # Check if user's email is confirmed
        if not user.email_confirmed:
            flash('Ваш email не подтвержден. Пожалуйста, проверьте вашу почту и следуйте инструкциям для подтверждения.', 'warning')
            # Resend confirmation email
            try:
                send_confirmation_email(user)
                db.session.commit()
                flash('Новое письмо с подтверждением было отправлено на ваш email.', 'info')
            except Exception as e:
                print(f"Error resending confirmation email: {str(e)}")
            return redirect(url_for('auth.login'))

        # Check if user account is active
        if not user.is_active:
            flash('Ваш аккаунт неактивен. Пожалуйста, свяжитесь с администратором.', 'warning')
            return redirect(url_for('auth.login'))

        session['user_id'] = user.id
        session['username'] = user.username
        session['email'] = user.email

        # Check if user has admin, editor, or lecturer role
        if user.has_role('admin'):
            session['is_admin'] = True
        elif user.has_role('editor'):
            session['is_editor'] = True
        elif user.has_role('lecturer'):
            session['is_lecturer'] = True
            # Check if lecturer has admin panel access
            if user.can_access_admin:
                session['is_editor'] = True  # Give lecturer editor-level access

        flash(f'Добро пожаловать, {user.username}!', 'success')
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('email', None)
    session.pop('is_admin', None)
    session.pop('is_editor', None)
    session.pop('is_lecturer', None)
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_active=False,  # User is inactive until email is confirmed
            email_confirmed=False  # Email is not confirmed yet
        )
        user.password = form.password.data

        # Add default user role
        user_role = Role.query.filter_by(name='user').first()
        if user_role:
            user.roles.append(user_role)

        db.session.add(user)
        db.session.commit()

        # Send confirmation email
        try:
            send_confirmation_email(user)
            db.session.commit()  # Save the confirmation token
            flash('Регистрация успешна! На ваш email отправлено письмо с инструкциями по активации аккаунта.', 'success')
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
            flash('Регистрация успешна, но возникла проблема при отправке письма с подтверждением. Пожалуйста, свяжитесь с администратором.', 'warning')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

def generate_reset_token():
    """Generate a secure token for password reset"""
    return secrets.token_urlsafe(32)

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if 'user_id' in session:
        return redirect(url_for('main.index'))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        try:
            # Send password reset email
            send_password_reset_email(user)
            db.session.commit()
            flash('Ссылка для сброса пароля отправлена на ваш email.', 'success')
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            flash('Произошла ошибка при отправке письма для сброса пароля. Пожалуйста, попробуйте позже.', 'danger')

        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if 'user_id' in session:
        return redirect(url_for('main.index'))

    # Find user with this token
    user = User.query.filter_by(reset_token=token).first()

    # Check if token is valid and not expired
    if user is None or (user.reset_token_expires and user.reset_token_expires < datetime.utcnow()):
        flash('Ссылка для сброса пароля недействительна или устарела.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = form.password.data
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()

        flash('Ваш пароль успешно сброшен.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    """Confirm user email with token"""
    # Find user with this token
    user = User.query.filter_by(confirmation_token=token).first()

    # Check if token is valid and not expired
    if user is None or (user.confirmation_token_expires and user.confirmation_token_expires < datetime.utcnow()):
        flash('Ссылка для подтверждения недействительна или устарела.', 'danger')
        return redirect(url_for('auth.login'))

    # Activate user account
    user.is_active = True
    user.email_confirmed = True
    user.confirmation_token = None
    user.confirmation_token_expires = None
    db.session.commit()

    flash('Ваш email успешно подтвержден! Теперь вы можете войти в систему.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/help')
def help():
    """Display help page with authentication instructions"""
    return render_template('auth/help.html')
