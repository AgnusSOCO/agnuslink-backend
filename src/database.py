from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

def reset_db(app):
    """Reset database - drop and recreate all tables"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset successfully!")

