import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta

# Import configuration
from src.config import config

# Import all models
from src.models.user import db
from src.models.lead import Lead
from src.models.commission import Commission
from src.models.commission_settings import CommissionSettings
from src.models.agreement import Agreement
from src.models.support import SupportTicket, SupportMessage

# Import all routes
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.leads import leads_bp
from src.routes.commissions import commissions_bp
from src.routes.support import support_bp
from src.routes.admin import admin_bp
from src.routes.ai import ai_bp

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Enable CORS for all routes
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize JWT
    jwt = JWTManager(app)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:"
        return response
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(leads_bp, url_prefix='/api/leads')
    app.register_blueprint(commissions_bp, url_prefix='/api/commissions')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    
    # Database configuration
    db.init_app(app)
    
    # Create tables and default data
    with app.app_context():
        db.create_all()
        
        # Create default commission settings if none exist
        if not CommissionSettings.query.first():
            default_settings = CommissionSettings()
            db.session.add(default_settings)
            db.session.commit()
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'version': '1.0.0'}, 200
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
                return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "index.html not found", 404

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'success': False, 'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired'}}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'success': False, 'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid token'}}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'success': False, 'error': {'code': 'TOKEN_REQUIRED', 'message': 'Authorization token is required'}}, 401
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
