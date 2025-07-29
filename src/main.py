from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.database import db
from src.config import Config
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # CORS configuration
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)
    
    # Import models to register them with SQLAlchemy
    from src.models.user import User
    from src.models.lead import Lead
    from src.models.commission import Commission
    from src.models.commission_settings import CommissionSettings
    from src.models.agreement import Agreement
    from src.models.support import SupportTicket, SupportMessage
    from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
    
    # Register blueprints
    from src.routes.auth import auth_bp
    from src.routes.user import user_bp
    from src.routes.leads import leads_bp
    from src.routes.commissions import commissions_bp
    from src.routes.support import support_bp
    from src.routes.admin import admin_bp
    from src.routes.ai import ai_bp
    from src.routes.onboarding import onboarding_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(leads_bp, url_prefix='/api/leads')
    app.register_blueprint(commissions_bp, url_prefix='/api/commissions')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
    
    # Create tables
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Agnus Link API is running'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

