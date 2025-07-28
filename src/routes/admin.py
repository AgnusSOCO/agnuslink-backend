from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import or_, and_, extract
from functools import wraps

from src.models.user import User, db
from src.models.lead import Lead
from src.models.commission import Commission
from src.models.support import SupportTicket, SupportMessage

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ADMIN_REQUIRED',
                    'message': 'Admin access required'
                }
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/leads', methods=['GET'])
@admin_required
def get_all_leads():
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status = request.args.get('status')
        search = request.args.get('search')
        affiliate_id = request.args.get('affiliate_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query
        query = Lead.query
        
        # Apply filters
        if status:
            query = query.filter(Lead.status == status)
        
        if affiliate_id:
            query = query.filter(Lead.submitted_by_id == affiliate_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Lead.full_name.ilike(search_term),
                    Lead.email.ilike(search_term),
                    Lead.phone.ilike(search_term),
                    Lead.lead_id.ilike(search_term)
                )
            )
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Lead.created_at >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                query = query.filter(Lead.created_at <= to_date)
            except ValueError:
                pass
        
        # Order by creation date (newest first)
        query = query.order_by(Lead.created_at.desc())
        
        # Paginate
        total = query.count()
        leads = query.offset((page - 1) * limit).limit(limit).all()
        
        # Add affiliate information to leads
        leads_data = []
        for lead in leads:
            lead_dict = lead.to_dict(include_admin_notes=True)
            lead_dict['submitted_by_name'] = lead.submitted_by.get_full_name()
            if lead.secondary_referrer:
                lead_dict['secondary_referrer_name'] = lead.secondary_referrer.get_full_name()
            leads_data.append(lead_dict)
        
        return jsonify({
            'success': True,
            'leads': leads_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit,
                'has_next': page * limit < total,
                'has_prev': page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching leads'
            }
        }), 500

@admin_bp.route('/leads/<int:lead_id>/status', methods=['PUT'])
@admin_required
def update_lead_status(lead_id):
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('status'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Status is required'
                }
            }), 400
        
        new_status = data['status']
        admin_notes = data.get('admin_notes', '')
        
        # Validate status
        valid_statuses = ['submitted', 'in_review', 'qualified', 'sold', 'unqualified']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STATUS',
                    'message': 'Invalid status'
                }
            }), 400
        
        # Find lead
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Update lead status
        lead.update_status(new_status, admin_notes)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lead status updated successfully',
            'lead': lead.to_dict(include_admin_notes=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while updating lead status'
            }
        }), 500

@admin_bp.route('/leads/<int:lead_id>/convert', methods=['POST'])
@admin_required
def convert_lead(lead_id):
    try:
        data = request.get_json()
        deal_value = data.get('deal_value', 1000.00)  # Default deal value
        
        # Find lead
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Check if lead can be converted
        if lead.status == 'sold':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ALREADY_CONVERTED',
                    'message': 'Lead is already converted'
                }
            }), 400
        
        # Update lead status to sold and calculate commissions
        lead.update_status('sold')
        
        # The commission calculation is handled in the Lead model
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lead converted successfully and commissions calculated',
            'lead': lead.to_dict(include_admin_notes=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while converting the lead'
            }
        }), 500

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        role = request.args.get('role')
        search = request.args.get('search')
        
        # Build query
        query = User.query
        
        # Apply filters
        if role:
            query = query.filter(User.role == role)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        total = query.count()
        users = query.offset((page - 1) * limit).limit(limit).all()
        
        # Add statistics to user data
        users_data = []
        for user in users:
            user_dict = user.to_dict()
            user_dict.update({
                'total_leads': len(user.leads_submitted),
                'total_commission': user.get_total_commission(),
                'pending_commission': user.get_pending_commission(),
                'referral_count': user.get_referral_count()
            })
            users_data.append(user_dict)
        
        return jsonify({
            'success': True,
            'users': users_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit,
                'has_next': page * limit < total,
                'has_prev': page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching users'
            }
        }), 500

@admin_bp.route('/users/<int:user_id>/tree', methods=['GET'])
@admin_required
def get_user_tree(user_id):
    try:
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
        
        def build_tree(user, max_depth=3, current_depth=0):
            """Recursively build referral tree"""
            if current_depth >= max_depth:
                return None
            
            user_data = {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'referral_code': user.referral_code,
                'total_leads': len(user.leads_submitted),
                'total_commission': user.get_total_commission(),
                'created_at': user.created_at.isoformat() if user.created_at else None,
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
                'message': 'An error occurred while building user tree'
            }
        }), 500

@admin_bp.route('/commissions/manual', methods=['POST'])
@admin_required
def create_manual_commission():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'amount', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'{field} is required'
                    }
                }), 400
        
        user_id = data['user_id']
        amount = float(data['amount'])
        description = data['description']
        commission_type = data.get('commission_type', 'bonus')
        
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        # Validate amount
        if amount <= 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_AMOUNT',
                    'message': 'Amount must be greater than 0'
                }
            }), 400
        
        # Create manual commission
        manual_commission = Commission(
            lead_id=None,  # No associated lead for manual commissions
            affiliate_id=user_id,
            commission_type=commission_type,
            percentage=0,  # Not applicable for manual commissions
            amount=amount,
            status='approved'  # Manual commissions are pre-approved
        )
        
        db.session.add(manual_commission)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Manual commission created successfully',
            'commission': manual_commission.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while creating manual commission'
            }
        }), 500

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    try:
        # Get overview statistics
        total_users = User.query.filter_by(role='affiliate').count()
        total_leads = Lead.query.count()
        total_commissions_paid = db.session.query(db.func.sum(Commission.amount)).filter_by(status='paid').scalar() or 0
        pending_commissions = db.session.query(db.func.sum(Commission.amount)).filter_by(status='pending').scalar() or 0
        
        # Get leads by status
        lead_status_counts = {}
        statuses = ['submitted', 'in_review', 'qualified', 'sold', 'unqualified']
        for status in statuses:
            count = Lead.query.filter_by(status=status).count()
            lead_status_counts[status] = count
        
        # Get recent activity (last 10 leads)
        recent_leads = Lead.query.order_by(Lead.created_at.desc()).limit(10).all()
        recent_leads_data = []
        for lead in recent_leads:
            lead_dict = lead.to_dict()
            lead_dict['submitted_by_name'] = lead.submitted_by.get_full_name()
            recent_leads_data.append(lead_dict)
        
        # Get monthly statistics
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_leads = Lead.query.filter(
            extract('month', Lead.created_at) == current_month,
            extract('year', Lead.created_at) == current_year
        ).count()
        
        monthly_conversions = Lead.query.filter(
            Lead.status == 'sold',
            extract('month', Lead.converted_at) == current_month,
            extract('year', Lead.converted_at) == current_year
        ).count()
        
        return jsonify({
            'success': True,
            'dashboard': {
                'overview': {
                    'total_users': total_users,
                    'total_leads': total_leads,
                    'total_commissions_paid': float(total_commissions_paid),
                    'pending_commissions': float(pending_commissions),
                    'monthly_leads': monthly_leads,
                    'monthly_conversions': monthly_conversions
                },
                'lead_status_breakdown': lead_status_counts,
                'recent_leads': recent_leads_data
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

