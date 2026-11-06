from datetime import datetime
from app import db

class RiderTransaction(db.Model):
    __tablename__ = 'rider_transactions'

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False) # Positive = Earning, Negative = Payout
    type = db.Column(db.String(20), nullable=False) # 'EARNING', 'PAYOUT'
    reference_id = db.Column(db.String(50)) # Order Tracking ID or Payout Ref
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rider_rel = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'type': self.type,
            'reference_id': self.reference_id,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }
