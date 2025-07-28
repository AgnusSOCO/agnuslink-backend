from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import or_, and_

from src.models.user import User, db
from src.models.lead import Lead

leads_bp = Blueprint('leads', __name__)

@leads_bp.route('', methods=['POST'])
@jwt_required()
def create_lead():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'{field} is required'
                    }
                }), 400
        
        # Validate secondary referrer if provided
        secondary_referrer_id = data.get('secondary_referrer_id')
        if secondary_referrer_id:
            secondary_referrer = User.query.get(secondary_referrer_id)
            if not secondary_referrer:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REFERRER',
                        'message': 'Invalid secondary referrer'
                    }
                }), 400
        
        # Create new lead
        new_lead = Lead(
            full_name=data['full_name'].strip(),
            email=data.get('email', '').strip() if data.get('email') else None,
            phone=data.get('phone', '').strip() if data.get('phone') else None,
            location_city=data.get('location_city', '').strip() if data.get('location_city') else None,
            location_state=data.get('location_state', '').strip() if data.get('location_state') else None,
            industry=data.get('industry', '').strip() if data.get('industry') else None,
            notes=data.get('notes', '').strip() if data.get('notes') else None,
            submitted_by_id=user_id,
            secondary_referrer_id=secondary_referrer_id
        )
        
        db.session.add(new_lead)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lead submitted successfully',
            'lead': new_lead.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while creating the lead'
            }
        }), 500

@leads_bp.route('', methods=['GET'])
@jwt_required()
def get_leads():
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)  # Max 100 items per page
        status = request.args.get('status')
        search = request.args.get('search')
        
        # Build query
        query = Lead.query.filter_by(submitted_by_id=user_id)
        
        # Apply filters
        if status:
            query = query.filter(Lead.status == status)
        
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
        
        # Order by creation date (newest first)
        query = query.order_by(Lead.created_at.desc())
        
        # Paginate
        total = query.count()
        leads = query.offset((page - 1) * limit).limit(limit).all()
        
        return jsonify({
            'success': True,
            'leads': [lead.to_dict() for lead in leads],
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

@leads_bp.route('/<int:lead_id>', methods=['GET'])
@jwt_required()
def get_lead(lead_id):
    try:
        user_id = get_jwt_identity()
        
        # Find lead
        lead = Lead.query.filter_by(id=lead_id, submitted_by_id=user_id).first()
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        return jsonify({
            'success': True,
            'lead': lead.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching the lead'
            }
        }), 500

@leads_bp.route('/<int:lead_id>', methods=['PUT'])
@jwt_required()
def update_lead(lead_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Find lead
        lead = Lead.query.filter_by(id=lead_id, submitted_by_id=user_id).first()
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Check if lead can be updated (only if not converted)
        if lead.status in ['sold', 'unqualified']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_LOCKED',
                    'message': 'Cannot update lead that has been processed'
                }
            }), 400
        
        # Update allowed fields
        updatable_fields = ['full_name', 'email', 'phone', 'location_city', 'location_state', 'industry', 'notes']
        for field in updatable_fields:
            if field in data:
                setattr(lead, field, data[field].strip() if data[field] else None)
        
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lead updated successfully',
            'lead': lead.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while updating the lead'
            }
        }), 500

@leads_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_lead_stats():
    try:
        user_id = get_jwt_identity()
        
        # Get total leads count
        total_leads = Lead.query.filter_by(submitted_by_id=user_id).count()
        
        # Get leads by status
        status_counts = {}
        statuses = ['submitted', 'in_review', 'qualified', 'sold', 'unqualified']
        for status in statuses:
            count = Lead.query.filter_by(submitted_by_id=user_id, status=status).count()
            status_counts[status] = count
        
        # Get recent leads (last 5)
        recent_leads = Lead.query.filter_by(submitted_by_id=user_id).order_by(
            Lead.created_at.desc()
        ).limit(5).all()
        
        # Get monthly stats (current month)
        from sqlalchemy import extract
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_leads = Lead.query.filter(
            Lead.submitted_by_id == user_id,
            extract('month', Lead.created_at) == current_month,
            extract('year', Lead.created_at) == current_year
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_leads': total_leads,
                'status_breakdown': status_counts,
                'monthly_leads': monthly_leads,
                'recent_leads': [lead.to_dict() for lead in recent_leads]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching lead statistics'
            }
        }), 500

@leads_bp.route('/<int:lead_id>/upload', methods=['POST'])
@jwt_required()
def upload_lead_attachment(lead_id):
    try:
        user_id = get_jwt_identity()
        
        # Find lead
        lead = Lead.query.filter_by(id=lead_id, submitted_by_id=user_id).first()
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
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
        filename = f"lead_{lead_id}_{file.filename}"
        attachment_url = f"/uploads/leads/{filename}"
        
        # Update lead with attachment URL
        lead.attachment_url = attachment_url
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'attachment_url': attachment_url
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while uploading the file'
            }
        }), 500

