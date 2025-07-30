from flask import Blueprint, jsonify
import datetime

# Create onboarding blueprint WITHOUT importing db at module level
onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
def get_onboarding_status():
    """Test endpoint with lazy database import"""
    # Import db inside the function to avoid circular import
    try:
        from database import db
        database_available = db is not None
        database_info = str(db.engine) if db else 'None'
    except ImportError as e:
        database_available = False
        database_info = f"Import error: {str(e)}"
    except Exception as e:
        database_available = False
        database_info = f"Error: {str(e)}"
    
    return jsonify({
        'success': True,
        'message': 'Onboarding blueprint with lazy database import is working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'current_step': 'test',
        'progress': 0,
        'database_available': database_available,
        'database_info': database_info,
        'test_mode': True,
        'import_method': 'lazy_import'
    })

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    """Test endpoint to verify onboarding routes are working"""
    return jsonify({
        'message': 'Onboarding routes with lazy database import are working!',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'routes_available': [
            '/status',
            '/test',
            '/health'
        ],
        'blueprint_name': 'onboarding',
        'import_status': 'lazy_database_import'
    })

@onboarding_bp.route('/health', methods=['GET'])
def onboarding_health():
    """Health check for onboarding blueprint"""
    # Test database connection inside function
    try:
        from database import db
        db_connected = True if db else False
    except:
        db_connected = False
    
    return jsonify({
        'status': 'healthy',
        'blueprint': 'onboarding',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'database_connected': db_connected
    })

