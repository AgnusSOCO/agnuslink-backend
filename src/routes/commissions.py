from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import extract

from src.models.user import User, db
from src.models.commission import Commission
from src.models.lead import Lead

commissions_bp = Blueprint('commissions', __name__)

@commissions_bp.route('', methods=['GET'])
@jwt_required()
def get_commissions():
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status = request.args.get('status')
        commission_type = request.args.get('type')
        
        # Build query
        query = Commission.query.filter_by(affiliate_id=user_id)
        
        # Apply filters
        if status:
            query = query.filter(Commission.status == status)
        
        if commission_type:
            query = query.filter(Commission.commission_type == commission_type)
        
        # Order by creation date (newest first)
        query = query.order_by(Commission.created_at.desc())
        
        # Paginate
        total = query.count()
        commissions = query.offset((page - 1) * limit).limit(limit).all()
        
        # Get commission data with lead information
        commission_data = []
        for commission in commissions:
            commission_dict = commission.to_dict()
            # Add lead information
            lead = Lead.query.get(commission.lead_id)
            if lead:
                commission_dict['lead'] = {
                    'lead_id': lead.lead_id,
                    'full_name': lead.full_name,
                    'status': lead.status
                }
            commission_data.append(commission_dict)
        
        # Calculate totals
        total_earned = Commission.get_total_by_affiliate(user_id, 'paid')
        total_pending = Commission.get_total_by_affiliate(user_id, 'pending')
        total_approved = Commission.get_total_by_affiliate(user_id, 'approved')
        
        return jsonify({
            'success': True,
            'commissions': commission_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit,
                'has_next': page * limit < total,
                'has_prev': page > 1
            },
            'totals': {
                'total_earned': total_earned,
                'total_pending': total_pending,
                'total_approved': total_approved
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching commissions'
            }
        }), 500

@commissions_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_commission_stats():
    try:
        user_id = get_jwt_identity()
        
        # Get total commissions
        total_earned = Commission.get_total_by_affiliate(user_id, 'paid')
        total_pending = Commission.get_total_by_affiliate(user_id, 'pending')
        total_approved = Commission.get_total_by_affiliate(user_id, 'approved')
        
        # Get monthly earnings for current and previous month
        current_date = datetime.now()
        current_month_earnings = Commission.get_monthly_earnings(
            user_id, current_date.year, current_date.month
        )
        
        # Previous month
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year
        
        previous_month_earnings = Commission.get_monthly_earnings(
            user_id, prev_year, prev_month
        )
        
        # Get commission breakdown by type
        primary_commissions = Commission.query.filter_by(
            affiliate_id=user_id,
            commission_type='primary',
            status='paid'
        ).count()
        
        referral_commissions = Commission.query.filter_by(
            affiliate_id=user_id,
            commission_type='referral',
            status='paid'
        ).count()
        
        # Get recent commissions (last 5)
        recent_commissions = Commission.query.filter_by(affiliate_id=user_id).order_by(
            Commission.created_at.desc()
        ).limit(5).all()
        
        recent_commission_data = []
        for commission in recent_commissions:
            commission_dict = commission.to_dict()
            lead = Lead.query.get(commission.lead_id)
            if lead:
                commission_dict['lead'] = {
                    'lead_id': lead.lead_id,
                    'full_name': lead.full_name
                }
            recent_commission_data.append(commission_dict)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_earned': total_earned,
                'total_pending': total_pending,
                'total_approved': total_approved,
                'current_month_earnings': current_month_earnings,
                'previous_month_earnings': previous_month_earnings,
                'commission_breakdown': {
                    'primary': primary_commissions,
                    'referral': referral_commissions
                },
                'recent_commissions': recent_commission_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching commission statistics'
            }
        }), 500

@commissions_bp.route('/payout-request', methods=['POST'])
@jwt_required()
def request_payout():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('amount') or not data.get('payment_method'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Amount and payment method are required'
                }
            }), 400
        
        amount = float(data['amount'])
        payment_method = data['payment_method']
        payment_details = data.get('payment_details', {})
        
        # Validate amount
        if amount <= 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_AMOUNT',
                    'message': 'Amount must be greater than 0'
                }
            }), 400
        
        # Check available balance (approved commissions)
        available_balance = Commission.get_total_by_affiliate(user_id, 'approved')
        
        if amount > available_balance:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INSUFFICIENT_BALANCE',
                    'message': f'Insufficient balance. Available: ${available_balance:.2f}'
                }
            }), 400
        
        # Validate payment method
        valid_payment_methods = ['paypal', 'bank_transfer']
        if payment_method not in valid_payment_methods:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PAYMENT_METHOD',
                    'message': 'Invalid payment method'
                }
            }), 400
        
        # Get user's payment information
        user = User.query.get(user_id)
        if payment_method == 'paypal' and not user.paypal_email:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_PAYMENT_INFO',
                    'message': 'PayPal email not configured in profile'
                }
            }), 400
        
        if payment_method == 'bank_transfer' and not user.bank_account_number:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_PAYMENT_INFO',
                    'message': 'Bank account information not configured in profile'
                }
            }), 400
        
        # TODO: Create payout request record
        # For now, we'll mark the commissions as payout requested
        approved_commissions = Commission.query.filter_by(
            affiliate_id=user_id,
            status='approved'
        ).order_by(Commission.created_at.asc()).all()
        
        remaining_amount = amount
        updated_commissions = []
        
        for commission in approved_commissions:
            if remaining_amount <= 0:
                break
            
            if commission.amount <= remaining_amount:
                commission.payout_requested_at = datetime.utcnow()
                updated_commissions.append(commission)
                remaining_amount -= commission.amount
            else:
                # Partial payout - would need to split commission record
                # For simplicity, we'll skip partial payouts in this implementation
                break
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payout request submitted successfully',
            'payout_request': {
                'amount': amount,
                'payment_method': payment_method,
                'commissions_count': len(updated_commissions),
                'requested_at': datetime.utcnow().isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while processing payout request'
            }
        }), 500

@commissions_bp.route('/payout-requests', methods=['GET'])
@jwt_required()
def get_payout_requests():
    try:
        user_id = get_jwt_identity()
        
        # Get commissions with payout requests
        payout_commissions = Commission.query.filter(
            Commission.affiliate_id == user_id,
            Commission.payout_requested_at.isnot(None)
        ).order_by(Commission.payout_requested_at.desc()).all()
        
        # Group by payout request date (simplified grouping)
        payout_requests = []
        current_group = None
        current_date = None
        
        for commission in payout_commissions:
            request_date = commission.payout_requested_at.date()
            
            if current_date != request_date:
                if current_group:
                    payout_requests.append(current_group)
                
                current_group = {
                    'requested_at': commission.payout_requested_at.isoformat(),
                    'status': commission.status,
                    'total_amount': 0,
                    'commissions': []
                }
                current_date = request_date
            
            current_group['total_amount'] += float(commission.amount)
            current_group['commissions'].append(commission.to_dict())
        
        if current_group:
            payout_requests.append(current_group)
        
        return jsonify({
            'success': True,
            'payout_requests': payout_requests
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching payout requests'
            }
        }), 500

