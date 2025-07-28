from datetime import datetime

from src.models.user import db

class Commission(db.Model):
    __tablename__ = 'commissions'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    affiliate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    commission_type = db.Column(db.String(50), nullable=False)  # 'primary', 'referral', 'bonus'
    
    # Commission Details
    percentage = db.Column(db.Numeric(5, 2), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payout Information
    status = db.Column(db.String(50), default='pending')  # 'pending', 'approved', 'paid'
    payout_requested_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Commission {self.id}: ${self.amount} for {self.commission_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'affiliate_id': self.affiliate_id,
            'commission_type': self.commission_type,
            'percentage': float(self.percentage),
            'amount': float(self.amount),
            'status': self.status,
            'payout_requested_at': self.payout_requested_at.isoformat() if self.payout_requested_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def approve(self):
        """Approve the commission for payout"""
        self.status = 'approved'
        self.approved_at = datetime.utcnow()
    
    def mark_as_paid(self):
        """Mark commission as paid"""
        self.status = 'paid'
        self.paid_at = datetime.utcnow()
    
    @staticmethod
    def get_total_by_affiliate(affiliate_id, status=None):
        """Get total commission amount for an affiliate"""
        query = Commission.query.filter_by(affiliate_id=affiliate_id)
        if status:
            query = query.filter_by(status=status)
        
        total = db.session.query(db.func.sum(Commission.amount)).filter(
            Commission.affiliate_id == affiliate_id
        )
        if status:
            total = total.filter(Commission.status == status)
        
        result = total.scalar()
        return float(result) if result else 0.0
    
    @staticmethod
    def get_monthly_earnings(affiliate_id, year, month):
        """Get monthly earnings for an affiliate"""
        from sqlalchemy import extract
        
        total = db.session.query(db.func.sum(Commission.amount)).filter(
            Commission.affiliate_id == affiliate_id,
            Commission.status == 'paid',
            extract('year', Commission.paid_at) == year,
            extract('month', Commission.paid_at) == month
        ).scalar()
        
        return float(total) if total else 0.0

