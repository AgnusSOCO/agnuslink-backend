from datetime import datetime

from src.models.user import db

class CommissionSettings(db.Model):
    __tablename__ = 'commission_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Commission Rates
    primary_affiliate_percentage = db.Column(db.Numeric(5, 2), default=50.00)
    referring_affiliate_percentage = db.Column(db.Numeric(5, 2), default=25.00)
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    effective_from = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CommissionSettings {self.id}: Primary {self.primary_affiliate_percentage}%, Referral {self.referring_affiliate_percentage}%>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'primary_affiliate_percentage': float(self.primary_affiliate_percentage),
            'referring_affiliate_percentage': float(self.referring_affiliate_percentage),
            'is_active': self.is_active,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def get_current_settings():
        """Get the current active commission settings"""
        settings = CommissionSettings.query.filter_by(is_active=True).order_by(
            CommissionSettings.effective_from.desc()
        ).first()
        
        if not settings:
            # Create default settings if none exist
            settings = CommissionSettings()
            db.session.add(settings)
            db.session.commit()
        
        return settings
    
    @staticmethod
    def create_new_settings(primary_percentage, referring_percentage):
        """Create new commission settings and deactivate old ones"""
        # Deactivate all existing settings
        CommissionSettings.query.update({'is_active': False})
        
        # Create new settings
        new_settings = CommissionSettings(
            primary_affiliate_percentage=primary_percentage,
            referring_affiliate_percentage=referring_percentage,
            is_active=True,
            effective_from=datetime.utcnow()
        )
        
        db.session.add(new_settings)
        db.session.commit()
        
        return new_settings

