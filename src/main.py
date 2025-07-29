from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    logger.info("Setting up Flask configuration...")
    
    # Basic Flask config
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    logger.info(f"Database URL found: {'Yes' if database_url else 'No'}")
    
    if database_url:
        # Fix postgres:// to postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            logger.info("Fixed postgres:// to postgresql://")
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info("Using PostgreSQL database")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agnus_link.db'
        logger.info("Using SQLite database (fallback)")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # File upload settings
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # Initialize extensions
    logger.info("Initializing Flask extensions...")
    
    # Initialize database
    from src.database import db
    db.init_app(app)
    logger.info("Database initialized")
    
    # Initialize JWT
    jwt = JWTManager(app)
    logger.info("JWT initialized")
    
    # Initialize CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)
    logger.info(f"CORS initialized with origins: {cors_origins}")
    
    # Import and register models
    logger.info("Importing models...")
    models_imported = []
    
    try:
        from src.models.user import User
        models_imported.append('User')
        logger.info("✅ User model imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import User model: {e}")
        return None
    
    # Try to import other models (optional)
    optional_models = [
        ('src.models.onboarding', ['DocumentSignature', 'KYCDocument', 'OnboardingStep']),
        ('src.models.lead', ['Lead']),
        ('src.models.commission', ['Commission']),
        ('src.models.commission_settings', ['CommissionSettings']),
        ('src.models.agreement', ['Agreement']),
        ('src.models.support', ['SupportTicket', 'SupportMessage'])
    ]
    
    for module_name, model_names in optional_models:
        try:
            module = __import__(module_name, fromlist=model_names)
            for model_name in model_names:
                if hasattr(module, model_name):
                    models_imported.append(model_name)
            logger.info(f"✅ {module_name} models imported")
        except ImportError:
            logger.warning(f"⚠️ {module_name} models not found (optional)")
    
    logger.info(f"Total models imported: {models_imported}")
    
    # Register blueprints
    logger.info("Registering blueprints...")
    blueprints_registered = []
    
    # Essential blueprints
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        blueprints_registered.append('auth')
        logger.info("✅ Auth blueprint registered")
    except ImportError as e:
        logger.error(f"❌ Failed to import auth blueprint: {e}")
    
    try:
        from src.routes.user import user_bp
        app.register_blueprint(user_bp, url_prefix='/api/users')
        blueprints_registered.append('user')
        logger.info("✅ User blueprint registered")
    except ImportError as e:
        logger.warning(f"⚠️ User blueprint not found: {e}")
    
    # Optional blueprints
    optional_blueprints = [
        ('src.routes.onboarding', 'onboarding_bp', '/api/onboarding'),
        ('src.routes.leads', 'leads_bp', '/api/leads'),
        ('src.routes.commissions', 'commissions_bp', '/api/commissions'),
        ('src.routes.support', 'support_bp', '/api/support'),
        ('src.routes.admin', 'admin_bp', '/api/admin'),
        ('src.routes.ai', 'ai_bp', '/api/ai')
    ]
    
    for module_name, blueprint_name, url_prefix in optional_blueprints:
        try:
            module = __import__(module_name, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            blueprints_registered.append(blueprint_name.replace('_bp', ''))
            logger.info(f"✅ {blueprint_name} registered")
        except ImportError:
            logger.warning(f"⚠️ {module_name} blueprint not found (optional)")
        except AttributeError:
            logger.warning(f"⚠️ {blueprint_name} not found in {module_name}")
    
    logger.info(f"Total blueprints registered: {blueprints_registered}")
    
    # Create database tables
    logger.info("Creating database tables...")
    with app.app_context():
        try:
            # Test database connection (SQLAlchemy 2.x compatible)
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            logger.info("✅ Database connection successful")
            
            # Drop all tables (clean slate)
            logger.info("Dropping existing tables...")
            db.drop_all()
            
            # Create all tables
            logger.info("Creating new tables...")
            db.create_all()
            
            # Verify tables were created (SQLAlchemy 2.x compatible)
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"✅ Tables created successfully: {tables}")
            
            if not tables:
                logger.error("❌ No tables were created!")
            else:
                logger.info(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
            
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            # Don't return None, let the app start anyway
    
    # Health check endpoints
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection (SQLAlchemy 2.x compatible)
            with app.app_context():
                with db.engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return jsonify({
            'status': 'healthy',
            'message': 'Agnus Link API is running',
            'database': db_status,
            'models_imported': models_imported,
            'blueprints_registered': blueprints_registered
        })
    
    @app.route('/')
    def index():
        """Root endpoint"""
        return jsonify({
            'message': 'Agnus Link API',
            'status': 'running',
            'version': '1.0.0'
        })
    
    @app.route('/api/debug/tables')
    def debug_tables():
        """Debug endpoint to check tables"""
        try:
            with app.app_context():
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                table_info = {}
                for table in tables:
                    columns = inspector.get_columns(table)
                    table_info[table] = [col['name'] for col in columns]
                
                return jsonify({
                    'tables': tables,
                    'table_info': table_info,
                    'total_tables': len(tables)
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/debug/create-tables')
    def force_create_tables():
        """Force create tables endpoint"""
        try:
            with app.app_context():
                logger.info("Force creating tables...")
                
                # Drop all tables
                db.drop_all()
                logger.info("Tables dropped")
                
                # Create all tables
                db.create_all()
                logger.info("Tables created")
                
                # Verify tables
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                return jsonify({
                    'success': True,
                    'message': 'Tables created successfully',
                    'tables': tables,
                    'total_tables': len(tables)
                })
        except Exception as e:
            logger.error(f"Error force creating tables: {e}")
            return jsonify({'error': str(e)}), 500
    
    logger.info("Flask app created successfully!")
    return app

if __name__ == '__main__':
    app = create_app()
    if app:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("Failed to create Flask app")
        exit(1)

