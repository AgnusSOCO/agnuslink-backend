from datetime import datetime
from src.database import db

class DocumentSignature(db.Model):
    __tablename__ = 'document_signatures'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # 'finders_fee_contract', 'affiliate_agreement'
    signnow_document_id = db.Column(db.String(255))
    signnow_template_id = db.Column(db.String(255))
    signature_status = db.Column(db.Enum('pending', 'sent', 'signed', 'completed', 'declined', name='signature_status'), default='pending')
    signed_at = db.Column(db.DateTime)
    document_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='document_signatures')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_type': self.document_type,
            'signnow_document_id': self.signnow_document_id,
            'signature_status': self.signature_status,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'document_url': self.document_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class KYCDocument(db.Model):
    __tablename__ = 'kyc_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_type = db.Column(db.Enum('government_id', 'proof_of_address', 'selfie_with_id', name='kyc_document_type'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    verification_status = db.Column(db.Enum('pending', 'approved', 'rejected', name='verification_status'), default='pending')
    rejection_reason = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='kyc_documents')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'verification_status': self.verification_status,
            'rejection_reason': self.rejection_reason,
            'uploaded_at': self.uploaded_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }

class OnboardingStep(db.Model):
    __tablename__ = 'onboarding_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    step_name = db.Column(db.String(50), nullable=False)  # 'welcome', 'signature', 'kyc', 'review', 'completed'
    step_status = db.Column(db.Enum('pending', 'in_progress', 'completed', 'skipped', name='step_status'), default='pending')
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    data = db.Column(db.JSON)  # Store step-specific data
    
    # Relationship
    user = db.relationship('User', backref='onboarding_steps')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'step_name': self.step_name,
            'step_status': self.step_status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'data': self.data
        }

