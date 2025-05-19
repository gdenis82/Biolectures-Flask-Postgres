from flask import current_app, render_template
from flask_mail import Message
from app import mail
import secrets
from datetime import datetime, timedelta

def get_start_date():
    """Генерирует ближайшую дату начала с учетом буднего дня, через неделю от текущей даты."""
    start_date = datetime.now() + timedelta(days=7)
    # Если день недели суббота (5) или воскресенье (6), сдвигаем дату на ближайший понедельник
    if start_date.weekday() == 5:  # Суббота
        start_date += timedelta(days=2)
    elif start_date.weekday() == 6:  # Воскресенье
        start_date += timedelta(days=1)
    return start_date.strftime("%Y-%m-%d")


def generate_token():
    """Generate a secure token for email confirmation or password reset"""
    return secrets.token_urlsafe(32)

def send_email(subject, recipients, html_body, text_body=None):
    """
    Send an email with the given subject and body to the specified recipients.

    Args:
        subject (str): The subject of the email
        recipients (list): List of recipient email addresses
        html_body (str): HTML content of the email
        text_body (str, optional): Plain text content of the email. Defaults to None.
    """
    msg = Message(
        subject=subject,
        recipients=recipients,
        html=html_body,
        body=text_body or html_body.replace('<br>', '\n').replace('</p>', '\n').replace('<p>', '')
    )
    mail.send(msg)

def send_confirmation_email(user):
    """
    Send a confirmation email to a newly registered user.

    Args:
        user: The user object to send the confirmation email to
    """
    # Generate confirmation token and set expiration (24 hours from now)
    token = generate_token()
    user.confirmation_token = token
    user.confirmation_token_expires = datetime.utcnow() + timedelta(hours=24)

    # Create confirmation URL
    confirmation_url = f"{current_app.config['BASE_URL']}/auth/confirm/{token}"

    # Render email template
    html = render_template('email/confirm_email.html', 
                          user=user, 
                          confirmation_url=confirmation_url,
                          site_name=current_app.config['SITE_NAME'])

    # Send email
    send_email(
        subject=f"Подтверждение регистрации - {current_app.config['SITE_NAME']}",
        recipients=[user.email],
        html_body=html
    )

def send_password_reset_email(user):
    """
    Send a password reset email to a user.

    Args:
        user: The user object to send the password reset email to
    """
    # Generate reset token and set expiration (24 hours from now)
    token = generate_token()
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)

    # Create reset URL
    reset_url = f"{current_app.config['BASE_URL']}/auth/reset_password/{token}"

    # Render email template
    html = render_template('email/reset_password.html', 
                          user=user, 
                          reset_url=reset_url,
                          site_name=current_app.config['SITE_NAME'])

    # Send email
    send_email(
        subject=f"Сброс пароля - {current_app.config['SITE_NAME']}",
        recipients=[user.email],
        html_body=html
    )

def send_order_confirmation_email(order, user=None, is_new_user=False):
    """
    Send an order confirmation email to a user.

    Args:
        order: The order object to send confirmation for
        user: The user object (optional, for registered users)
        is_new_user: Boolean indicating if this is a new user registration
    """
    # Generate confirmation token and set expiration (24 hours from now)
    token = generate_token()
    order.confirmation_token = token
    order.confirmation_token_expires = datetime.utcnow() + timedelta(hours=24)

    admin_email = current_app.config.get('ADMIN_EMAIL', 'biolectures@mail.ru')

    # Create confirmation URL
    confirmation_url = f"{current_app.config['BASE_URL']}/order/confirm/{token}"

    # Determine template based on user status
    template = 'email/order_confirmation_new_user.html' if is_new_user else 'email/order_confirmation.html'

    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    current_year = datetime.now().year

    order_url = f"{current_app.config['BASE_URL']}/admin/orderform/edit/?{order.id}&url=/admin/orderform/"
    # Render admin notification email
    admin_html = render_template('email/order_form_admin.html',
                                 order=order,
                                 user=user,
                                 site_name=current_app.config['SITE_NAME'],
                                 order_url=order_url,
                                 current_year=current_year)

    # Render email template
    html = render_template(template, 
                          order=order,
                          user=user,
                          confirmation_url=confirmation_url,
                          site_name=current_app.config['SITE_NAME'])

    # Send email
    send_email(
        subject=f"Подтверждение заказа лекции - {current_app.config['SITE_NAME']}",
        recipients=[order.email],
        html_body=html
    )

    # Send email to admin
    send_email(
        subject=f"Новое сообщение с сайта - {current_app.config['SITE_NAME']}",
        recipients=[admin_email],
        html_body=admin_html
    )

def send_contact_form_emails(form_data):
    """
    Send emails for contact form submission.

    Args:
        form_data: Dictionary containing form data (name, email, phone, organization, message)
    """
    # Get current timestamp
    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    current_year = datetime.now().year

    # Get admin email from config
    admin_email = current_app.config.get('ADMIN_EMAIL', 'biolectures@mail.ru')

    # Render user confirmation email
    user_html = render_template('email/contact_form_confirmation.html',
                               name=form_data.get('name', ''),
                               email=form_data.get('email', ''),
                               phone=form_data.get('phone', ''),
                               organization=form_data.get('organization', ''),
                               message=form_data.get('message', ''),
                               site_name=current_app.config['SITE_NAME'],
                               current_year=current_year)

    # Render admin notification email
    admin_html = render_template('email/contact_form_admin_notification.html',
                                timestamp=timestamp,
                                name=form_data.get('name', ''),
                                email=form_data.get('email', ''),
                                phone=form_data.get('phone', ''),
                                organization=form_data.get('organization', ''),
                                message=form_data.get('message', ''),
                                site_name=current_app.config['SITE_NAME'],
                                current_year=current_year)

    # Send email to user
    send_email(
        subject=f"Спасибо за ваше сообщение - {current_app.config['SITE_NAME']}",
        recipients=[form_data.get('email')],
        html_body=user_html
    )

    # Send email to admin
    send_email(
        subject=f"Новое сообщение с сайта - {current_app.config['SITE_NAME']}",
        recipients=[admin_email],
        html_body=admin_html
    )
