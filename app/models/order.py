from datetime import datetime
from app import db

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), unique=True, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    status = db.Column(db.String(50), default='Pending Pickup')
    # Statuses: Pending Pickup, Rider Assigned, Picked Up, Washing, Drying, Ironing,
    #           Ready for Delivery, Out for Delivery, Delivered, Cancelled
    
    total_amount = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)   # cumulative payments received
    payment_status = db.Column(db.String(30), default='Unpaid')  # Unpaid, Part Paid, Paid

    pickup_time = db.Column(db.DateTime, nullable=True)
    delivery_time = db.Column(db.DateTime, nullable=True)
    pickup_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=True)
    delivery_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=True)
    
    created_by_admin = db.Column(db.Boolean, default=False)  # True when admin creates on behalf of customer

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    payments = db.relationship('Payment', backref='order', lazy='dynamic')
    status_logs = db.relationship('OrderStatusLog', backref='order', lazy='dynamic')
    
    # Rider Revenue Snapshot
    rider_earnings = db.Column(db.Float, default=0.0)
    commission_rate = db.Column(db.Float, default=0.0)

    @property
    def balance_due(self):
        return max(0.0, self.total_amount - (self.amount_paid or 0.0))

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id or f'#{self.id}',
            'status': self.status,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid or 0.0,
            'balance_due': self.balance_due,
            'payment_status': self.payment_status or 'Unpaid',
            'created_at': self.created_at.isoformat(),
            'items_count': self.items.count(),
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'created_by_admin': self.created_by_admin or False,
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False) # e.g., Shirt, Trousers
    quantity = db.Column(db.Integer, default=1)
    service_type = db.Column(db.String(50), nullable=False) # e.g., Wash Only, Dry Clean, Iron Only
    price_per_item = db.Column(db.Float, nullable=False)
    
    def to_dict(self):
        return {
            'item_name': self.item_name,
            'quantity': self.quantity,
            'service_type': self.service_type,
            'price': self.price_per_item
        }

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Completed')  # Completed, Failed
    payment_method = db.Column(db.String(50), default='Cash')  # Cash, Transfer, Card, POS
    note = db.Column(db.String(255), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    reference = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recorded_by = db.relationship('User', foreign_keys=[recorded_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'status': self.status,
            'payment_method': self.payment_method,
            'note': self.note,
            'reference': self.reference,
            'created_at': self.created_at.isoformat(),
            'recorded_by': self.recorded_by.profile.full_name if self.recorded_by and self.recorded_by.profile else None,
        }

class OrderStatusLog(db.Model):
    __tablename__ = 'order_status_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
