from flask import render_template, request
from . import web
from app.models.items import LaundryItem
from app.models import User
from app import db
import os

@web.route('/')
def index():
    return render_template('landing.html')

@web.route('/debug-init-db')
def debug_init_db():
    try:
        db.create_all()
        return "Database tables created successfully!"
    except Exception as e:
        return f"Error creating tables: {str(e)}"

@web.route('/debug-config')
def debug_config():
    db_url = os.environ.get('DATABASE_URL')
    status = "Set" if db_url else "Not Set"
    return f"DATABASE_URL is: {status}"

@web.route('/debug-create-admin')
def debug_create_admin():
    """
    Secure admin creation endpoint.
    Protected by ADMIN_SETUP_TOKEN env var.
    Usage: /debug-create-admin?email=you@example.com&password=yourpass&token=YOUR_TOKEN
    Disable by removing ADMIN_SETUP_TOKEN from environment after first use.
    """
    import os
    setup_token = os.environ.get('ADMIN_SETUP_TOKEN', '').strip()

    # If no token is configured, this endpoint is disabled
    if not setup_token:
        return "Admin setup is disabled. Set ADMIN_SETUP_TOKEN in environment to enable.", 403

    # Validate token from query string
    provided_token = request.args.get('token', '').strip()
    if not provided_token or provided_token != setup_token:
        return "Invalid or missing token.", 403

    email    = request.args.get('email', '').strip()
    password = request.args.get('password', '').strip()

    if not email or not password:
        return "Usage: /debug-create-admin?email=EMAIL&password=PASSWORD&token=TOKEN", 400

    if len(password) < 8:
        return "Password must be at least 8 characters.", 400

    try:
        from app.models import UserProfile
        # Ensure all tables exist before querying
        db.create_all()
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, role='admin')
            user.password = password
            profile = UserProfile(full_name='Super Admin', phone='')
            user.profile = profile
            db.session.add(user)
            action = "Created"
        else:
            user.role = 'admin'
            user.password = password
            action = "Updated"

        db.session.commit()
        return f"Admin {action} successfully: {email}. Remove ADMIN_SETUP_TOKEN from environment now.", 200
    except Exception as e:
        return f"Error: {str(e)}", 500



@web.route('/pricing')
def pricing():
    items = LaundryItem.query.all()
    categories = {}
    for item in items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
    return render_template('pricing.html', categories=categories)

@web.route('/services')
def services():
    return render_template('services.html')

@web.route('/about')
def about():
    return render_template('about.html')

@web.route('/help')
def help():
    return render_template('help.html')

@web.route('/login')
def login():
    return render_template('auth/login.html')

@web.route('/register')
def register():
    return render_template('auth/register.html')

@web.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot_password.html')

@web.route('/reset-password/<token>')
def reset_password_page(token):
    return render_template('auth/reset_password.html', token=token) # Pass token to template if needed, or JS extracts it

@web.route('/dashboard')
def dashboard():
    return render_template('customer/dashboard.html')

@web.route('/create-order')
def create_order():
    return render_template('customer/create_order.html')

@web.route('/rider/dashboard')
def rider_dashboard():
    return render_template('rider/dashboard.html')

@web.route('/staff/dashboard')
def staff_dashboard():
    return render_template('staff/dashboard.html')

@web.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@web.route('/admin/items')
def admin_items():
    return render_template('admin/items.html')

@web.route('/admin/users')
def admin_users():
    return render_template('admin/users.html')

@web.route('/admin/orders')
def admin_orders():
    return render_template('admin/orders.html')

@web.route('/admin/settings')
def admin_settings():
    return render_template('admin/settings.html')

@web.route('/admin/finance')
def admin_finance():
    return render_template('admin/finance.html')

@web.route('/admin/reports')
def admin_reports():
    return render_template('admin/reports.html')

@web.route('/profile')
def profile():
    return render_template('profile.html')
