from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import ImageUploadField, Select2Field
from flask import Blueprint, url_for, redirect, request, flash, session, render_template
from werkzeug.utils import secure_filename
from wtforms import PasswordField, DateField
import os

from app import db
from models.models import User, Role, Section, LectureType, Lecture, Contact, OrderForm, MenuItem, HomeBlock, SeoSettings

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

class SecureModelView(ModelView):
    """Base ModelView with security and customizations"""
    def is_accessible(self):
        # Check if user is authenticated and has admin, editor role, or is a lecturer with admin access
        if 'user_id' not in session:
            return False

        user = User.query.get(session['user_id'])
        return user is not None and (
            user.has_role('admin') or 
            user.has_role('editor') or 
            (user.has_role('lecturer') and user.can_access_admin)
        )

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access
        flash('You need to be logged in as an admin to access this area.', 'error')
        return redirect(url_for('auth.login', next=request.url))

class AdminOnlyModelView(ModelView):
    """ModelView that only allows admin role access"""
    def is_accessible(self):
        # Check if user is authenticated and has admin role
        if 'user_id' not in session:
            return False

        user = User.query.get(session['user_id'])
        return user is not None and user.has_role('admin')

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access
        flash('You need to be logged in as an admin to access this area.', 'error')
        return redirect(url_for('auth.login', next=request.url))

class SectionAdmin(SecureModelView):
    """Admin view for Section model"""
    column_list = ('name', 'slug', 'order', 'is_active')
    column_searchable_list = ('name', 'slug')
    column_filters = ('is_active',)
    form_excluded_columns = ('lectures',)

    # Handle image upload
    form_extra_fields = {
        'image': ImageUploadField('Image',
                                base_path=lambda: os.path.join(os.getcwd(), 'static', 'uploads', 'sections'),
                                url_relative_path='uploads/sections/')
    }

class LectureTypeAdmin(SecureModelView):
    """Admin view for LectureType model"""
    column_list = ('name', 'description')
    column_searchable_list = ('name',)
    form_excluded_columns = ('lectures',)

class LectureAdmin(SecureModelView):
    """Admin view for Lecture model"""
    column_list = ('order','title','slug', 'section', 'lecture_type', 'is_active')
    column_searchable_list = ('title', 'subtitle', 'slug')
    column_filters = ('section', 'lecture_type', 'is_active')

    column_formatters = {}

    # Handle image upload and lecturers selection
    form_extra_fields = {
        'image': ImageUploadField('Image',
                                base_path=lambda: os.path.join(os.getcwd(), 'static', 'uploads', 'lectures'),
                                url_relative_path='uploads/lectures/')
    }

    def on_model_change(self, form, model, is_created):
        """Handle the many-to-many relationship with lecturers"""
        # Get the selected lecturers from the form
        if 'lecturers' in form._fields:
            selected_lecturers = form._fields['lecturers'].data

            # Clear existing lecturers
            model.lecturers = []

            # Add selected lecturers
            if selected_lecturers:
                for lecturer_id in selected_lecturers:
                    lecturer = User.query.get(lecturer_id)
                    if lecturer and lecturer.has_role('lecturer'):
                        model.lecturers.append(lecturer)

    def create_form(self, obj=None):
        form = super(LectureAdmin, self).create_form(obj)
        self._add_lecturers_field(form)
        return form

    def edit_form(self, obj=None):
        form = super(LectureAdmin, self).edit_form(obj)
        self._add_lecturers_field(form, obj)
        return form

    def _add_lecturers_field(self, form, obj=None):
        """Add a field for selecting lecturers"""
        from wtforms import SelectMultipleField

        # Get all users with lecturer role
        lecturers = User.query.join(User.roles).filter(Role.name == 'lecturer').all()
        choices = [(str(l.id), f"{l.first_name} {l.last_name} ({l.username})") for l in lecturers]

        # Create the field
        form.lecturers = SelectMultipleField('Лекторы', choices=choices)

        # Set default value if editing an existing lecture
        if obj is not None:
            form.lecturers.data = [str(l.id) for l in obj.lecturers]

class ContactAdmin(SecureModelView):
    """Admin view for Contact model"""
    column_list = ('name', 'email', 'phone', 'position', 'is_active')
    column_searchable_list = ('name', 'email', 'phone')
    column_filters = ('is_active',)

    # Handle image upload
    form_extra_fields = {
        'image': ImageUploadField('Image',
                                base_path=lambda: os.path.join(os.getcwd(), 'static', 'uploads', 'contacts'),
                                url_relative_path='uploads/contacts/')
    }

