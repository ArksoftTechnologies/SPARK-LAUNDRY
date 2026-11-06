from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Order, OrderStatusLog
from app import db
from sqlalchemy import func
from app.api.utils import staff_required 
from app.utils.email import send_email

rider_ns = Namespace('rider', description='Rider operations')

@rider_ns.route('/available')
class AvailableTasks(Resource):
    @jwt_required()
    def get(self):
        """Get available pickup/delivery tasks"""
        # Tasks not yet assigned to restricted status like 'Ready for Delivery' or 'Pending Pickup'
        orders = Order.query.filter(
            (Order.status == 'Pending Pickup') | (Order.status == 'Ready for Delivery'),
            Order.rider_id == None
        ).all()
        result = []
        for o in orders:
             d = o.to_dict()
             d['customer_name'] = o.customer.profile.full_name if o.customer.profile and o.customer.profile.full_name else 'Valued Customer'
             result.append(d)
        return result, 200

@rider_ns.route('/mytasks')
class MyTasks(Resource):
    @jwt_required()
    def get(self):
        """Get tasks assigned to current rider"""
        current_user_id = get_jwt_identity()
        orders = Order.query.filter_by(rider_id=current_user_id).all()
        result = []
        for o in orders:
             d = o.to_dict()
             d['customer_name'] = o.customer.profile.full_name if o.customer.profile and o.customer.profile.full_name else 'Customer'
             result.append(d)
        return result, 200

@rider_ns.route('/tasks/<int:id>/accept')
class AcceptTask(Resource):
    @jwt_required()
    def put(self, id):
        """Accept a pickup or delivery task"""
        current_user_id = get_jwt_identity()
        order = Order.query.get_or_404(id)
        
        if order.rider_id:
            return {'message': 'Task already assigned'}, 400
            
        order.rider_id = current_user_id
        if order.status == 'Pending Pickup':
            order.status = 'Rider Assigned'
        
        db.session.commit()
        return {'message': 'Task accepted'}, 200

@rider_ns.route('/tasks/<int:id>/complete')
class CompleteTask(Resource):
    @jwt_required()
    def put(self, id):
        """Mark task as completed (Picked Up or Delivered)"""
        from app.models.settings import SystemSetting
        from app.models.finance import RiderTransaction
        
        order = Order.query.get_or_404(id)
        current_user_id = int(get_jwt_identity())
        
        # Verify rider ownership
        if order.rider_id != current_user_id:
            return {'message': 'Unauthorized'}, 403
        
        current_status = order.status
        if current_status == 'Rider Assigned':
            order.status = 'Picked Up'
            # Send Email (Pickup)
            try:
                send_email(order.customer.email, f'Order Picked Up - {order.tracking_id}', 'email/status_update.html', order=order)
            except: pass

        elif current_status == 'Out for Delivery':
            order.status = 'Delivered'
            order.payment_status = 'Paid' # Assume COD or payment upon delivery for now
            
            # Calculate Earnings
            rate = float(SystemSetting.get_value('rider_commission_rate', '0.15'))
            earnings = order.total_amount * rate
            
            order.rider_earnings = earnings
            order.commission_rate = rate
            
            # Create Ledger Entry
            tx = RiderTransaction(
                rider_id=current_user_id,
                amount=earnings,
                type='EARNING',
                reference_id=order.tracking_id,
                description=f'Commission for Order {order.tracking_id}'
            )
            db.session.add(tx)
            
            # Send Email (Delivered)
            try:
                send_email(order.customer.email, f'Order Delivered - {order.tracking_id}', 'email/status_update.html', order=order)
            except: pass
            
        db.session.commit()
        return {'message': 'Task updated'}, 200

@rider_ns.route('/wallet')
class RiderWallet(Resource):
    @jwt_required()
    def get(self):
        """Get wallet balance and history"""
        from app.models.finance import RiderTransaction
        current_user_id = get_jwt_identity()
        
        # Balance
        balance = db.session.query(func.sum(RiderTransaction.amount)).filter_by(rider_id=current_user_id).scalar() or 0.0
        
        # History
        history = RiderTransaction.query.filter_by(rider_id=current_user_id).order_by(RiderTransaction.created_at.desc()).limit(20).all()
        
        return {
            'balance': balance,
            'history': [t.to_dict() for t in history]
        }, 200

@rider_ns.route('/tasks/<int:id>')
class RiderTaskDetail(Resource):
    @jwt_required()
    def get(self, id):
        """Get full task details"""
        order = Order.query.get_or_404(id)
        # Security check: Rider should only see if available OR assigned to them
        current_rider_id = get_jwt_identity()
        
        # Allow if no rider assigned (Available) OR assigned to this rider
        if order.rider_id and order.rider_id != int(current_rider_id):
            return {'message': 'Unauthorized'}, 403
            
        data = order.to_dict()
        data['items'] = [i.to_dict() for i in order.items]
        data['customer'] = order.customer.to_dict()
        
        if order.pickup_address_id:
             from app.models import Address
             p_addr = Address.query.get(order.pickup_address_id)
             data['pickup_address'] = p_addr.to_dict() if p_addr else None
             
        return data, 200
