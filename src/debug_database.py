#!/usr/bin/env python3
"""
Database debugging script for Railway deployment
This script will help diagnose and fix table creation issues
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def create_debug_app():
    """Create Flask app for debugging"""
    app = Flask(__name__)
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    print(f"Original DATABASE_URL: {database_url}")
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print(f"Fixed DATABASE_URL: {database_url}")
    
    if not database_url:
        print("ERROR: No DATABASE_URL found!")
        return None
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    return app

def test_database_connection(app, db):
    """Test database connection"""
    try:
        with app.app_context():
            # Test connection
            result = db.engine.execute('SELECT 1')
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables_manually(app, db):
    """Manually create all tables"""
    try:
        with app.app_context():
            print("Creating tables manually...")
            
            # Drop all tables first (clean slate)
            print("Dropping existing tables...")
            db.drop_all()
            
            # Create all tables
            print("Creating new tables...")
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Tables created: {tables}")
            
            return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def main():
    """Main debugging function"""
    print("🔍 Starting database debugging...")
    print("=" * 50)
    
    # Check environment variables
    print("Environment variables:")
    print(f"DATABASE_URL: {'✅ Set' if os.getenv('DATABASE_URL') else '❌ Missing'}")
    print(f"SECRET_KEY: {'✅ Set' if os.getenv('SECRET_KEY') else '❌ Missing'}")
    print(f"JWT_SECRET_KEY: {'✅ Set' if os.getenv('JWT_SECRET_KEY') else '❌ Missing'}")
    print()
    
    # Create app
    app = create_debug_app()
    if not app:
        print("❌ Failed to create Flask app")
        return False
    
    # Initialize database
    db = SQLAlchemy()
    db.init_app(app)
    
    # Test connection
    if not test_database_connection(app, db):
        return False
    
    # Import models
    print("Importing models...")
    try:
        # Import User model (basic)
        sys.path.append('/app')  # Add app directory to path
        from src.models.user import User
        print("✅ User model imported")
        
        # Try to import onboarding models
        try:
            from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
            print("✅ Onboarding models imported")
        except ImportError as e:
            print(f"⚠️ Onboarding models not found: {e}")
        
        # Try to import other models
        try:
            from src.models.lead import Lead
            print("✅ Lead model imported")
        except ImportError:
            print("⚠️ Lead model not found")
            
        try:
            from src.models.commission import Commission
            print("✅ Commission model imported")
        except ImportError:
            print("⚠️ Commission model not found")
            
    except ImportError as e:
        print(f"❌ Error importing models: {e}")
        return False
    
    # Create tables
    if not create_tables_manually(app, db):
        return False
    
    print("=" * 50)
    print("🎉 Database debugging completed successfully!")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

