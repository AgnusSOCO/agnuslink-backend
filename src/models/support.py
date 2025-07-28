from datetime import datetime

from src.models.user import db

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ticket Information
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='open')  # 'open', 'in_progress', 'resolved', 'closed'
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high', 'urgent'
    
    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='support_tickets')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])
    messages = db.relationship('SupportMessage', backref='ticket', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SupportTicket {self.id}: {self.subject}>'
    
    def to_dict(self, include_messages=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'priority': self.priority,
            'assigned_to_id': self.assigned_to_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'user_name': self.user.get_full_name() if self.user else None,
            'assigned_to_name': self.assigned_to.get_full_name() if self.assigned_to else None
        }
        
        if include_messages:
            data['messages'] = [message.to_dict() for message in self.messages]
        
        return data
    
    def add_message(self, user_id, message, is_internal=False, attachment_url=None):
        """Add a message to the ticket"""
        support_message = SupportMessage(
            ticket_id=self.id,
            user_id=user_id,
            message=message,
            is_internal=is_internal,
            attachment_url=attachment_url
        )
        db.session.add(support_message)
        self.updated_at = datetime.utcnow()
        return support_message
    
    def update_status(self, new_status):
        """Update ticket status"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if new_status in ['resolved', 'closed']:
            self.resolved_at = datetime.utcnow()
    
    def assign_to(self, admin_user_id):
        """Assign ticket to an admin"""
        self.assigned_to_id = admin_user_id
        self.status = 'in_progress'
        self.updated_at = datetime.utcnow()


class SupportMessage(db.Model):
    __tablename__ = 'support_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Message Content
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # For admin-only notes
    
    # Attachments
    attachment_url = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='support_messages')
    
    def __repr__(self):
        return f'<SupportMessage {self.id} for Ticket {self.ticket_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'message': self.message,
            'is_internal': self.is_internal,
            'attachment_url': self.attachment_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_name': self.user.get_full_name() if self.user else None,
            'user_role': self.user.role if self.user else None
        }

