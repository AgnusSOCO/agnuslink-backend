from flask import Blueprint, jsonify
import datetime

# Create a minimal onboarding blueprint with no complex imports
onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
def get_onboarding_status():
    """Minimal test endpoint to verify blueprint registration works"""
    return jsonify({
        'success': True,
        'message': 'Onboarding blueprint is working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'current_step': 'test',
        'progress': 0,
        'test_mode': True
    })

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Minimal onboarding routes are working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'routes_available': [
            '/status',
            '/test'
        ],
        'blueprint_name': 'onboarding',
        'import_status': 'minimal_imports_only'
    })

@onboarding_bp.route('/health', methods=['GET'])
def onboarding_health():
    """Health check for onboarding blueprint"""
    return jsonify({
        'status': 'healthy',
        'blueprint': 'onboarding',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

