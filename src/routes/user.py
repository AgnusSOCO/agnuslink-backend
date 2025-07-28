from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models.user import User, db
from src.models.lead import Lead
from src.models.commission import Commission

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
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
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching profile'
            }
        }), 500

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
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
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = [
            'first_name', 'last_name', 'phone', 'paypal_email',
            'bank_account_number', 'bank_routing_number', 'bank_account_holder_name'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field].strip() if data[field] else None)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while updating profile'
            }
        }), 500

@user_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
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
        
        # Get lead statistics
        total_leads = Lead.query.filter_by(submitted_by_id=user_id).count()
        
        # Get commission statistics
        total_commission = user.get_total_commission()
        pending_commission = user.get_pending_commission()
        
        # Get referral statistics
        active_affiliates = user.get_referral_count()
        
        # Get recent leads (last 5)
        recent_leads = Lead.query.filter_by(submitted_by_id=user_id).order_by(
            Lead.created_at.desc()
        ).limit(5).all()
        
        # Get commission breakdown
        from sqlalchemy import extract
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Previous month
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year
        
        this_month_commission = Commission.get_monthly_earnings(user_id, current_year, current_month)
        last_month_commission = Commission.get_monthly_earnings(user_id, prev_year, prev_month)
        
        return jsonify({
            'success': True,
            'dashboard': {
                'total_leads': total_leads,
                'total_commission': total_commission,
                'active_affiliates': active_affiliates,
                'pending_payouts': pending_commission,
                'recent_leads': [lead.to_dict() for lead in recent_leads],
                'commission_breakdown': {
                    'this_month': this_month_commission,
                    'last_month': last_month_commission
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching dashboard data'
            }
        }), 500

@user_bp.route('/referrals/tree', methods=['GET'])
@jwt_required()
def get_referral_tree():
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
        
        def build_tree(user, max_depth=2, current_depth=0):
            """Build referral tree for user"""
            if current_depth >= max_depth:
                return None
            
            user_data = {
                'id': user.id,
                'name': user.get_full_name(),
                'referral_code': user.referral_code,
                'total_leads': len(user.leads_submitted),
                'total_earnings': user.get_total_commission(),
                'joined_date': user.created_at.isoformat() if user.created_at else None,
                'children': []
            }
            
            # Get direct referrals
            for referral in user.referrals:
                child_tree = build_tree(referral, max_depth, current_depth + 1)
                if child_tree:
                    user_data['children'].append(child_tree)
            
            return user_data
        
        tree = build_tree(user)
        
        return jsonify({
            'success': True,
            'tree': tree
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while building referral tree'
            }
        }), 500

@user_bp.route('/referrals/stats', methods=['GET'])
@jwt_required()
def get_referral_stats():
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
        
        # Get direct referrals
        direct_referrals = len(user.referrals)
        
        # Get active referrals (those who have submitted leads)
        active_referrals = 0
        for referral in user.referrals:
            if len(referral.leads_submitted) > 0:
                active_referrals += 1
        
        # Get total commission from referrals
        referral_commissions = Commission.query.filter_by(
            affiliate_id=user_id,
            commission_type='referral',
            status='paid'
        ).all()
        
        total_referral_commission = sum(float(comm.amount) for comm in referral_commissions)
        
        # Get level breakdown (simplified to 2 levels)
        level_1_count = direct_referrals
        level_2_count = 0
        for referral in user.referrals:
            level_2_count += len(referral.referrals)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_referrals': direct_referrals,
                'active_referrals': active_referrals,
                'total_commission_from_referrals': total_referral_commission,
                'levels': {
                    'level_1': level_1_count,
                    'level_2': level_2_count
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching referral statistics'
            }
        }), 500

@user_bp.route('/upload-id', methods=['POST'])
@jwt_required()
def upload_government_id():
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
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': 'No file uploaded'
                }
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': 'No file selected'
                }
            }), 400
        
        # TODO: Implement file upload to storage service
        # For now, we'll just simulate the upload
        filename = f"id_{user_id}_{file.filename}"
        id_url = f"/uploads/ids/{filename}"
        
        # Update user with ID URL
        user.government_id_url = id_url
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Government ID uploaded successfully',
            'id_url': id_url
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while uploading ID'
            }
        }), 500
