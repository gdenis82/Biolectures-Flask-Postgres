from xml.sax.saxutils import escape

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, jsonify, Response
from sqlalchemy import func

from models.models import Section, Lecture, Contact, OrderForm, MenuItem, HomeBlock, User, Role, SeoSettings
from app import db
from auth.views import login_required
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

from utils import get_start_date

# Create main blueprint
user_bp = Blueprint('main', __name__)

@user_bp.route('/')
@user_bp.route('/index')
@user_bp.route('/index.html')
def index():
    """Homepage view"""
    # Get active home blocks ordered by position
    blocks = []

    try:
        # Try to get home blocks with error handling
        blocks = HomeBlock.query.filter_by(is_active=True).order_by(HomeBlock.order).all()
    except UnicodeDecodeError as e:
        # Log the error and continue with empty blocks
        print(f"UnicodeDecodeError when querying HomeBlock: {str(e)}")
        # Return a basic page if blocks can't be loaded
        return render_template('index.html', blocks=[])
    except Exception as e:
        print(f"Error querying HomeBlock: {str(e)}")
        # Return a basic page if blocks can't be loaded
        return render_template('index.html', blocks=[])

    return render_template('index.html', blocks=blocks)

@user_bp.route('/sections')
def sections():
    """View all sections"""
    sections_list = []

    try:
        sections_list = Section.query.filter_by(is_active=True).order_by(Section.order).all()
    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError when querying Section: {str(e)}")
    except Exception as e:
        print(f"Error querying Section: {str(e)}")

    return render_template('sections.html', sections=sections_list)



@user_bp.route('/section/<slug>')
def section_detail(slug):
    """View lectures in a section"""
    section = None
    lectures = []

    try:
        # Safely encode the slug
        safe_slug = slug.encode('ascii', 'ignore').decode('ascii')
        section = Section.query.filter(
            func.lower(Section.slug) == safe_slug.lower(),
            Section.is_active == True
        ).first_or_404()

        try:
            lectures = Lecture.query.filter_by(section_id=section.id, is_active=True).all()
        except UnicodeDecodeError as e:
            print(f"UnicodeDecodeError when querying Lecture: {str(e)}")
        except Exception as e:
            print(f"Error querying Lecture: {str(e)}")

    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError when querying Section with slug '{slug}': {str(e)}")
        return render_template('404.html'), 404
    except Exception as e:
        print(f"Error querying Section with slug '{slug}': {str(e)}")
        return render_template('404.html'), 404

    return render_template('section_detail.html', section=section, lectures=lectures)

@user_bp.route('/lectures_section/<slug>')
def load_lectures_section(slug):
    """API возвращает раздел и связанные с ним лекции с поддержкой пагинации"""
    try:
        # Получение параметров пагинации
        page = int(request.args.get('page', 1))  # Номер страницы, по умолчанию 1
        limit = int(request.args.get('limit', 5))  # Лимит лекций на одной странице, по умолчанию 5
        offset = (page - 1) * limit  # Смещение в выборке

        # Найти раздел по slug
        section = Section.query.filter(
            func.lower(Section.slug) == slug.lower(),
            Section.is_active == True
        ).first_or_404()

        # Найти все активные лекции, связанные с этим разделом
        lectures_query = Lecture.query.filter_by(section_id=section.id, is_active=True).order_by(Lecture.order)

        # Применить лимит и смещение для пагинации
        total_lectures = lectures_query.count()  # Общее количество лекций
        lectures = lectures_query.offset(offset).limit(limit).all()

        # Если лекции закончились, вернуть пустой список, чтобы скрыть кнопку "Загрузить ещё"
        if not lectures:
            return jsonify({
                'section': {
                    'id': section.id,
                    'title': section.name,
                    'description': section.description,
                    'image': section.image
                },
                'lectures': []
            })

        # Отправить данные в формате JSON
        return jsonify({
            'section': {
                'id': section.id,
                'title': section.name,
                'description': section.description,
                'image': section.image
            },
            'lectures': [
                {
                    'id': lecture.id,
                    'title': lecture.title,
                    'subtitle': lecture.subtitle,
                    'description': lecture.description,
                    'content': lecture.content,
                    'image': lecture.image,
                    'slug': lecture.slug,
                    'order': lecture.order,
                }
                for lecture in lectures
            ],
            'pagination': {
                'total': total_lectures,  # Общее количество лекций
                'page': page,  # Текущая страница
                'limit': limit,  # Лимит на загрузку
                'has_more': offset + limit < total_lectures  # Есть ли ещё лекции
            }
        })

    except Exception as e:
        print(f"Error loading section or lectures: {str(e)}")
        return jsonify({
            "error": "Произошла ошибка. Раздел или лекции не найдены."
        }), 404


