from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime

# Create onboarding blueprint with lazy imports
onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Get user's onboarding status and next steps"""
    try:
        # Lazy imports to avoid circular import issues
        from database import db
        from models.user import User
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Basic onboarding status logic
        current_step = 'welcome'
        progress = 0
        
        # Determine progress based on user attributes
        if hasattr(user, 'agreement_signed') and user.agreement_signed:
            current_step = 'kyc_upload'
            progress = 40
        elif hasattr(user, 'kyc_verified') and user.kyc_verified:
            current_step = 'complete'
            progress = 100
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
            'onboarding_complete': getattr(user, 'onboarding_complete', False),
            'kyc_verified': getattr(user, 'kyc_verified', False),
            'agreement_signed': getattr(user, 'agreement_signed', False),
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'import_status': 'user_model_imported'
        })
        
    except ImportError as e:
        return jsonify({
            'error': f'Import error: {str(e)}',
            'success': False
        }), 500
    except Exception as e:
        return jsonify({
            'error': f'Error: {str(e)}',
            'success': False
        }), 500

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Onboarding routes with User model import are working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'routes_available': [
            '/status (requires JWT)',
            '/test',
            '/health'
        ],
        'blueprint_name': 'onboarding',
        'import_status': 'database_and_user_model_imported',
        'features': [
            'JWT authentication',
            'User model access',
            'Basic onboarding logic'
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
    """Get current user information"""
    try:
        from database import db
        from models.user import User
        
        user_id = get_jwt_identity()
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
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error getting user info: {str(e)}',
            'success': False
        }), 500

