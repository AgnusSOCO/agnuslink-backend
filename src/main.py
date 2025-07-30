import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import text
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix postgres:// to postgresql:// for SQLAlchemy 2.x
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agnus_link.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # CORS configuration - FIXED for Vercel
    cors_origins = os.environ.get('CORS_ORIGINS', 'https://agnusfrontend.vercel.app').split(',')
    CORS(app, 
         origins=cors_origins,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'Accept'],
         supports_credentials=True)
    
    # Initialize extensions
    from src.database import db
    db.init_app(app)
    
    jwt = JWTManager(app)
    
    # Import models to ensure they're registered
    try:
        from src.models.user import User
        logger.info("Imported User model")
    except ImportError as e:
        logger.error(f"Failed to import User model: {e}")
    
    try:
        from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
        logger.info("Imported onboarding models")
    except ImportError as e:
        logger.error(f"Failed to import onboarding models: {e}")
    
    try:
        from src.models.lead import Lead
        logger.info("Imported Lead model")
    except ImportError as e:
        logger.error(f"Failed to import Lead model: {e}")
    
    try:
        from src.models.commission import Commission
        logger.info("Imported Commission model")
    except ImportError as e:
        logger.error(f"Failed to import Commission model: {e}")
    
    try:
        from src.models.commission_settings import CommissionSettings
        logger.info("Imported CommissionSettings model")
    except ImportError as e:
        logger.error(f"Failed to import CommissionSettings model: {e}")
    
    try:
        from src.models.agreement import Agreement
        logger.info("Imported Agreement model")
    except ImportError as e:
        logger.error(f"Failed to import Agreement model: {e}")
    
    try:
        from src.models.support import SupportTicket, SupportMessage
        logger.info("Imported Support models")
    except ImportError as e:
        logger.error(f"Failed to import Support models: {e}")
    
    # Register blueprints
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        logger.info("Registered auth blueprint")
    except ImportError as e:
        logger.error(f"Failed to import auth blueprint: {e}")
    
    try:
        from src.routes.user import user_bp
        app.register_blueprint(user_bp, url_prefix='/api/user')
        logger.info("Registered user blueprint")
    except ImportError as e:
        logger.error(f"Failed to import user blueprint: {e}")
    
    # CRITICAL: Register onboarding blueprint
    try:
        from src.routes.onboarding import onboarding_bp
        app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
        logger.info("Registered onboarding blueprint")
    except ImportError as e:
        logger.error(f"Failed to import onboarding blueprint: {e}")
    except Exception as e:
        logger.error(f"Error registering onboarding blueprint: {e}")
    
    try:
        from src.routes.leads import leads_bp
        app.register_blueprint(leads_bp, url_prefix='/api/leads')
        logger.info("Registered leads blueprint")
    except ImportError as e:
        logger.error(f"Failed to import leads blueprint: {e}")
    
    try:
        from src.routes.commissions import commissions_bp
        app.register_blueprint(commissions_bp, url_prefix='/api/commissions')
        logger.info("Registered commissions blueprint")
    except ImportError as e:
        logger.error(f"Failed to import commissions blueprint: {e}")
    
    try:
        from src.routes.support import support_bp
        app.register_blueprint(support_bp, url_prefix='/api/support')
        logger.info("Registered support blueprint")
    except ImportError as e:
        logger.error(f"Failed to import support blueprint: {e}")
    
    try:
        from src.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        logger.info("Registered admin blueprint")
    except ImportError as e:
        logger.error(f"Failed to import admin blueprint: {e}")
    
    try:
        from src.routes.ai import ai_bp
        app.register_blueprint(ai_bp, url_prefix='/api/ai')
        logger.info("Registered ai blueprint")
    except ImportError as e:
        logger.error(f"Failed to import ai blueprint: {e}")
    
    # Create tables
    with app.app_context():
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            logger.info("Database connection successful")
            
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # List created tables for debugging
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result]
                logger.info(f"Tables created: {tables}")
                
        except Exception as e:
            logger.error(f"Database error: {e}")
    
    # Health check endpoint
    @app.route('/health')
    def health():
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get registered blueprints
        blueprints = list(app.blueprints.keys())
        
        # Get imported models
        models = []
        try:
            from src.models.user import User
            models.append("User")
        except:
            pass
        try:
            from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
            models.extend(["DocumentSignature", "KYCDocument", "OnboardingStep"])
        except:
            pass
        try:
            from src.models.lead import Lead
            models.append("Lead")
        except:
            pass
        try:
            from src.models.commission import Commission
            models.append("Commission")
        except:
            pass
        try:
            from src.models.commission_settings import CommissionSettings
            models.append("CommissionSettings")
        except:
            pass
        try:
            from src.models.agreement import Agreement
            models.append("Agreement")
        except:
            pass
        try:
            from src.models.support import SupportTicket, SupportMessage
            models.extend(["SupportTicket", "SupportMessage"])
        except:
            pass
        
        return jsonify({
            'status': 'healthy',
            'message': 'Agnus Link API is running',
            'database': db_status,
            'blueprints_registered': blueprints,
            'models_imported': models
        })
    
    # Debug endpoint to list tables
    @app.route('/api/debug/tables')
    def debug_tables():
        try:
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                """))
                
                tables = {}
                for row in result:
                    table_name, column_name, data_type = row
                    if table_name not in tables:
                        tables[table_name] = []
                    tables[table_name].append(f"{column_name} ({data_type})")
                
                return jsonify({
                    'tables': list(tables.keys()),
                    'total_tables': len(tables),
                    'table_details': tables
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Force create tables endpoint
    @app.route('/api/debug/create-tables')
    def create_tables():
        try:
            with app.app_context():
                # Drop all tables and recreate
                db.drop_all()
                db.create_all()
                
                # List created tables
                with db.engine.connect() as connection:
                    result = connection.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """))
                    tables = [row[0] for row in result]
                
                return jsonify({
                    'message': 'Tables created successfully',
                    'tables': tables
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

