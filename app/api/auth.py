from flask_restx import Namespace, Resource, fields
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, UserProfile
from app import db
from app.utils.email import send_email
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer

auth_ns = Namespace('auth', description='Authentication operations')

# Request Models
login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

register_model = auth_ns.model('Register', {
    'email': fields.String(required=True),
    'password': fields.String(required=True),
    'full_name': fields.String(required=True),
    'phone': fields.String()
})

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        """Register a new customer"""
        data = request.get_json()
        
        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered'}, 400
            
        new_user = User(
            email=data['email'],
            role='customer' # Default to customer for public registration
        )
        new_user.password = data['password']
        
        # Create profile
        profile = UserProfile(
            full_name=data['full_name'],
            phone=data.get('phone', '')
        )
        new_user.profile = profile
        
        db.session.add(new_user)
        db.session.commit()
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send Welcome Email
        try:
            send_email(new_user.email, 'Welcome to Spark Laundry', 'email/welcome.html', user=new_user)
        except Exception as e:
            print(f"Welcome email failed: {e}")
            
        return {'message': 'User registered successfully'}, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login and get JWT token"""
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        
        if user and user.verify_password(data['password']):
            # Identity must be a string for flask-jwt-extended
            access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
            return {
                'access_token': access_token,
                'user': user.to_dict()
            }, 200
            
        return {'message': 'Invalid credentials'}, 401

@auth_ns.route('/me')
class Me(Resource):
    @auth_ns.doc(security='apikey')
    @jwt_required()
    def get(self):
        """Get current user profile"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return {'message': 'User not found'}, 404
        return user.to_dict(), 200
        return user.to_dict(), 200

@auth_ns.route('/forgot-password')
class ForgotPassword(Resource):
    def post(self):
        """Request password reset email"""
        data = request.get_json()
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(user.email, salt='recover-key')
            # Generate Link (Assuming frontend route /reset-password will exist)
            # For now, we point to the backend template route or a frontend URL
            # Let's assume we serve a server-side template for reset
            reset_url = url_for('web.reset_password_page', token=token, _external=True)
            
            try:
                send_email(user.email, 'Reset Your Password', 'email/reset_password.html', reset_url=reset_url)
            except Exception as e:
                print(f"Reset email failed: {e}")
                
        # Always return success to prevent email enumeration
        return {'message': 'If an account exists, a reset link has been sent.'}, 200

@auth_ns.route('/reset-password/<token>')
class ResetPassword(Resource):
    def post(self, token):
        """Reset password using token"""
        data = request.get_json()
        new_password = data.get('password')
        
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = s.loads(token, salt='recover-key', max_age=3600) # 1 hour expiration
        except:
            return {'message': 'Invalid or expired token'}, 400
            
        user = User.query.filter_by(email=email).first_or_404()
        user.password = new_password
        db.session.commit()
        
        return {'message': 'Password updated successfully'}, 200


@auth_ns.route('/profile')
class UpdateProfile(Resource):
    @jwt_required()
    def put(self):
        """Update current user's profile (name, phone, email, password)"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return {'message': 'User not found'}, 404

        data = request.get_json()

        # Update email (check uniqueness)
        new_email = data.get('email', '').strip()
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                return {'message': 'Email already in use'}, 400
            user.email = new_email

        # Update password
        new_password = data.get('new_password', '').strip()
        current_password = data.get('current_password', '').strip()
        if new_password:
            if not current_password:
                return {'message': 'Current password is required to set a new one'}, 400
            if not user.verify_password(current_password):
                return {'message': 'Current password is incorrect'}, 400
            user.password = new_password

        # Update profile fields
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
            db.session.add(user.profile)

        if 'full_name' in data:
            user.profile.full_name = data['full_name'].strip()
        if 'phone' in data:
            user.profile.phone = data['phone'].strip()

        db.session.commit()
        return user.to_dict(), 200