@user_bp.route('/lecture/<slug>')
def lecture_detail(slug):
    """View a specific lecture"""
    lecture = None

    try:
        # Safely encode the slug
        safe_slug = slug.encode('ascii', 'ignore').decode('ascii')
        lecture = Lecture.query.filter(
            func.lower(Lecture.slug) == safe_slug.lower(),
            Lecture.is_active == True
        ).first_or_404()


    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError when querying Lecture with slug '{slug}': {str(e)}")
        return render_template('404.html'), 404
    except Exception as e:
        print(f"Error querying Lecture with slug '{slug}': {str(e)}")
        return render_template('404.html'), 404

    return render_template('lecture_detail.html', lecture=lecture)

@user_bp.route('/contacts')
def contacts():
    """View contact information"""
    contacts_list = []

    try:
        contacts_list = Contact.query.filter_by(is_active=True).order_by(Contact.order).all()
    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError when querying Contact: {str(e)}")
    except Exception as e:
        print(f"Error querying Contact: {str(e)}")

    return render_template('contacts.html', contacts=contacts_list)

@user_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = User.query.get_or_404(session['user_id'])

    # Get orders placed by the user
    user_orders = OrderForm.query.filter_by(user_id=user.id).order_by(OrderForm.created_at.desc()).all()

    # Get date filter parameters
    date_filter = request.args.get('date_filter', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    specific_date = request.args.get('specific_date')

    # Initialize variables
    assigned_orders = []

    # Check if user is a lecturer
    is_lecturer = user.has_role('lecturer')

    if is_lecturer:
        # Get orders assigned to the lecturer
        assigned_orders_query = OrderForm.query.filter_by(lecturer_id=user.id)

        # Apply date filters if provided
        if date_filter == 'range' and start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Filter orders by date
                assigned_orders_query = assigned_orders_query.filter(OrderForm.created_at >= start_date_obj,
                                                                   OrderForm.created_at <= end_date_obj)
            except ValueError:
                flash('Неверный формат даты', 'danger')

        elif date_filter == 'specific' and specific_date:
            try:
                specific_date_obj = datetime.strptime(specific_date, '%Y-%m-%d').date()

                # Filter orders by date (using date part of created_at)
                from sqlalchemy import func
                assigned_orders_query = assigned_orders_query.filter(
                    func.date(OrderForm.created_at) == specific_date_obj
                )
            except ValueError:
                flash('Неверный формат даты', 'danger')

        # Get the filtered orders
        assigned_orders = assigned_orders_query.order_by(OrderForm.created_at.desc()).all()

    return render_template('profile.html', user=user, orders=user_orders, 
                          assigned_orders=assigned_orders, is_lecturer=is_lecturer,
                          date_filter=date_filter, start_date=start_date, 
                          end_date=end_date, specific_date=specific_date)

@user_bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Upload user avatar"""
    user = User.query.get_or_404(session['user_id'])

    if 'avatar' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.profile'))

    file = request.files['avatar']

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.profile'))

    if file:
        # Generate a unique filename to prevent overwriting
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"

        # Save the file to avatars directory
        uploads_dir = os.path.join(current_app.config['UPLOAD_FOLDER_AVATARS'])
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        file_path = os.path.join(uploads_dir, unique_filename)
        file.save(file_path)

        # Update user avatar in database
        user.avatar = unique_filename
        db.session.commit()

        flash('Avatar uploaded successfully', 'success')

    return redirect(url_for('main.profile'))

@user_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    user = User.query.get_or_404(session['user_id'])

    try:
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        # Validate username and email
        if not username:
            flash('Имя пользователя обязательно', 'danger')
            return redirect(url_for('main.profile'))

        if not email:
            flash('Email обязателен', 'danger')
            return redirect(url_for('main.profile'))

        # Check if username is already taken by another user
        existing_user = User.query.filter(User.username == username, User.id != user.id).first()
        if existing_user:
            flash('Это имя пользователя уже занято', 'danger')
            return redirect(url_for('main.profile'))

        # Check if email is already taken by another user
        existing_email = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_email:
            flash('Этот email уже используется', 'danger')
            return redirect(url_for('main.profile'))

        # Update user information
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        db.session.commit()
        flash('Профиль успешно обновлен', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {str(e)}")
        flash('Произошла ошибка при обновлении профиля', 'danger')

    return redirect(url_for('main.profile'))

@user_bp.route('/order/confirm/<token>')
def confirm_order(token):
    """Confirm order with token"""
    # Find order with this token
    order = OrderForm.query.filter_by(confirmation_token=token).first()

    # Check if token is valid and not expired
    if order is None or (order.confirmation_token_expires and order.confirmation_token_expires < datetime.utcnow()):
        flash('Ссылка для подтверждения заказа недействительна или устарела.', 'danger')
        return redirect(url_for('main.index'))

    # Get user associated with the order
    user = User.query.get(order.user_id) if order.user_id else None

    # If user exists and is not confirmed, confirm the user
    if user and not user.email_confirmed:
        user.is_active = True
        user.email_confirmed = True
        user.confirmation_token = None
        user.confirmation_token_expires = None

    # Confirm order
    order.is_confirmed = True
    order.status = 'confirmed'
    order.confirmation_token = None
    order.confirmation_token_expires = None

    db.session.commit()

    flash('Ваш заказ успешно подтвержден! Наш менеджер свяжется с вами в ближайшее время.', 'success')

    # If user is authenticated, redirect to profile
    if 'user_id' in session:
        return redirect(url_for('main.profile'))

    # Otherwise, redirect to login page
    return redirect(url_for('auth.login'))

@user_bp.route('/contact-form', methods=['POST'])
def contact_form():
    """Handle contact form submission"""
    from utils import send_contact_form_emails

    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            organization = request.form.get('organization', '').strip()
            message = request.form.get('message', '').strip()

            # Get CAPTCHA data
            captcha_num1 = request.form.get('captchaNum1', '')
            captcha_num2 = request.form.get('captchaNum2', '')
            captcha_answer = request.form.get('captchaAnswer', '')

            # Validate required fields
            if not name:
                flash('Пожалуйста, укажите ваше имя', 'danger')
                return redirect(url_for('main.index', _anchor='contact-form'))

            if not email:
                flash('Пожалуйста, укажите ваш email', 'danger')
                return redirect(url_for('main.index', _anchor='contact-form'))

            # Validate CAPTCHA
            try:
                num1 = int(captcha_num1)
                num2 = int(captcha_num2)
                answer = int(captcha_answer)

                if answer != (num1 + num2):
                    flash('Неверный ответ на проверку безопасности', 'danger')
                    return redirect(url_for('main.index', _anchor='contact-form'))
            except (ValueError, TypeError):
                flash('Ошибка проверки безопасности', 'danger')
                return redirect(url_for('main.index', _anchor='contact-form'))

            # Prepare form data for email
            form_data = {
                'name': name,
                'email': email,
                'phone': phone,
                'organization': organization,
                'message': message
            }

            # Send emails
            try:
                send_contact_form_emails(form_data)
                flash('Спасибо за ваше сообщение! Мы свяжемся с вами в ближайшее время.', 'success')
            except Exception as e:
                print(f"Error sending contact form emails: {str(e)}")
                flash('Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте еще раз позже.', 'danger')

            return redirect(url_for('main.index'))

        except Exception as e:
            print(f"Error processing contact form: {str(e)}")
            flash('Произошла ошибка при обработке формы. Пожалуйста, попробуйте еще раз.', 'danger')
            return redirect(url_for('main.index', _anchor='contact-form'))

    # If not POST, redirect to home page
    return redirect(url_for('main.index'))

@user_bp.route('/order/<int:lecture_id>', methods=['GET', 'POST'])
def order_lecture(lecture_id):
    """Order a lecture form"""
    from utils import send_order_confirmation_email, send_confirmation_email, generate_token
    from werkzeug.security import generate_password_hash
    import random
    import string

    lecture = None
    is_authenticated = 'user_id' in session

    try:
        lecture = Lecture.query.get_or_404(lecture_id)

        if request.method == 'POST':
            try:
                # Process the form submission
                # Safely encode form data
                name = request.form.get('name', '')
                email = request.form.get('email', '')
                phone = request.form.get('phone', '')
                organization = request.form.get('organization', '')
                message = request.form.get('message', '')

                # Check if user is authenticated
                if is_authenticated:
                    # Get current user
                    user = User.query.get(session['user_id'])

                    # Create order
                    order = OrderForm(
                        name=name,
                        email=email,
                        phone=phone,
                        organization=organization,
                        message=message,
                        lecture_id=lecture.id,
                        user_id=user.id,
                        status='pending',
                        is_confirmed=False
                    )

                    db.session.add(order)
                    db.session.commit()

                    # Send order confirmation email
                    try:
                        send_order_confirmation_email(order, user)
                        db.session.commit()
                        flash('Заказ успешно создан! На ваш email отправлено письмо с подтверждением.', 'success')
                    except Exception as e:
                        print(f"Error sending order confirmation email: {str(e)}")
                        flash('Заказ создан, но возникла проблема при отправке письма с подтверждением.', 'warning')

                else:
                    # Check if user with this email already exists
                    existing_user = User.query.filter_by(email=email).first()

                    if existing_user:
                        # Create order for existing user
                        order = OrderForm(
                            name=name,
                            email=email,
                            phone=phone,
                            organization=organization,
                            message=message,
                            lecture_id=lecture.id,
                            user_id=existing_user.id,
                            status='pending',
                            is_confirmed=False
                        )

                        db.session.add(order)
                        db.session.commit()

                        # Send order confirmation email
                        try:
                            send_order_confirmation_email(order, existing_user)
                            db.session.commit()
                            flash('Заказ успешно создан! На ваш email отправлено письмо с подтверждением.', 'success')
                        except Exception as e:
                            print(f"Error sending order confirmation email: {str(e)}")
                            flash('Заказ создан, но возникла проблема при отправке письма с подтверждением.', 'warning')

                    else:
                        # Create new user
                        # Generate username from email
                        username = email.split('@')[0]
                        # Check if username exists
                        if User.query.filter_by(username=username).first():
                            # Add random suffix
                            username = f"{username}{random.randint(100, 999)}"

                        # Create user
                        new_user = User(
                            username=username,
                            email=email,
                            first_name=name.split(' ')[0] if ' ' in name else name,
                            last_name=' '.join(name.split(' ')[1:]) if ' ' in name else '',
                            is_active=False,
                            email_confirmed=False
                        )

                        # Generate random password (user will reset it later)
                        random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        new_user.password = random_password

                        # Add default user role
                        user_role = Role.query.filter_by(name='user').first()
                        if user_role:
                            new_user.roles.append(user_role)

                        db.session.add(new_user)
                        db.session.commit()

                        # Create order for new user
                        order = OrderForm(
                            name=name,
                            email=email,
                            phone=phone,
                            organization=organization,
                            message=message,
                            lecture_id=lecture.id,
                            user_id=new_user.id,
                            status='pending',
                            is_confirmed=False
                        )

                        db.session.add(order)
                        db.session.commit()

                        # Send order confirmation email for new user
                        try:
                            send_order_confirmation_email(order, new_user, is_new_user=True)
                            db.session.commit()
                            flash('Заказ успешно создан! На ваш email отправлено письмо с подтверждением и данными для входа в систему.', 'success')
                        except Exception as e:
                            print(f"Error sending order confirmation email: {str(e)}")
                            flash('Заказ создан, но возникла проблема при отправке письма с подтверждением.', 'warning')

                return redirect(url_for('main.lecture_detail', slug=lecture.slug))
            except UnicodeDecodeError as e:
                print(f"UnicodeDecodeError when processing order form: {str(e)}")
                flash('Ошибка при обработке заказа. Пожалуйста, попробуйте еще раз.', 'error')
            except Exception as e:
                print(f"Error processing order form: {str(e)}")
                flash('Ошибка при обработке заказа. Пожалуйста, попробуйте еще раз.', 'error')

    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError when querying Lecture with ID {lecture_id}: {str(e)}")
        return render_template('404.html'), 404
    except Exception as e:
        print(f"Error querying Lecture with ID {lecture_id}: {str(e)}")
        return render_template('404.html'), 404

    return render_template('order_form.html', lecture=lecture, is_authenticated=is_authenticated)

@user_bp.route('/sitemap.xml')
def sitemap():
    """Generate and serve sitemap.xml"""
    try:
        # Get SEO settings
        seo_settings = SeoSettings.query.first()

        # If no settings exist, create default settings
        if not seo_settings:
            seo_settings = SeoSettings()
            db.session.add(seo_settings)
            db.session.commit()

        # Update last updated timestamp
        seo_settings.sitemap_last_updated = datetime.utcnow()
        db.session.commit()

        # Start XML content
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # Add homepage
        sitemap_xml += '  <url>\n'
        sitemap_xml += f'    <loc>{url_for("main.index", _external=True)}</loc>\n'
        sitemap_xml += f'    <lastmod>{datetime.utcnow().strftime("%Y-%m-%d")}</lastmod>\n'
        sitemap_xml += f'    <changefreq>{seo_settings.sitemap_changefreq}</changefreq>\n'
        sitemap_xml += f'    <priority>{seo_settings.sitemap_priority + 0.5}</priority>\n'  # Homepage gets higher priority
        sitemap_xml += '  </url>\n'

        # Add sections if enabled
        if seo_settings.sitemap_include_sections:
            sections = Section.query.filter_by(is_active=True).all()
            for section in sections:
                sitemap_xml += '  <url>\n'
                sitemap_xml += f'    <loc>{url_for("main.section_detail", slug=section.slug, _external=True)}</loc>\n'
                sitemap_xml += f'    <lastmod>{section.updated_at.strftime("%Y-%m-%d")}</lastmod>\n'
                sitemap_xml += f'    <changefreq>{seo_settings.sitemap_changefreq}</changefreq>\n'
                sitemap_xml += f'    <priority>{seo_settings.sitemap_priority + 0.3}</priority>\n'  # Sections get higher priority than lectures
                sitemap_xml += '  </url>\n'

        # Add lectures if enabled
        if seo_settings.sitemap_include_lectures:
            lectures = Lecture.query.filter_by(is_active=True).all()
            for lecture in lectures:
                sitemap_xml += '  <url>\n'
                sitemap_xml += f'    <loc>{url_for("main.lecture_detail", slug=lecture.slug, _external=True)}</loc>\n'
                sitemap_xml += f'    <lastmod>{lecture.updated_at.strftime("%Y-%m-%d")}</lastmod>\n'
                sitemap_xml += f'    <changefreq>{seo_settings.sitemap_changefreq}</changefreq>\n'
                sitemap_xml += f'    <priority>{seo_settings.sitemap_priority}</priority>\n'
                sitemap_xml += '  </url>\n'

        # Add static pages if enabled
        if seo_settings.sitemap_include_pages:
            # Add sections page
            sitemap_xml += '  <url>\n'
            sitemap_xml += f'    <loc>{url_for("main.sections", _external=True)}</loc>\n'
            sitemap_xml += f'    <lastmod>{datetime.utcnow().strftime("%Y-%m-%d")}</lastmod>\n'
            sitemap_xml += f'    <changefreq>{seo_settings.sitemap_changefreq}</changefreq>\n'
            sitemap_xml += f'    <priority>{seo_settings.sitemap_priority + 0.2}</priority>\n'
            sitemap_xml += '  </url>\n'

            # Add contacts page
            sitemap_xml += '  <url>\n'
            sitemap_xml += f'    <loc>{url_for("main.contacts", _external=True)}</loc>\n'
            sitemap_xml += f'    <lastmod>{datetime.utcnow().strftime("%Y-%m-%d")}</lastmod>\n'
            sitemap_xml += f'    <changefreq>{seo_settings.sitemap_changefreq}</changefreq>\n'
            sitemap_xml += f'    <priority>{seo_settings.sitemap_priority + 0.1}</priority>\n'
            sitemap_xml += '  </url>\n'

        # Close XML
        sitemap_xml += '</urlset>'

        return Response(sitemap_xml, mimetype='application/xml')

    except Exception as e:
        print(f"Error generating sitemap: {str(e)}")
        # Return a basic sitemap with just the homepage if there's an error
        basic_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
        basic_sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        basic_sitemap += '  <url>\n'
        basic_sitemap += f'    <loc>{url_for("main.index", _external=True)}</loc>\n'
        basic_sitemap += '  </url>\n'
        basic_sitemap += '</urlset>'

        return Response(basic_sitemap, mimetype='application/xml')

@user_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt file"""
    try:
        # Get SEO settings
        seo_settings = SeoSettings.query.first()

        # If no settings exist, create default settings with a basic robots.txt
        if not seo_settings:
            seo_settings = SeoSettings(
                robots_txt=f"User-agent: *\nAllow: /\nSitemap: {url_for('main.sitemap', _external=True)}"
            )
            db.session.add(seo_settings)
            db.session.commit()

        # If robots_txt is empty, generate a default one
        if not seo_settings.robots_txt:
            seo_settings.robots_txt = f"User-agent: *\nAllow: /\nSitemap: {url_for('main.sitemap', _external=True)}"
            db.session.commit()

        return Response(seo_settings.robots_txt, mimetype='text/plain')

    except Exception as e:
        print(f"Error serving robots.txt: {str(e)}")
        # Return a basic robots.txt if there's an error
        basic_robots = f"User-agent: *\nAllow: /\nSitemap: {url_for('main.sitemap', _external=True)}"
        return Response(basic_robots, mimetype='text/plain')

@user_bp.route('/feed.xml')
def generate_feed():
    """Generate and serve the YML feed."""
    try:
        # Получаем список активных лекций и категорий
        lectures = Lecture.query.filter_by(is_active=True).all()
        sections = Section.query.filter_by(is_active=True).all()

        # Генерация XML заголовка
        feed_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        feed_xml += '<yml_catalog date="{date}">\n'.format(date=datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
        feed_xml += '  <shop>\n'
        feed_xml += '    <name>{}</name>\n'.format(escape("Биолекторий"))
        feed_xml += '    <company>{}</company>\n'.format(escape("Зоологический музей Московского государственного университета имени М. В. Ломоносова"))
        feed_xml += '    <url>{}</url>\n'.format("https://biolectures.ru")
        feed_xml += '    <email>{}</email>\n'.format("biolectures@mail.ru")
        feed_xml += '    <picture>{}</picture>\n'.format(f"https://biolectures.ru/static/img/logo.png")
        feed_xml += '    <description>{}</description>\n'.format(escape("Лекции для всех возрастов"))

        # Добавляем валюту
        feed_xml += '    <currencies>\n'
        feed_xml += '      <currency id="RUR" rate="1"/>\n'
        feed_xml += '    </currencies>\n'

        # Добавляем наборы курсов (пример с категориями)
        feed_xml += '    <sets>\n'
        for section in sections:
            feed_xml += '      <set id="s{id}">\n'.format(id=section.id)
            feed_xml += '        <name>{}</name>\n'.format(escape(section.name))
            feed_xml += '        <url>{}</url>\n'.format(
                url_for('main.sections', _external=True)
            )
            feed_xml += '      </set>\n'
        feed_xml += '    </sets>\n'

        # Генерация предложений (offers) на основе лекций
        feed_xml += '    <offers>\n'
        for lecture in lectures:
            feed_xml += '      <offer id="{id}">\n'.format(id=lecture.id)
            # Название лекции
            title = lecture.title or "Без названия"
            feed_xml += '        <name>{}</name>\n'.format(escape(title))
            # URL-адрес лекции
            feed_xml += '        <url>{}</url>\n'.format(
                url_for('main.lecture_detail', slug=lecture.slug, _external=True)
            )

            # Категория
            feed_xml += '        <categoryId>{}</categoryId>\n'.format(10006)

            # Указываем id наборов лекций
            set_ids = getattr(lecture, 'set_ids', "s1")
            feed_xml += '        <set-ids>{}</set-ids>\n'.format(escape(set_ids))

            # Цена лекции
            price = getattr(lecture, 'price', 0)
            feed_xml += '        <price>{}</price>\n'.format(price)
            feed_xml += '        <currencyId>RUR</currencyId>\n'

            # Дата ближайшего события
            feed_xml += '        <param name="Ближайшая дата">{}</param>\n'.format(get_start_date())
            duration = getattr(lecture, 'duration', 1)
            feed_xml += '        <param name="Продолжительность" unit="час">{}</param>\n'.format(duration)

            # Описание
            description = lecture.description or "Описание отсутствует"
            feed_xml += '        <description>{}</description>\n'.format(escape(description))
            # Дополнительное изображение для лекции
            if lecture.image:
                feed_xml += '        <picture>{}</picture>\n'.format(f"https://biolectures.ru/static/uploads/lectures/{lecture.image}")

            # Обучающие параметры
            feed_xml += '        <param name="Формат обучения">В группе с наставником</param>\n'


            feed_xml += '        <param name="Есть вебинары">false</param>\n'
            feed_xml += '        <param name="Есть домашние работы">false</param>\n'
            feed_xml += '        <param name="Есть видеоуроки">false</param>\n'
            feed_xml += '        <param name="Есть текстовые уроки">false</param>\n'
            feed_xml += '        <param name="Есть тренажеры">false</param>\n'
            feed_xml += '        <param name="Есть сообщество">false</param>\n'

            feed_xml += '        <param name="Сложность">Для новичков</param>\n'
            feed_xml += '        <param name="Тип обучения">Курс</param>\n'
            feed_xml += '        <param name="План">Вводная часть, Основная часть, Практическая часть, Заключение</param>\n'

            feed_xml += '      </offer>\n'

        # Закрытие секции предложений
        feed_xml += '    </offers>\n'

        # Закрытие XML
        feed_xml += '  </shop>\n'
        feed_xml += '</yml_catalog>'

        return Response(feed_xml, mimetype='application/xml')

    except Exception as e:
        print(f"Error generating feed.xml: {str(e)}")
        return Response("Ошибка при генерации XML фида", status=500)
