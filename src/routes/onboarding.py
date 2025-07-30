from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime

# Create onboarding blueprint with proper JWT string handling
onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Get user's onboarding status and next steps with proper JWT string handling"""
    try:
        # Lazy imports to avoid circular import issues
        from database import db
        from models.user import User
        
        # Get user identity (now should be a string after auth.py fix)
        user_identity = get_jwt_identity()
        
        # Debug logging for JWT identity
        print(f"JWT Identity: {user_identity}, Type: {type(user_identity)}")
        
        # Convert string user_id back to integer for database query
        try:
            user_id = int(user_identity)
        except (ValueError, TypeError):
            return jsonify({
                'error': f'Invalid user ID format in JWT token: {user_identity}',
                'success': False
            }), 401
        
        # Query user with proper error handling
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': f'User not found with ID: {user_id}'}), 404
        
        # Basic onboarding status logic
        current_step = 'welcome'
        progress = 0
        
        # Determine progress based on user attributes (with safe attribute access)
        agreement_signed = getattr(user, 'agreement_signed', False)
        kyc_verified = getattr(user, 'kyc_verified', False)
        onboarding_complete = getattr(user, 'onboarding_complete', False)
        
        if onboarding_complete:
            current_step = 'complete'
            progress = 100
        elif kyc_verified:
            current_step = 'complete'
            progress = 100
        elif agreement_signed:
            current_step = 'kyc_upload'
            progress = 60
        else:
            current_step = 'signature'
            progress = 20
        
        return jsonify({
            'success': True,
            'current_step': current_step,
            'progress': progress,
            'user_id': user.id,
            'user_email': user.email,
            'user_name': f"{user.first_name} {user.last_name}",
            'onboarding_complete': onboarding_complete,
            'kyc_verified': kyc_verified,
            'agreement_signed': agreement_signed,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'jwt_identity_received': user_identity,
            'jwt_identity_type': str(type(user_identity)),
            'processed_user_id': user_id
        })
        
    except ImportError as e:
        return jsonify({
            'error': f'Import error: {str(e)}',
            'success': False
        }), 500
    except Exception as e:
        return jsonify({
            'error': f'Error: {str(e)}',
            'success': False,
            'error_type': str(type(e))
        }), 500

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Onboarding routes with JWT string fixes are working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'routes_available': [
            '/status (requires JWT)',
            '/test',
            '/health',
            '/user-info (requires JWT)'
        ],
        'blueprint_name': 'onboarding',
        'import_status': 'database_and_user_model_imported_with_jwt_string_fixes',
        'features': [
            'JWT authentication with string identity handling',
            'User model access',
            'Enhanced error handling',
            'Debug information',
            'Proper type conversion'
        ]
    })

@onboarding_bp.route('/health', methods=['GET'])
def onboarding_health():
    """Health check for onboarding blueprint"""
    try:
        from database import db
        from models.user import User
        
        # Test database and model access
        user_count = User.query.count()
        
        return jsonify({
            'status': 'healthy',
            'blueprint': 'onboarding',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'database_connected': True,
            'user_model_accessible': True,
            'total_users': user_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'blueprint': 'onboarding',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@onboarding_bp.route('/user-info', methods=['GET'])
@jwt_required()
def get_user_info():
    """Get current user information with JWT string handling"""
    try:
        from database import db
        from models.user import User
        
        # Get user identity and convert to integer
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'onboarding_complete': getattr(user, 'onboarding_complete', False),
                'kyc_verified': getattr(user, 'kyc_verified', False),
                'agreement_signed': getattr(user, 'agreement_signed', False)
            },
            'jwt_debug': {
                'received_identity': user_identity,
                'processed_user_id': user_id,
                'identity_type': str(type(user_identity))
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error getting user info: {str(e)}',
            'success': False
        }), 500

