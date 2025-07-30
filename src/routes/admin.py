from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime, timedelta

# Create blueprint
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

def is_admin_user(user_id):
    """Check if user has admin privileges"""
    try:
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        return user and getattr(user, 'is_admin', False)
    except:
        return False

@admin_bp.route('/pending-onboarding', methods=['GET'])
@jwt_required()
def get_pending_onboarding():
    """Get list of users who completed onboarding but need agreements sent"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        # Check admin privileges
        if not is_admin_user(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        from src.database import db
        from src.models.user import User
        
        # Get users who completed onboarding but haven't signed agreements
        pending_users = User.query.filter(
            User.onboarding_completed == True,
            User.agreement_signed != True
        ).all()
        
        pending_list = []
        for user in pending_users:
            pending_list.append({
                'id': user.id,
                'email': user.email,
                'first_name': getattr(user, 'first_name', ''),
                'last_name': getattr(user, 'last_name', ''),
                'phone': getattr(user, 'phone', ''),
                'onboarding_completion_date': getattr(user, 'onboarding_completion_date', None),
                'status': getattr(user, 'status', 'active'),
                'kyc_submitted': getattr(user, 'kyc_submitted', False),
                'kyc_verified': getattr(user, 'kyc_verified', False),
                'days_since_completion': (
                    (datetime.now() - user.onboarding_completion_date).days 
                    if getattr(user, 'onboarding_completion_date', None) else 0
                )
            })
        
        return jsonify({
            'success': True,
            'pending_users': pending_list,
            'total_count': len(pending_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending onboarding: {str(e)}")
        return jsonify({'error': f'Failed to get pending onboarding: {str(e)}'}), 500

@admin_bp.route('/mark-agreement-sent/<int:user_id>', methods=['POST'])
@jwt_required()
def mark_agreement_sent(user_id):
    """Mark that agreement has been sent to user"""
    try:
        admin_identity = get_jwt_identity()
        admin_user_id = int(admin_identity)
        
        # Check admin privileges
        if not is_admin_user(admin_user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user status
        user.agreement_sent = True
        user.agreement_sent_date = datetime.now()
        user.status = 'agreement_sent'
        
        db.session.commit()
        
        logger.info(f"Agreement marked as sent for user {user_id} by admin {admin_user_id}")
        return jsonify({
            'success': True,
            'message': f'Agreement marked as sent for {user.email}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking agreement sent: {str(e)}")
        return jsonify({'error': f'Failed to mark agreement sent: {str(e)}'}), 500

@admin_bp.route('/mark-agreement-signed/<int:user_id>', methods=['POST'])
@jwt_required()
def mark_agreement_signed(user_id):
    """Mark that user has signed the agreement"""
    try:
        admin_identity = get_jwt_identity()
        admin_user_id = int(admin_identity)
        
        # Check admin privileges
        if not is_admin_user(admin_user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user status
        user.agreement_signed = True
        user.agreement_signed_date = datetime.now()
        user.status = 'active'  # Fully active user
        
        db.session.commit()
        
        logger.info(f"Agreement marked as signed for user {user_id} by admin {admin_user_id}")
        return jsonify({
            'success': True,
            'message': f'Agreement marked as signed for {user.email}. User is now fully active.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking agreement signed: {str(e)}")
        return jsonify({'error': f'Failed to mark agreement signed: {str(e)}'}), 500

@admin_bp.route('/onboarding-stats', methods=['GET'])
@jwt_required()
def get_onboarding_stats():
    """Get onboarding statistics for admin dashboard"""
    try:
        user_identity = get_jwt_identity()
        user_id = int(user_identity)
        
        # Check admin privileges
        if not is_admin_user(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        from src.database import db
        from src.models.user import User
        
        # Calculate various statistics
        total_users = User.query.count()
        
        completed_onboarding = User.query.filter(
            User.onboarding_completed == True
        ).count()
        
        pending_agreements = User.query.filter(
            User.onboarding_completed == True,
            User.agreement_signed != True
        ).count()
        
        fully_active = User.query.filter(
            User.agreement_signed == True
        ).count()
        
        # Recent completions (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_completions = User.query.filter(
            User.onboarding_completion_date >= week_ago
        ).count()
        
        stats = {
            'total_users': total_users,
            'completed_onboarding': completed_onboarding,
            'pending_agreements': pending_agreements,
            'fully_active_users': fully_active,
            'recent_completions_7_days': recent_completions,
            'completion_rate': (completed_onboarding / total_users * 100) if total_users > 0 else 0,
            'activation_rate': (fully_active / total_users * 100) if total_users > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting onboarding stats: {str(e)}")
        return jsonify({'error': f'Failed to get onboarding stats: {str(e)}'}), 500

@admin_bp.route('/user-details/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_details(user_id):
    """Get detailed information about a specific user"""
    try:
        admin_identity = get_jwt_identity()
        admin_user_id = int(admin_identity)
        
        # Check admin privileges
        if not is_admin_user(admin_user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_details = {
            'id': user.id,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'phone': getattr(user, 'phone', ''),
            'address': getattr(user, 'address', ''),
            'city': getattr(user, 'city', ''),
            'state': getattr(user, 'state', ''),
            'zip_code': getattr(user, 'zip_code', ''),
            'created_at': user.created_at,
            'status': getattr(user, 'status', 'active'),
            'onboarding_completed': getattr(user, 'onboarding_completed', False),
            'onboarding_completion_date': getattr(user, 'onboarding_completion_date', None),
            'kyc_submitted': getattr(user, 'kyc_submitted', False),
            'kyc_verified': getattr(user, 'kyc_verified', False),
            'kyc_document_type': getattr(user, 'kyc_document_type', ''),
            'agreement_sent': getattr(user, 'agreement_sent', False),
            'agreement_sent_date': getattr(user, 'agreement_sent_date', None),
            'agreement_signed': getattr(user, 'agreement_signed', False),
            'agreement_signed_date': getattr(user, 'agreement_signed_date', None),
            'referral_code': getattr(user, 'referral_code', ''),
            'referred_by': getattr(user, 'referred_by', None)
        }
        
        return jsonify({
            'success': True,
            'user': user_details
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        return jsonify({'error': f'Failed to get user details: {str(e)}'}), 500

@admin_bp.route('/send-notification', methods=['POST'])
@jwt_required()
def send_team_notification():
    """Send notification to team about new onboarding completion"""
    try:
        admin_identity = get_jwt_identity()
        admin_user_id = int(admin_identity)
        
        # Check admin privileges
        if not is_admin_user(admin_user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        user_id = data.get('user_id')
        notification_type = data.get('type', 'onboarding_completed')
        
        from src.database import db
        from src.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Here you would integrate with your notification system
        # Examples: Email, Slack, Discord, SMS, etc.
        
        # For now, just log the notification
        logger.info(f"Team notification: {notification_type} for user {user.email}")
        
        # You could add notification tracking to database here
        
        return jsonify({
            'success': True,
            'message': f'Notification sent for {user.email}',
            'notification_type': notification_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return jsonify({'error': f'Failed to send notification: {str(e)}'}), 500

