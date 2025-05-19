from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Define the association table for user roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# Define the association table for lecturer-lecture relationships
lecturer_lectures = db.Table('lecturer_lectures',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('lecture_id', db.Integer, db.ForeignKey('lectures.id'), primary_key=True)
)

class Role(db.Model):
    """Model for user roles"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model):
    """Model for users"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    avatar = db.Column(db.String(255), nullable=True)  # Path to user avatar image
    is_active = db.Column(db.Boolean, default=False)  # Changed to False by default, will be set to True after email confirmation
    email_confirmed = db.Column(db.Boolean, default=False)  # Flag to track if email is confirmed
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)  # Token for email confirmation
    confirmation_token_expires = db.Column(db.DateTime, nullable=True)  # Expiration time for confirmation token
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    can_access_admin = db.Column(db.Boolean, default=False)  # Flag to allow lecturers to access admin panel

    # Relationship with orders
    orders = db.relationship('OrderForm', foreign_keys='OrderForm.user_id', lazy='dynamic')

    # Relationship with roles (many-to-many)
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))

    # Relationship with lectures for lecturers (many-to-many)
    lectures = db.relationship('Lecture', secondary=lecturer_lectures, lazy='dynamic', backref=db.backref('lecturers', lazy='dynamic'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def __repr__(self):
        return f'<User {self.username}>'

class Section(db.Model):
    """Model for lecture sections (categories)"""
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    image = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with lectures
    lectures = db.relationship('Lecture', backref='section', lazy='dynamic')

    def __repr__(self):
        return f'<Section {self.name}>'

class LectureType(db.Model):
    """Model for lecture types (interactive, regular, etc.)"""
    __tablename__ = 'lecture_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Relationship with lectures
    lectures = db.relationship('Lecture', backref='lecture_type', lazy='dynamic')

    def __repr__(self):
        return f'<LectureType {self.name}>'

class Lecture(db.Model):
    """Model for lectures"""
    __tablename__ = 'lectures'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255))
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    image = db.Column(db.String(255))
    slug = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    # Foreign keys
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    lecture_type_id = db.Column(db.Integer, db.ForeignKey('lecture_types.id'))

    def __repr__(self):
        return f'<Lecture {self.title}>'

class Contact(db.Model):
    """Model for contact information"""
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    position = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Contact {self.name}>'

class OrderForm(db.Model):
    """Model for lecture order forms"""
    __tablename__ = 'order_forms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    organization = db.Column(db.String(255))
    message = db.Column(db.Text)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ID of the lecturer assigned to this order
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, processing, approved, cancelled
    is_confirmed = db.Column(db.Boolean, default=False)  # Flag to track if order is confirmed by email
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)  # Token for order confirmation
    confirmation_token_expires = db.Column(db.DateTime, nullable=True)  # Expiration time for confirmation token
    lecture_date = db.Column(db.Date, nullable=True)  # Date when the lecture will be conducted (set by admin)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with lecture
    lecture = db.relationship('Lecture', backref='orders')

    # Relationship with user who placed the order
    user = db.relationship('User', foreign_keys=[user_id])

    # Relationship with lecturer (different from the user who placed the order)
    lecturer = db.relationship('User', foreign_keys=[lecturer_id], backref='assigned_orders')

    def __repr__(self):
        return f'<OrderForm {self.name} - {self.status}>'

class MenuItem(db.Model):
    """Model for menu items"""
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))

    # Self-referential relationship for hierarchical menu
    children = db.relationship('MenuItem', backref=db.backref('parent', remote_side=[id]))

    def __repr__(self):
        return f'<MenuItem {self.name}>'

class HomeBlock(db.Model):
    """Model for homepage blocks"""
    __tablename__ = 'home_blocks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    image = db.Column(db.String(255))
    button_text = db.Column(db.String(100))
    button_url = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    block_type = db.Column(db.String(50), default='content')  # header, content, gallery, etc.
    template = db.Column(db.String(255))  # Name of the template file to use
    slug = db.Column(db.String(255), unique=False, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<HomeBlock {self.title}>'

class SeoSettings(db.Model):
    """Model for SEO settings including sitemap and robots.txt"""
    __tablename__ = 'seo_settings'

    id = db.Column(db.Integer, primary_key=True)
    robots_txt = db.Column(db.Text, nullable=True)  # Content of robots.txt file
    sitemap_include_lectures = db.Column(db.Boolean, default=True)  # Include lectures in sitemap
    sitemap_include_sections = db.Column(db.Boolean, default=True)  # Include sections in sitemap
    sitemap_include_pages = db.Column(db.Boolean, default=True)  # Include static pages in sitemap
    sitemap_changefreq = db.Column(db.String(20), default='weekly')  # Sitemap change frequency
    sitemap_priority = db.Column(db.Float, default=0.5)  # Default priority for sitemap entries
    sitemap_last_updated = db.Column(db.DateTime, default=datetime.utcnow)  # Last time sitemap was updated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SeoSettings {self.id}>'
