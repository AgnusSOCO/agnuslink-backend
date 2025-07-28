from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import bcrypt
import re

from src.models.user import User, db
from src.models.agreement import Agreement

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'{field} is required'
                    }
                }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        phone = data.get('phone', '').strip()
        referred_by_code = data.get('referred_by_code', '').strip()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Invalid email format'
                }
            }), 400
        
        # Validate password strength
        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': password_message
                }
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USER_EXISTS',
                    'message': 'User with this email already exists'
                }
            }), 400
        
        # Find referring user if referral code provided
        referring_user = None
        if referred_by_code:
            referring_user = User.query.filter_by(referral_code=referred_by_code).first()
            if not referring_user:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REFERRAL',
                        'message': 'Invalid referral code'
                    }
                }), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create new user
        new_user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            referred_by_id=referring_user.id if referring_user else None
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create required agreements for the new user
        Agreement.create_required_agreements(new_user.id)
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'id': new_user.id,
                'email': new_user.email,
                'referral_code': new_user.referral_code,
                'first_name': new_user.first_name,
                'last_name': new_user.last_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred during registration'
            }
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Email and password are required'
                }
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            }), 401
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            }), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        # Check agreement status
        agreements_complete, missing_agreements = Agreement.check_required_agreements(user.id)
        
        return jsonify({
            'success': True,
            'token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_verified': user.is_verified,
                'referral_code': user.referral_code,
                'agreements_complete': agreements_complete,
                'missing_agreements': missing_agreements
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred during login'
            }
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        # Check agreement status
        agreements_complete, missing_agreements = Agreement.check_required_agreements(user.id)
        
        user_data = user.to_dict()
        user_data.update({
            'agreements_complete': agreements_complete,
            'missing_agreements': missing_agreements
        })
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching user data'
            }
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a production app, you might want to blacklist the token
    # For now, we'll just return a success message
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Current password and new password are required'
                }
            }), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Find user
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        # Check current password
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PASSWORD',
                    'message': 'Current password is incorrect'
                }
            }), 400
        
        # Validate new password
        is_valid, password_message = validate_password(new_password)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': password_message
                }
            }), 400
        
        # Update password
        user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while changing password'
            }
        }), 500

