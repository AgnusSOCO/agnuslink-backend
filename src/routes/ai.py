from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from src.models.user import User, db
from src.models.lead import Lead
from src.models.commission import Commission
from src.services.ai_service import AIService

ai_bp = Blueprint('ai', __name__)
ai_service = AIService()

@ai_bp.route('/analyze-lead/<int:lead_id>', methods=['POST'])
@jwt_required()
def analyze_lead(lead_id):
    """
    Analyze a specific lead for quality and provide recommendations
    """
    try:
        user_id = get_jwt_identity()
        lead = Lead.query.get(lead_id)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Check if user owns this lead or is admin
        if lead.submitted_by_id != user_id:
            user = User.query.get(user_id)
            if not user or user.role != 'admin':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'You can only analyze your own leads'
                    }
                }), 403
        
        # Prepare lead data for AI analysis
        lead_data = {
            'full_name': lead.full_name,
            'email': lead.email,
            'phone': lead.phone,
            'address': lead.address,
            'city': lead.city,
            'state': lead.state,
            'lead_type': lead.lead_type,
            'notes': lead.notes
        }
        
        # Get AI analysis
        analysis = ai_service.score_lead_quality(lead_data)
        
        # Store analysis in lead record (you might want to create a separate table for this)
        lead.ai_score = analysis.get('score')
        lead.ai_quality_level = analysis.get('quality_level')
        lead.ai_analyzed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred during lead analysis'
            }
        }), 500

@ai_bp.route('/follow-up-suggestions/<int:lead_id>', methods=['GET'])
@jwt_required()
def get_follow_up_suggestions(lead_id):
    """
    Get AI-generated follow-up suggestions for a lead
    """
    try:
        user_id = get_jwt_identity()
        lead = Lead.query.get(lead_id)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Check if user owns this lead
        if lead.submitted_by_id != user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'You can only get suggestions for your own leads'
                }
            }), 403
        
        # Prepare lead data
        lead_data = {
            'lead_type': lead.lead_type,
            'city': lead.city,
            'state': lead.state,
            'notes': lead.notes
        }
        
        # Get AI suggestions
        suggestions = ai_service.generate_follow_up_suggestions(lead_data, lead.status)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'lead_id': lead_id,
            'generated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while generating suggestions'
            }
        }), 500

@ai_bp.route('/performance-analysis', methods=['GET'])
@jwt_required()
def analyze_performance():
    """
    Get AI analysis of affiliate performance
    """
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
        
        # Gather performance data
        leads = Lead.query.filter_by(submitted_by_id=user_id).all()
        commissions = Commission.query.filter_by(user_id=user_id).all()
        
        total_leads = len(leads)
        converted_leads = len([l for l in leads if l.status == 'sold'])
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        total_earnings = sum([float(c.amount) for c in commissions if c.status == 'paid'])
        
        # Calculate active days (days with lead submissions)
        lead_dates = [l.created_at.date() for l in leads if l.created_at]
        active_days = len(set(lead_dates))
        
        # Get lead types and locations
        lead_types = list(set([l.lead_type for l in leads if l.lead_type]))
        locations = list(set([f"{l.city}, {l.state}" for l in leads if l.city and l.state]))
        
        affiliate_data = {
            'total_leads': total_leads,
            'conversion_rate': round(conversion_rate, 2),
            'total_earnings': total_earnings,
            'active_days': active_days,
            'referral_count': len(user.referrals) if hasattr(user, 'referrals') else 0,
            'lead_types': lead_types,
            'locations': locations[:5]  # Top 5 locations
        }
        
        # Get AI analysis
        analysis = ai_service.analyze_affiliate_performance(affiliate_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'performance_data': affiliate_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred during performance analysis'
            }
        }), 500

