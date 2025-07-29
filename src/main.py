from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///agnus_link.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File upload settings
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # Initialize extensions
    from src.database import db
    db.init_app(app)
    
    jwt = JWTManager(app)
    
    # CORS configuration
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)
    
    # Import models to register them with SQLAlchemy
    try:
        from src.models.user import User
        from src.models.lead import Lead
        from src.models.commission import Commission
        from src.models.commission_settings import CommissionSettings
        from src.models.agreement import Agreement
        from src.models.support import SupportTicket, SupportMessage
        from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
    except ImportError as e:
        print(f"Warning: Could not import some models: {e}")
        # Import basic models that should exist
        from src.models.user import User
    
    # Register blueprints
    try:
        from src.routes.auth import auth_bp
        from src.routes.user import user_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(user_bp, url_prefix='/api/users')
        
        # Try to import other routes
        try:
            from src.routes.leads import leads_bp
            app.register_blueprint(leads_bp, url_prefix='/api/leads')
        except ImportError:
            print("Warning: leads routes not found")
            
        try:
            from src.routes.commissions import commissions_bp
            app.register_blueprint(commissions_bp, url_prefix='/api/commissions')
        except ImportError:
            print("Warning: commissions routes not found")
            
        try:
            from src.routes.support import support_bp
            app.register_blueprint(support_bp, url_prefix='/api/support')
        except ImportError:
            print("Warning: support routes not found")
            
        try:
            from src.routes.admin import admin_bp
            app.register_blueprint(admin_bp, url_prefix='/api/admin')
        except ImportError:
            print("Warning: admin routes not found")
            
        try:
            from src.routes.ai import ai_bp
            app.register_blueprint(ai_bp, url_prefix='/api/ai')
        except ImportError:
            print("Warning: ai routes not found")
            
        try:
            from src.routes.onboarding import onboarding_bp
            app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
        except ImportError:
            print("Warning: onboarding routes not found")
            
    except ImportError as e:
        print(f"Error importing routes: {e}")
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Agnus Link API is running'}
    
    @app.route('/')
    def index():
        return {'message': 'Agnus Link API', 'status': 'running'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

