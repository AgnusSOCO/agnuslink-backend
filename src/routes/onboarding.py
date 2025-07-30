from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

# Create blueprint
onboarding_bp = Blueprint('onboarding', __name__)
logger = logging.getLogger(__name__)

@onboarding_bp.route('/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Get current user's onboarding status"""
    try:
        # Get user identity from JWT token
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        # Import inside function to avoid circular imports
        from src.database import db
        from src.models.user import User
        
        # Get user from database
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine onboarding progress
        onboarding_status = {
            'user_id': user.id,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'current_step': 1,
            'total_steps': 3,
            'steps': {
                'personal_info': {
                    'completed': bool(getattr(user, 'first_name', None) and getattr(user, 'last_name', None)),
                    'step_number': 1,
                    'title': 'Personal Information',
                    'description': 'Complete your profile information'
                },
                'kyc_upload': {
                    'completed': getattr(user, 'kyc_verified', False),
                    'step_number': 2,
                    'title': 'Identity Verification',
                    'description': 'Upload your identification documents'
                },
                'agreement_pending': {
                    'completed': getattr(user, 'agreement_signed', False),
                    'step_number': 3,
                    'title': 'Agreement Signing',
                    'description': 'Our team will send you the agreement to sign'
                }
            },
            'is_complete': getattr(user, 'agreement_signed', False),
            'agreement_status': 'pending_team_action' if not getattr(user, 'agreement_signed', False) else 'completed'
        }
        
        # Calculate current step
        if not onboarding_status['steps']['personal_info']['completed']:
            onboarding_status['current_step'] = 1
        elif not onboarding_status['steps']['kyc_upload']['completed']:
            onboarding_status['current_step'] = 2
        else:
            onboarding_status['current_step'] = 3
        
        return jsonify(onboarding_status), 200
        
    except Exception as e:
        logger.error(f"Error getting onboarding status: {str(e)}")
        return jsonify({'error': f'Failed to get onboarding status: {str(e)}'}), 500

@onboarding_bp.route('/update-personal-info', methods=['POST'])
@jwt_required()
def update_personal_info():
    """Update user's personal information"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update user information
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'address' in data:
            user.address = data['address']
        if 'city' in data:
            user.city = data['city']
        if 'state' in data:
            user.state = data['state']
        if 'zip_code' in data:
            user.zip_code = data['zip_code']
        
        db.session.commit()
        
        logger.info(f"Personal info updated for user {user_id}")
        return jsonify({
            'success': True,
            'message': 'Personal information updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating personal info: {str(e)}")
        return jsonify({'error': f'Failed to update personal info: {str(e)}'}), 500

@onboarding_bp.route('/upload-kyc', methods=['POST'])
@jwt_required()
def upload_kyc_document():
    """Handle KYC document upload"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # For now, just mark KYC as submitted (manual review process)
        # In a real implementation, you would handle file uploads here
        
        data = request.get_json()
        document_type = data.get('document_type', 'drivers_license')
        
        # Mark KYC as submitted for manual review
        user.kyc_submitted = True
        user.kyc_document_type = document_type
        user.kyc_submission_date = db.func.now()
        
        db.session.commit()
        
        logger.info(f"KYC document submitted for user {user_id}")
        return jsonify({
            'success': True,
            'message': 'KYC document submitted successfully. Our team will review it shortly.',
            'status': 'submitted_for_review'
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading KYC: {str(e)}")
        return jsonify({'error': f'Failed to upload KYC: {str(e)}'}), 500

@onboarding_bp.route('/complete-onboarding', methods=['POST'])
@jwt_required()
def complete_onboarding():
    """Mark onboarding as complete and notify team"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has completed required steps
        if not (getattr(user, 'first_name', None) and getattr(user, 'last_name', None)):
            return jsonify({'error': 'Personal information not complete'}), 400
        
        if not getattr(user, 'kyc_submitted', False):
            return jsonify({'error': 'KYC documents not submitted'}), 400
        
        # Mark onboarding as complete
        user.onboarding_completed = True
        user.onboarding_completion_date = db.func.now()
        user.status = 'pending_agreement'  # Status indicating team needs to send agreement
        
        db.session.commit()
        
        # TODO: Send notification to team (email, Slack, etc.)
        # This is where you would integrate with your team notification system
        
        logger.info(f"Onboarding completed for user {user_id} - {user.email}")
        return jsonify({
            'success': True,
            'message': 'Onboarding completed! Our team will send you the agreement to sign shortly.',
            'status': 'completed',
            'next_step': 'wait_for_agreement'
        }), 200
        
    except Exception as e:
        logger.error(f"Error completing onboarding: {str(e)}")
        return jsonify({'error': f'Failed to complete onboarding: {str(e)}'}), 500

@onboarding_bp.route('/user-info', methods=['GET'])
@jwt_required()
def get_user_info():
    """Get current user information"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_info = {
            'id': user.id,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'phone': getattr(user, 'phone', ''),
            'address': getattr(user, 'address', ''),
            'city': getattr(user, 'city', ''),
            'state': getattr(user, 'state', ''),
            'zip_code': getattr(user, 'zip_code', ''),
            'kyc_submitted': getattr(user, 'kyc_submitted', False),
            'kyc_verified': getattr(user, 'kyc_verified', False),
            'onboarding_completed': getattr(user, 'onboarding_completed', False),
            'agreement_signed': getattr(user, 'agreement_signed', False),
            'status': getattr(user, 'status', 'active')
        }
        
        return jsonify(user_info), 200
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return jsonify({'error': f'Failed to get user info: {str(e)}'}), 500

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Onboarding routes are working!',
        'version': 'manual_process_v1.0',
        'endpoints': [
            '/api/onboarding/status',
            '/api/onboarding/update-personal-info',
            '/api/onboarding/upload-kyc',
            '/api/onboarding/complete-onboarding',
            '/api/onboarding/user-info',
            '/api/onboarding/test'
        ]
    }), 200

