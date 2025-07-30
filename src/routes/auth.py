from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from src.database import db
from src.models.user import User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        logger.info(f"Registration attempt for email: {data.get('email')}")
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user with onboarding defaults
        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role=data.get('role', 'affiliate'),
            # Onboarding defaults
            onboarding_status='pending',
            onboarding_step=1,
            kyc_status='pending',
            agreements_complete=False,
            affiliate_agreement_signed=False,
            finders_fee_contract_signed=False
        )
        
        # Set password
        user.set_password(data['password'])
        
        # Handle referral code
        if data.get('referral_code'):
            referrer = User.query.filter_by(referral_code=data['referral_code']).first()
            if referrer:
                user.referred_by_id = referrer.id
                logger.info(f"User referred by: {referrer.email}")
        
        # Save user
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User registered successfully: {user.email}")
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7)
        )
        
        # New users always need onboarding
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'token': access_token,
            'user': user.to_dict(),
            'requires_onboarding': True,
            'redirect_to': 'onboarding',
            'onboarding_step': user.onboarding_step,
            'next_action': {
                'step': 'welcome',
                'action': 'start_onboarding',
                'message': 'Welcome! Please complete the onboarding process to access your dashboard.'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        logger.info(f"Login attempt for email: {data.get('email')}")
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            logger.warning(f"Login failed - user not found: {data['email']}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.check_password(data['password']):
            logger.warning(f"Login failed - invalid password: {data['email']}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"User logged in successfully: {user.email}")
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7)
        )
        
        # Determine redirect based on onboarding status
        requires_onboarding = not user.onboarding_complete
        
        if requires_onboarding:
            # User needs to complete onboarding
            redirect_to = 'onboarding'
            next_action = _get_next_onboarding_action(user)
        else:
            # User can access dashboard
            redirect_to = 'dashboard'
            next_action = {
                'step': 'completed',
                'action': 'access_dashboard',
                'message': 'Welcome back! Access your dashboard.'
            }
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': access_token,
            'user': user.to_dict(),
            'requires_onboarding': requires_onboarding,
            'redirect_to': redirect_to,
            'onboarding_step': user.onboarding_step,
            'next_action': next_action
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine next action
        requires_onboarding = not user.onboarding_complete
        next_action = _get_next_onboarding_action(user) if requires_onboarding else None
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'requires_onboarding': requires_onboarding,
            'onboarding_step': user.onboarding_step,
            'next_action': next_action
        })
        
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to get user', 'details': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token removal)"""
    try:
        user_id = get_jwt_identity()
        logger.info(f"User logged out: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/test', methods=['GET'])
def test_auth():
    """Test endpoint to verify auth blueprint is working"""
    return jsonify({
        'success': True,
        'message': 'Auth blueprint is working',
        'timestamp': datetime.utcnow().isoformat()
    })

def _get_next_onboarding_action(user):
    """Get the next onboarding action for a user"""
    if user.onboarding_complete:
        return {
            'step': 'completed',
            'action': 'access_dashboard',
            'message': 'Onboarding complete! You can now access the full dashboard.'
        }
    
    if user.kyc_status == 'rejected':
        return {
            'step': 'kyc_resubmit',
            'action': 'upload_kyc',
            'message': 'Your KYC documents were rejected. Please resubmit with valid documents.',
            'rejection_reason': user.kyc_rejection_reason
        }
    
    if user.kyc_status == 'submitted':
        return {
            'step': 'pending_review',
            'action': 'wait',
            'message': 'Your documents are under review. You will be notified once approved.'
        }
    
    if not user.finders_fee_contract_signed:
        return {
            'step': 'document_signing',
            'action': 'sign_contract',
            'message': 'Please sign the Finder\'s Fee Contract to continue.'
        }
    
    if user.finders_fee_contract_signed and user.kyc_status == 'pending':
        return {
            'step': 'kyc_upload',
            'action': 'upload_kyc',
            'message': 'Please upload your government-issued ID for verification.'
        }
    
    return {
        'step': 'welcome',
        'action': 'start_onboarding',
        'message': 'Welcome! Let\'s complete your onboarding process.'
    }

