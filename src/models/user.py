from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
import string

# Import db from database module
from src.database import db

class User(db.Model):
    __tablename__ = 'users'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic authentication
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    
    # Account settings
    role = db.Column(db.String(20), default='affiliate')  # 'affiliate', 'admin', 'client'
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Onboarding fields
    onboarding_status = db.Column(db.String(50), default='pending')
    onboarding_step = db.Column(db.Integer, default=1)
    kyc_status = db.Column(db.String(50), default='pending')
    kyc_rejection_reason = db.Column(db.Text)
    
    # Agreement tracking
    agreements_complete = db.Column(db.Boolean, default=False)
    affiliate_agreement_signed = db.Column(db.Boolean, default=False)
    finders_fee_contract_signed = db.Column(db.Boolean, default=False)
    
    # Payment information
    paypal_email = db.Column(db.String(120))
    bank_account_number = db.Column(db.String(50))
    bank_routing_number = db.Column(db.String(20))
    bank_account_holder_name = db.Column(db.String(100))
    
    # Referral system
    referral_code = db.Column(db.String(20), unique=True, index=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    commission_rate = db.Column(db.Float, default=0.10)
    
    # File uploads
    government_id_url = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    referred_by = db.relationship('User', remote_side=[id], backref='referrals')
    
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
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def missing_agreements(self):
        """Return list of missing agreements"""
        missing = []
        if not self.affiliate_agreement_signed:
            missing.append('affiliate_agreement')
        if not self.finders_fee_contract_signed:
            missing.append('finders_fee_contract')
        return missing
    
    @property
    def onboarding_complete(self):
        """Check if onboarding is complete"""
        return (self.onboarding_status == 'completed' and 
                self.kyc_status == 'approved' and 
                self.agreements_complete)
    
    @property
    def can_access_dashboard(self):
        """Check if user can access full dashboard"""
        return self.onboarding_complete and self.is_active
    
    def update_onboarding_status(self):
        """Update onboarding status based on current state"""
        if self.finders_fee_contract_signed and self.kyc_status != 'submitted':
            self.onboarding_status = 'documents_signed'
        elif self.kyc_status == 'submitted':
            self.onboarding_status = 'kyc_submitted'
        elif self.kyc_status == 'approved' and self.finders_fee_contract_signed:
            self.onboarding_status = 'completed'
            self.agreements_complete = True
        elif self.kyc_status == 'rejected':
            self.onboarding_status = 'rejected'
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'onboarding_status': self.onboarding_status,
            'onboarding_step': self.onboarding_step,
            'kyc_status': self.kyc_status,
            'kyc_rejection_reason': self.kyc_rejection_reason,
            'agreements_complete': self.agreements_complete,
            'affiliate_agreement_signed': self.affiliate_agreement_signed,
            'finders_fee_contract_signed': self.finders_fee_contract_signed,
            'missing_agreements': self.missing_agreements,
            'onboarding_complete': self.onboarding_complete,
            'can_access_dashboard': self.can_access_dashboard,
            'referral_code': self.referral_code,
            'referred_by_id': self.referred_by_id,
            'commission_rate': self.commission_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
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
    
    def __repr__(self):
        return f'<User {self.email}>'