class OrderFormAdmin(SecureModelView):
    """Admin view for OrderForm model"""
    column_list = ('created_at', 'name', 'email', 'organization', 'lecture', 'lecturer', 'lecture_date', 'status')
    column_searchable_list = ('name', 'email', 'organization')
    column_filters = ('status', 'created_at', 'lecturer', 'lecture_date')
    form_excluded_columns = ('created_at', 'updated_at')

    # Make some fields read-only in edit mode
    form_edit_rules = ('name', 'email', 'phone', 'organization', 'message', 'lecture', 'lecturer', 'lecture_date', 'status')
    form_create_rules = ('name', 'email', 'phone', 'organization', 'message', 'lecture', 'lecturer', 'lecture_date', 'status')

    # Add status dropdown, lecturer selection, and date picker
    form_extra_fields = {
        'lecture': QuerySelectField(
            'Lecture',
            query_factory=lambda: Lecture.query,  # Обеспечивает выбор только из доступных лекций
            get_label='title'  # Используем поле title для отображения вместо <Lecture>
        ),

        'lecturer': QuerySelectField(
            'Lecturer',
            query_factory=lambda: User.query.join(User.roles).filter(Role.name == 'lecturer').all(),
            get_label=lambda u: f"{u.first_name} {u.last_name} ({u.username})",
            allow_blank=True,
            blank_text='-- No lecturer assigned --'
        ),

        'status': Select2Field('Status', choices=[
            ('new', 'Новый'),
            ('processing', 'В обработке'),
            ('approved', 'Утвержден'),
            ('cancelled', 'Отменен')
        ]),

        'lecture_date': DateField('Дата проведения лекции', 
                                    description='Дата, когда будет проведена лекция',
                                    format='%Y-%m-%d')
    }

    # Кастомный форматтер для created_at
    def _format_created_at(view, context, model, name):
        if model.created_at:
            return model.created_at.strftime('%Y-%m-%d %H:%M')  # Only date, hours, and minutes
        return '—'

    # Custom formatter for lecture column
    def _lecture_formatter(view, context, model, name):
        # Assuming `lecture` is a relationship or object with a `title` property
        return f"{model.lecture.order}. {model.lecture.title}" if model.lecture else '—'

    # Custom formatter for lecturer column
    def _lecturer_formatter(view, context, model, name):
        if model.lecturer:
            return f"{model.lecturer.first_name} {model.lecturer.last_name} ({model.lecturer.username})"
        return '— Не назначен —'

    # Custom formatter for lecture_date column
    def _lecture_date_formatter(view, context, model, name):
        if model.lecture_date:
            return model.lecture_date.strftime('%d.%m.%Y')
        return '— Не назначена —'

    column_formatters = {
        'created_at': _format_created_at,
        'lecture': _lecture_formatter,
        'lecturer': _lecturer_formatter,
        'lecture_date': _lecture_date_formatter
    }


class MenuItemAdmin(SecureModelView):
    """Admin view for MenuItem model"""
    column_list = ('name', 'url', 'parent', 'order', 'is_active')
    column_searchable_list = ('name',)
    column_filters = ('is_active',)

    # Customize form to handle parent-child relationship
    form_excluded_columns = ('children',)

class HomeBlockAdmin(SecureModelView):
    """Admin view for HomeBlock model"""
    column_list = ('title', 'block_type', 'template', 'order', 'is_active')
    column_searchable_list = ('title',)
    column_filters = ('block_type', 'is_active')

    def _get_template_choices(self):
        """Get a list of available templates from the block_templates directory"""
        template_dir = os.path.join(os.getcwd(), 'templates', 'block_templates')
        templates = []

        # Add an empty option
        templates.append(('', 'Use default template'))

        # Scan the template directory
        if os.path.exists(template_dir):
            for filename in os.listdir(template_dir):
                if filename.endswith('.html'):
                    # Use the filename as both the value and label
                    templates.append((filename, filename))

        return templates

    # Handle image upload and template selection
    form_extra_fields = {
        'image': ImageUploadField('Image',
                                base_path=lambda: os.path.join(os.getcwd(), 'static', 'uploads', 'blocks'),
                                url_relative_path='uploads/blocks/'),
        'template': Select2Field('Template', choices=lambda: HomeBlockAdmin._get_template_choices(None))
    }

