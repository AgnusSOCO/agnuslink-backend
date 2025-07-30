from flask import Blueprint, jsonify
import datetime

# Add database import
from database import db

# Create onboarding blueprint with database import
onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
def get_onboarding_status():
    """Test endpoint with database import"""
    return jsonify({
        'success': True,
        'message': 'Onboarding blueprint with database import is working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'current_step': 'test',
        'progress': 0,
        'database_available': db is not None,
        'test_mode': True
    })

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Onboarding routes with database import are working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'routes_available': [
            '/status',
            '/test',
            '/health'
        ],
        'blueprint_name': 'onboarding',
        'import_status': 'database_imported',
        'database_engine': str(db.engine) if db else 'None'
    })

@onboarding_bp.route('/health', methods=['GET'])
def onboarding_health():
    """Health check for onboarding blueprint"""
    return jsonify({
        'status': 'healthy',
        'blueprint': 'onboarding',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'database_connected': True if db else False
    })

