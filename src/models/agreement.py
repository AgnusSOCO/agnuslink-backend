from datetime import datetime
import json

from src.models.user import db

class Agreement(db.Model):
    __tablename__ = 'agreements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agreement_type = db.Column(db.String(50), nullable=False)  # 'affiliate_agreement', 'finders_fee_contract'
    
    # Agreement Details
    document_url = db.Column(db.String(255))
    signed_document_url = db.Column(db.String(255))
    
    # Signature Information
    signed_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    signature_data = db.Column(db.Text)  # JSON data from signature API
    
    # Status
    status = db.Column(db.String(50), default='pending')  # 'pending', 'signed', 'expired'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='agreements')
    
    def __repr__(self):
        return f'<Agreement {self.id}: {self.agreement_type} for User {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'agreement_type': self.agreement_type,
            'document_url': self.document_url,
            'signed_document_url': self.signed_document_url,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'ip_address': self.ip_address,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def sign_agreement(self, signature_data, ip_address):
        """Sign the agreement"""
        self.signature_data = json.dumps(signature_data) if isinstance(signature_data, dict) else signature_data
        self.ip_address = ip_address
        self.signed_at = datetime.utcnow()
        self.status = 'signed'
    
    def get_signature_data(self):
        """Get signature data as dictionary"""
        if self.signature_data:
            try:
                return json.loads(self.signature_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @staticmethod
    def get_user_agreements(user_id):
        """Get all agreements for a user"""
        return Agreement.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def check_required_agreements(user_id):
        """Check if user has signed all required agreements"""
        required_types = ['affiliate_agreement', 'finders_fee_contract']
        signed_agreements = Agreement.query.filter_by(
            user_id=user_id,
            status='signed'
        ).all()
        
        signed_types = [agreement.agreement_type for agreement in signed_agreements]
        missing_agreements = [agreement_type for agreement_type in required_types 
                            if agreement_type not in signed_types]
        
        return len(missing_agreements) == 0, missing_agreements
    
    @staticmethod
    def create_required_agreements(user_id):
        """Create required agreements for a new user"""
        required_types = ['affiliate_agreement', 'finders_fee_contract']
        
        for agreement_type in required_types:
            existing = Agreement.query.filter_by(
                user_id=user_id,
                agreement_type=agreement_type
            ).first()
            
            if not existing:
                agreement = Agreement(
                    user_id=user_id,
                    agreement_type=agreement_type,
                    status='pending'
                )
                db.session.add(agreement)
        
        db.session.commit()

