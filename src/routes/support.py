from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models.user import User, db
from src.models.support import SupportTicket, SupportMessage

support_bp = Blueprint('support', __name__)

@support_bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_ticket():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['subject', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'{field} is required'
                    }
                }), 400
        
        subject = data['subject'].strip()
        message = data['message'].strip()
        priority = data.get('priority', 'medium')
        
        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if priority not in valid_priorities:
            priority = 'medium'
        
        # Create new ticket
        new_ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            message=message,
            priority=priority
        )
        
        db.session.add(new_ticket)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Support ticket created successfully',
            'ticket': new_ticket.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while creating the ticket'
            }
        }), 500

@support_bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_tickets():
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status = request.args.get('status')
        
        # Build query
        query = SupportTicket.query.filter_by(user_id=user_id)
        
        # Apply filters
        if status:
            query = query.filter(SupportTicket.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(SupportTicket.created_at.desc())
        
        # Paginate
        total = query.count()
        tickets = query.offset((page - 1) * limit).limit(limit).all()
        
        return jsonify({
            'success': True,
            'tickets': [ticket.to_dict() for ticket in tickets],
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
                'message': 'An error occurred while fetching tickets'
            }
        }), 500

@support_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    try:
        user_id = get_jwt_identity()
        
        # Find ticket
        ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=user_id).first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TICKET_NOT_FOUND',
                    'message': 'Ticket not found'
                }
            }), 404
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict(include_messages=True)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching the ticket'
            }
        }), 500

@support_bp.route('/tickets/<int:ticket_id>/messages', methods=['POST'])
@jwt_required()
def add_message_to_ticket(ticket_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('message'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Message is required'
                }
            }), 400
        
        # Find ticket
        ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=user_id).first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TICKET_NOT_FOUND',
                    'message': 'Ticket not found'
                }
            }), 404
        
        # Check if ticket is closed
        if ticket.status == 'closed':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TICKET_CLOSED',
                    'message': 'Cannot add messages to a closed ticket'
                }
            }), 400
        
        message = data['message'].strip()
        attachment_url = data.get('attachment_url')
        
        # Add message to ticket
        support_message = ticket.add_message(
            user_id=user_id,
            message=message,
            attachment_url=attachment_url
        )
        
        # If ticket was resolved, reopen it
        if ticket.status == 'resolved':
            ticket.update_status('open')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Message added successfully',
            'support_message': support_message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while adding the message'
            }
        }), 500

@support_bp.route('/tickets/<int:ticket_id>/close', methods=['POST'])
@jwt_required()
def close_ticket(ticket_id):
    try:
        user_id = get_jwt_identity()
        
        # Find ticket
        ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=user_id).first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TICKET_NOT_FOUND',
                    'message': 'Ticket not found'
                }
            }), 404
        
        # Update ticket status
        ticket.update_status('closed')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ticket closed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while closing the ticket'
            }
        }), 500

@support_bp.route('/tickets/stats', methods=['GET'])
@jwt_required()
def get_ticket_stats():
    try:
        user_id = get_jwt_identity()
        
        # Get total tickets count
        total_tickets = SupportTicket.query.filter_by(user_id=user_id).count()
        
        # Get tickets by status
        status_counts = {}
        statuses = ['open', 'in_progress', 'resolved', 'closed']
        for status in statuses:
            count = SupportTicket.query.filter_by(user_id=user_id, status=status).count()
            status_counts[status] = count
        
        # Get recent tickets (last 5)
        recent_tickets = SupportTicket.query.filter_by(user_id=user_id).order_by(
            SupportTicket.created_at.desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tickets': total_tickets,
                'status_breakdown': status_counts,
                'recent_tickets': [ticket.to_dict() for ticket in recent_tickets]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while fetching ticket statistics'
            }
        }), 500

