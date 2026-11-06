from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Order, OrderStatusLog
from app import db
from app.api.utils import staff_required
from app.utils.email import send_email
from datetime import datetime

staff_ns = Namespace('staff', description='Staff operations')

status_update_model = staff_ns.model('StatusUpdate', {
    'status': fields.String(required=True, description='New status'),
    'note': fields.String(description='Optional note')
})

@staff_ns.route('/orders')
class StaffOrders(Resource):
    @jwt_required()
    @staff_required
    def get(self):
        """Get all orders requiring processing"""
        # Filter logic: Show only orders that are ready for processing (Picked Up onwards)
        # Exclude: 'Pending Pickup', 'Rider Assigned', 'Cancelled', 'Delivered', 'Completed' if you only want active processing
        # Use NOT IN for simplicity to exclude pre-processing stages
        orders = Order.query.filter(Order.status.notin_(['Pending Pickup', 'Rider Assigned'])).order_by(Order.created_at.desc()).all()
        result = []
        for o in orders:
             d = o.to_dict()
             d['customer_name'] = o.customer.profile.full_name if o.customer.profile and o.customer.profile.full_name else 'Customer'
             result.append(d)
        return result, 200

@staff_ns.route('/orders/<int:id>/status')
class OrderStatus(Resource):
    @jwt_required()
    @staff_required
    @staff_ns.expect(status_update_model)
    def put(self, id):
        """Update order status"""
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        order = Order.query.get_or_404(id)
        old_status = order.status
        order.status = data['status']
        
        # Log the change
        log = OrderStatusLog(
            order_id=order.id,
            status=data['status'],
            note=data.get('note'),
            updated_by_id=current_user_id
        )
        db.session.add(log)
        db.session.commit()
        
        db.session.commit()
        
        # Send Status Update Email
        try:
            send_email(order.customer.email, f'Order Status Update - {order.tracking_id}', 'email/status_update.html', order=order)
        except Exception as e:
            print(f"Status email failed: {e}")
        
        return {'message': f'Order status updated from {old_status} to {order.status}'}, 200
        return {'message': f'Order status updated from {old_status} to {order.status}'}, 200

@staff_ns.route('/orders/<int:id>')
class StaffOrderDetail(Resource):
    @jwt_required()
    @staff_required
    def get(self, id):
        """Get full details for processing"""
        order = Order.query.get_or_404(id)
        data = order.to_dict()
        data['items'] = [i.to_dict() for i in order.items]
        data['customer'] = order.customer.to_dict()
        if order.rider:
            data['rider'] = order.rider.to_dict()
        
        if order.pickup_address_id:
             from app.models import Address
             p_addr = Address.query.get(order.pickup_address_id)
             data['pickup_address'] = p_addr.to_dict() if p_addr else None
             
        return data, 200
