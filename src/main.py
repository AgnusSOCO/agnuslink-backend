from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///agnus_link.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    CORS(app, origins=['*'], supports_credentials=True, 
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    jwt = JWTManager(app)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database
    try:
        from src.database import db
        db.init_app(app)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Global error handlers for JSON responses
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({'error': 'Unprocessable entity', 'message': 'Invalid data provided'}), 422
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token expired', 'message': 'Please log in again'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token', 'message': 'Please log in again'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Missing token', 'message': 'Authorization header required'}), 401
    
    # Handle preflight OPTIONS requests globally
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({'message': 'OK'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
    
    # Register blueprints
    blueprints_registered = []
    
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        blueprints_registered.append('auth')
        logger.info("Auth blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register auth blueprint: {str(e)}")
    
    try:
        from src.routes.user import user_bp
        app.register_blueprint(user_bp, url_prefix='/api/user')
        blueprints_registered.append('user')
        logger.info("User blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register user blueprint: {str(e)}")
    
    try:
        from src.routes.onboarding import onboarding_bp
        app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
        blueprints_registered.append('onboarding')
        logger.info("Onboarding blueprint registered successfully")
        
        # Log all onboarding routes
        onboarding_routes = []
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/api/onboarding'):
                onboarding_routes.append(rule.rule)
        logger.info(f"Onboarding routes registered: {onboarding_routes}")
        
    except Exception as e:
        logger.error(f"Failed to register onboarding blueprint: {str(e)}")
    
    try:
        from src.routes.leads import leads_bp
        app.register_blueprint(leads_bp, url_prefix='/api/leads')
        blueprints_registered.append('leads')
        logger.info("Leads blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register leads blueprint: {str(e)}")
    
    try:
        from src.routes.commissions import commissions_bp
        app.register_blueprint(commissions_bp, url_prefix='/api/commissions')
        blueprints_registered.append('commissions')
        logger.info("Commissions blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register commissions blueprint: {str(e)}")
    
    try:
        from src.routes.support import support_bp
        app.register_blueprint(support_bp, url_prefix='/api/support')
        blueprints_registered.append('support')
        logger.info("Support blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register support blueprint: {str(e)}")
    
    try:
        from src.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        blueprints_registered.append('admin')
        logger.info("Admin blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register admin blueprint: {str(e)}")
    
    try:
        from src.routes.ai import ai_bp
        app.register_blueprint(ai_bp, url_prefix='/api/ai')
        blueprints_registered.append('ai')
        logger.info("AI blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register ai blueprint: {str(e)}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Import models to verify they're working
            from src.models.user import User
            from src.models.lead import Lead
            from src.models.commission import Commission
            from src.models.commission_settings import CommissionSettings
            from src.models.agreement import Agreement
            from src.models.support import SupportTicket
            
            models_imported = ['User', 'Lead', 'Commission', 'CommissionSettings', 'Agreement', 'SupportTicket']
            
            # Get all registered routes
            all_routes = []
            for rule in app.url_map.iter_rules():
                all_routes.append(rule.rule)
            
            # Get onboarding specific routes
            onboarding_routes = [rule for rule in all_routes if rule.startswith('/api/onboarding')]
            
            return jsonify({
                'status': 'healthy',
                'message': 'Agnus Link API is running',
                'version': 'v1.0_json_error_handling',
                'blueprints_registered': blueprints_registered,
                'models_imported': models_imported,
                'total_routes': len(all_routes),
                'onboarding_routes': onboarding_routes,
                'cors_enabled': True,
                'json_error_handling': True
            }), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'blueprints_registered': blueprints_registered
            }), 500
    
    # Create tables
    with app.app_context():
        try:
            from src.database import db
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
    
    logger.info(f"Flask app created successfully with {len(blueprints_registered)} blueprints")
    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

