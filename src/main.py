from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from sqlalchemy import text
import os
import logging

# Import database instance
from src.database import db
from src.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Configure CORS with specific settings for Vercel
    CORS(app, 
         origins=[
             "https://agnusfrontend.vercel.app",
             "https://*.vercel.app",
             "http://localhost:3000",
             "http://localhost:5173"
         ],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"]
    )
    
    # Handle preflight requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
            response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Accept")
            response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response

    # Import and register blueprints
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

    try:
        from src.routes.onboarding import onboarding_bp
        app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
        logger.info("Registered onboarding blueprint")
    except ImportError as e:
        logger.error(f"Failed to import onboarding blueprint: {e}")

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

    # Import models to ensure they're registered
    try:
        from src.models.user import User
        from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
        from src.models.lead import Lead
        from src.models.commission import Commission
        from src.models.commission_settings import CommissionSettings
        from src.models.agreement import Agreement
        from src.models.support import SupportTicket, SupportMessage
        logger.info("Imported all models successfully")
    except ImportError as e:
        logger.error(f"Failed to import some models: {e}")

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
            
        except Exception as e:
            logger.error(f"Database error: {e}")

    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get registered blueprints
        blueprints = [bp.name for bp in app.blueprints.values()]
        
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

    # Debug endpoints
    @app.route('/api/debug/tables')
    def debug_tables():
        try:
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
                tables = [row[0] for row in result]
            return jsonify({
                'tables': tables,
                'total_tables': len(tables)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/debug/create-tables', methods=['POST'])
    def force_create_tables():
        try:
            # Drop all tables and recreate
            db.drop_all()
            db.create_all()
            
            # Get created tables
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
                tables = [row[0] for row in result]
            
            return jsonify({
                'message': 'Tables created successfully',
                'tables': tables
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