@ai_bp.route('/generate-content', methods=['POST'])
@jwt_required()
def generate_marketing_content():
    """
    Generate AI marketing content for affiliates
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        content_type = data.get('content_type', 'social_media_post')
        target_audience = data.get('target_audience', 'homeowners')
        lead_type = data.get('lead_type', 'solar')
        
        # Validate inputs
        valid_content_types = ['social_media_post', 'email_template', 'blog_post', 'ad_copy']
        if content_type not in valid_content_types:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CONTENT_TYPE',
                    'message': f'Content type must be one of: {", ".join(valid_content_types)}'
                }
            }), 400
        
        # Generate content
        content = ai_service.generate_marketing_content(content_type, target_audience, lead_type)
        
        return jsonify({
            'success': True,
            'content': content,
            'content_type': content_type,
            'target_audience': target_audience,
            'lead_type': lead_type,
            'generated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while generating content'
            }
        }), 500

@ai_bp.route('/conversion-prediction/<int:lead_id>', methods=['GET'])
@jwt_required()
def predict_conversion(lead_id):
    """
    Predict when a lead is likely to convert
    """
    try:
        user_id = get_jwt_identity()
        lead = Lead.query.get(lead_id)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'LEAD_NOT_FOUND',
                    'message': 'Lead not found'
                }
            }), 404
        
        # Check if user owns this lead
        if lead.submitted_by_id != user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'You can only get predictions for your own leads'
                }
            }), 403
        
        # Get historical data for similar leads
        similar_leads = Lead.query.filter_by(
            submitted_by_id=user_id,
            lead_type=lead.lead_type
        ).filter(Lead.id != lead_id).all()
        
        # Prepare historical data
        historical_data = []
        for similar_lead in similar_leads:
            if similar_lead.status == 'sold' and similar_lead.created_at:
                # Calculate conversion time (simplified - you might want to track actual conversion date)
                conversion_days = (datetime.utcnow() - similar_lead.created_at).days
                historical_data.append({
                    'conversion_days': min(conversion_days, 30),  # Cap at 30 days
                    'converted': True
                })
            elif similar_lead.created_at and (datetime.utcnow() - similar_lead.created_at).days > 30:
                historical_data.append({
                    'conversion_days': 30,
                    'converted': False
                })
        
        # Prepare lead data
        lead_data = {
            'lead_type': lead.lead_type,
            'city': lead.city,
            'state': lead.state,
            'phone': lead.phone,
            'email': lead.email,
            'notes': lead.notes
        }
        
        # Get AI prediction
        prediction = ai_service.predict_lead_conversion_time(lead_data, historical_data)
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'historical_sample_size': len(historical_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while generating prediction'
            }
        }), 500

@ai_bp.route('/platform-insights', methods=['GET'])
@jwt_required()
def get_platform_insights():
    """
    Get AI-generated platform insights (admin only)
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Admin access required'
                }
            }), 403
        
        # Gather platform data
        total_affiliates = User.query.filter_by(role='affiliate').count()
        active_affiliates = User.query.join(Lead).filter(User.role == 'affiliate').distinct().count()
        total_leads = Lead.query.count()
        
        # Calculate conversion rate
        converted_leads = Lead.query.filter_by(status='sold').count()
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Calculate average lead value
        paid_commissions = Commission.query.filter_by(status='paid').all()
        avg_lead_value = sum([float(c.amount) for c in paid_commissions]) / len(paid_commissions) if paid_commissions else 0
        
        # Get top lead types
        from sqlalchemy import func
        top_lead_types = db.session.query(
            Lead.lead_type, 
            func.count(Lead.id).label('count')
        ).group_by(Lead.lead_type).order_by(func.count(Lead.id).desc()).limit(5).all()
        
        # Calculate growth rate (simplified - last 30 days vs previous 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        
        recent_leads = Lead.query.filter(Lead.created_at >= thirty_days_ago).count()
        previous_leads = Lead.query.filter(
            Lead.created_at >= sixty_days_ago,
            Lead.created_at < thirty_days_ago
        ).count()
        
        growth_rate = ((recent_leads - previous_leads) / previous_leads * 100) if previous_leads > 0 else 0
        
        platform_data = {
            'total_affiliates': total_affiliates,
            'active_affiliates': active_affiliates,
            'total_leads': total_leads,
            'conversion_rate': round(conversion_rate, 2),
            'avg_lead_value': round(avg_lead_value, 2),
            'top_lead_types': [lt[0] for lt in top_lead_types],
            'growth_rate': round(growth_rate, 2)
        }
        
        # Get AI insights
        insights = ai_service.generate_smart_insights(platform_data)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'platform_data': platform_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An error occurred while generating insights'
            }
        }), 500

