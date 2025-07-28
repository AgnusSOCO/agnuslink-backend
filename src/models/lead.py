from datetime import datetime
import secrets
import string

from src.models.user import db

class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.String(20), unique=True, nullable=False)
    
    # Lead Information
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    location_city = db.Column(db.String(100))
    location_state = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    # Submission Information
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    secondary_referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Status Tracking
    status = db.Column(db.String(50), default='submitted')  # 'submitted', 'in_review', 'qualified', 'sold', 'unqualified'
    
    # File Attachments
    attachment_url = db.Column(db.String(255))
    
    # Admin Notes
    admin_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    converted_at = db.Column(db.DateTime)
    
    # Relationships
    secondary_referrer = db.relationship('User', foreign_keys=[secondary_referrer_id])
    commissions = db.relationship('Commission', backref='lead')
    
    def __init__(self, **kwargs):
        super(Lead, self).__init__(**kwargs)
        if not self.lead_id:
            self.lead_id = self.generate_lead_id()
    
    def generate_lead_id(self):
        """Generate a unique lead ID"""
        year = datetime.now().year
        while True:
            # Format: LEAD-YYYY-XXX (where XXX is a 3-digit number)
            random_num = ''.join(secrets.choice(string.digits) for _ in range(3))
            lead_id = f"LEAD-{year}-{random_num}"
            if not Lead.query.filter_by(lead_id=lead_id).first():
                return lead_id
    
    def __repr__(self):
        return f'<Lead {self.lead_id}: {self.full_name}>'
    
    def to_dict(self, include_admin_notes=False):
        data = {
            'id': self.id,
            'lead_id': self.lead_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'location_city': self.location_city,
            'location_state': self.location_state,
            'industry': self.industry,
            'notes': self.notes,
            'submitted_by_id': self.submitted_by_id,
            'secondary_referrer_id': self.secondary_referrer_id,
            'status': self.status,
            'attachment_url': self.attachment_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None
        }
        
        if include_admin_notes:
            data['admin_notes'] = self.admin_notes
        
        return data
    
    def update_status(self, new_status, admin_notes=None):
        """Update lead status and optionally add admin notes"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if admin_notes:
            self.admin_notes = admin_notes
        
        if new_status == 'sold':
            self.converted_at = datetime.utcnow()
            # Trigger commission calculation
            self.calculate_commissions()
    
    def calculate_commissions(self):
        """Calculate and create commission records when lead converts"""
        from src.models.commission import Commission
        from src.models.commission_settings import CommissionSettings
        
        # Get current commission settings
        settings = CommissionSettings.get_current_settings()
        
        # Assume a base commission amount (this would typically come from the deal value)
        base_amount = 1000.00  # This should be configurable or passed as parameter
        
        # Primary affiliate commission
        primary_amount = base_amount * (settings.primary_affiliate_percentage / 100)
        primary_commission = Commission(
            lead_id=self.id,
            affiliate_id=self.submitted_by_id,
            commission_type='primary',
            percentage=settings.primary_affiliate_percentage,
            amount=primary_amount
        )
        db.session.add(primary_commission)
        
        # Referring affiliate commission (if exists)
        if self.submitted_by.referred_by_id:
            referring_amount = base_amount * (settings.referring_affiliate_percentage / 100)
            referring_commission = Commission(
                lead_id=self.id,
                affiliate_id=self.submitted_by.referred_by_id,
                commission_type='referral',
                percentage=settings.referring_affiliate_percentage,
                amount=referring_amount
            )
            db.session.add(referring_commission)
        
        db.session.commit()

