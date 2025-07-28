from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
import string

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='affiliate')  # 'affiliate', 'admin', 'client'
    
    # Profile Information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    
    # Payment Information
    paypal_email = db.Column(db.String(120))
    bank_account_number = db.Column(db.String(50))
    bank_routing_number = db.Column(db.String(20))
    bank_account_holder_name = db.Column(db.String(100))
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    government_id_url = db.Column(db.String(255))
    
    # Referral Information
    referral_code = db.Column(db.String(20), unique=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    referred_by = db.relationship('User', remote_side=[id], backref='referrals')
    leads_submitted = db.relationship('Lead', foreign_keys='Lead.submitted_by_id', backref='submitted_by')
    commissions = db.relationship('Commission', backref='affiliate')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
    
    def generate_referral_code(self):
        """Generate a unique referral code"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not User.query.filter_by(referral_code=code).first():
                return code
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'is_verified': self.is_verified,
            'referral_code': self.referral_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data.update({
                'paypal_email': self.paypal_email,
                'bank_account_number': self.bank_account_number,
                'bank_routing_number': self.bank_routing_number,
                'bank_account_holder_name': self.bank_account_holder_name,
                'government_id_url': self.government_id_url
            })
        
        return data
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    def get_referral_count(self):
        """Get count of direct referrals"""
        return len(self.referrals)
    
    def get_total_commission(self):
        """Get total commission earned"""
        from src.models.commission import Commission
        total = db.session.query(db.func.sum(Commission.amount)).filter_by(
            affiliate_id=self.id,
            status='paid'
        ).scalar()
        return float(total) if total else 0.0
    
    def get_pending_commission(self):
        """Get pending commission amount"""
        from src.models.commission import Commission
        total = db.session.query(db.func.sum(Commission.amount)).filter_by(
            affiliate_id=self.id,
            status='pending'
        ).scalar()
        return float(total) if total else 0.0