class UserAdmin(AdminOnlyModelView):
    """Admin view for User model"""
    column_list = ('username', 'email', 'first_name', 'last_name', 'avatar', 'is_active', 'can_access_admin', 'created_at')
    column_searchable_list = ('username', 'email', 'first_name', 'last_name')
    column_filters = ('is_active', 'roles', 'can_access_admin')
    form_excluded_columns = ('password_hash',)

    # Custom form for password handling and avatar upload
    form_extra_fields = {
        'new_password': PasswordField('New Password'),
        'avatar': ImageUploadField('Avatar',
                                base_path=lambda: os.path.join(os.getcwd(), 'static', 'uploads', 'avatars'),
                                url_relative_path='uploads/avatars/')
    }

    # Format the can_access_admin column to show only for lecturers
    def _format_can_access_admin(view, context, model, name):
        if model.has_role('lecturer'):
            return 'Да' if model.can_access_admin else 'Нет'
        return '—'

    column_formatters = {
        'can_access_admin': _format_can_access_admin
    }

    def on_model_change(self, form, model, is_created):
        if form.new_password.data:
            model.password = form.new_password.data

        # Only allow can_access_admin for lecturers
        if model.can_access_admin and not model.has_role('lecturer'):
            model.can_access_admin = False

class RoleAdmin(AdminOnlyModelView):
    """Admin view for Role model"""
    column_list = ('name', 'description')
    column_searchable_list = ('name', 'description')

class SeoSettingsAdmin(AdminOnlyModelView):
    """Admin view for SEO settings"""
    column_list = ('id', 'sitemap_include_lectures', 'sitemap_include_sections', 'sitemap_include_pages', 
                  'sitemap_changefreq', 'sitemap_priority', 'sitemap_last_updated')
    form_columns = ('robots_txt', 'sitemap_include_lectures', 'sitemap_include_sections', 
                   'sitemap_include_pages', 'sitemap_changefreq', 'sitemap_priority')

    form_choices = {
        'sitemap_changefreq': [
            ('always', 'Always'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
            ('never', 'Never')
        ]
    }

    form_args = {
        'robots_txt': {
            'label': 'Robots.txt Content',
            'description': 'Content of robots.txt file. Include "Sitemap: https://yourdomain.com/sitemap.xml" to reference your sitemap.'
        },
        'sitemap_include_lectures': {
            'label': 'Include Lectures',
            'description': 'Include lecture pages in sitemap'
        },
        'sitemap_include_sections': {
            'label': 'Include Sections',
            'description': 'Include section pages in sitemap'
        },
        'sitemap_include_pages': {
            'label': 'Include Static Pages',
            'description': 'Include static pages (contacts, etc.) in sitemap'
        },
        'sitemap_changefreq': {
            'label': 'Change Frequency',
            'description': 'How frequently the pages typically change'
        },
        'sitemap_priority': {
            'label': 'Priority',
            'description': 'Priority of pages (0.0 to 1.0)'
        }
    }

    def on_model_change(self, form, model, is_created):
        """Ensure there's only one settings record"""
        if is_created:
            # Check if there are other settings records
            count = SeoSettings.query.count()
            if count > 1:
                # Delete the oldest records, keeping only the newest
                old_settings = SeoSettings.query.order_by(SeoSettings.id).limit(count - 1).all()
                for setting in old_settings:
                    db.session.delete(setting)

def init_admin(app):
    """Initialize the admin interface"""
    admin = Admin(app, name='Biolectures Admin', template_mode='bootstrap4', url='/admin', endpoint='admin_panel')

    # Add model views
    admin.add_view(SeoSettingsAdmin(SeoSettings, db.session, name='SEO Settings', category='Settings'))
    admin.add_view(UserAdmin(User, db.session, name='Users', endpoint='admin_users'))
    admin.add_view(RoleAdmin(Role, db.session, name='Roles'))
    admin.add_view(SectionAdmin(Section, db.session, name='Sections'))
    admin.add_view(LectureTypeAdmin(LectureType, db.session, name='Lecture Types'))
    admin.add_view(LectureAdmin(Lecture, db.session, name='Lectures'))
    admin.add_view(ContactAdmin(Contact, db.session, name='Contacts'))
    admin.add_view(OrderFormAdmin(OrderForm, db.session, name='Orders'))
    admin.add_view(MenuItemAdmin(MenuItem, db.session, name='Menu Items'))
    admin.add_view(HomeBlockAdmin(HomeBlock, db.session, name='Home Blocks'))

    return admin

# Routes for the admin blueprint
@admin_bp.route('/')
def index():
    """Admin dashboard"""
    # Check if user is authenticated and has admin, editor role, or is a lecturer with admin access
    if 'user_id' not in session:
        flash('You need to be logged in as an admin to access this area.', 'error')
        return redirect(url_for('auth.login', next=request.url))

    user = User.query.get(session['user_id'])
    if not user or (
        not user.has_role('admin') and 
        not user.has_role('editor') and 
        not (user.has_role('lecturer') and user.can_access_admin)
    ):
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    # Render the admin dashboard template
    return render_template('admin/dashboard.html')
