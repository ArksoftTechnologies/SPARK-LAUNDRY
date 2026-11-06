from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Order, OrderItem, Address
from app import db
from app.api.utils import customer_required
from app.utils.email import send_email
import random
import string

customer_ns = Namespace('customer', description='Customer operations')

# Data Transfer Objects
order_item_model = customer_ns.model('OrderItemInput', {
    'item_name': fields.String(required=True),
    'quantity': fields.Integer(default=1),
    'service_type': fields.String(required=True, enum=['Wash', 'DryClean', 'Iron']),
    'price': fields.Float(required=True)
})

order_model = customer_ns.model('OrderInput', {
    'items': fields.List(fields.Nested(order_item_model), required=True),
    'pickup_time': fields.String(required=True, description='ISO 8601 datetime'),
    'pickup_address_id': fields.Integer(required=True)
})

@customer_ns.route('/orders')
class CustomerOrders(Resource):
    @jwt_required()
    @customer_required
    def get(self):
        """Get all orders for the logged-in customer"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        orders = user.orders.order_by(Order.created_at.desc()).all()
        return [order.to_dict() for order in orders], 200

    @jwt_required()
    @customer_required
    @customer_ns.expect(order_model)
    def post(self):
        """Create a new order"""
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Basic validation (extend as needed)
        address = Address.query.get(data['pickup_address_id'])
        # JWT returns string, DB has int
        if not address or address.user_id != int(current_user_id):
            return {'message': 'Invalid address'}, 400

        # Calculate total
        total_amount = sum(item['price'] * item['quantity'] for item in data['items'])

        # Generate Tracking ID
        tracking_id = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        new_order = Order(
            customer_id=current_user_id,
            tracking_id=tracking_id,
            total_amount=total_amount,
            # pickup_time=datetime.fromisoformat(data['pickup_time']), # Add import if needed
            pickup_address_id=data['pickup_address_id']
        )
        
        db.session.add(new_order)
        db.session.flush() # Get ID
        
        for item_data in data['items']:
            item = OrderItem(
                order_id=new_order.id,
                item_name=item_data['item_name'],
                quantity=item_data['quantity'],
                service_type=item_data['service_type'],
                price_per_item=item_data['price']
            )
            db.session.add(item)
            
        db.session.commit()

        # Send Order Confirmation Email
        try:
            send_email(new_order.customer.email, f'Order Confirmation - {new_order.tracking_id}', 'email/order_confirmation.html', order=new_order)
        except Exception as e:
            print(f"Order email failed: {e}")

        # Notify admins
        try:
            from app.api.admin import _notify_admins_new_order
            _notify_admins_new_order(new_order, placed_by='Customer')
        except Exception as e:
            print(f"Admin notification failed: {e}")

        return new_order.to_dict(), 201
@customer_ns.route('/addresses')
class CustomerAddresses(Resource):
    @jwt_required()
    @customer_required
    def get(self):
        """Get all addresses for the logged-in customer"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        return [addr.to_dict() for addr in user.addresses.all()], 200

    @jwt_required()
    @customer_required
    def post(self):
        """Add a new address"""
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        new_address = Address(
            user_id=current_user_id,
            street=data.get('street'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            is_default=False # Logic to handle defaults later
        )
        db.session.add(new_address)
        db.session.commit()
        return new_address.to_dict(), 201

@customer_ns.route('/orders/<int:id>')
class CustomerOrderDetail(Resource):
    @jwt_required()
    @customer_required
    def get(self, id):
        """Get full order details"""
        current_user_id = get_jwt_identity()
        order = Order.query.filter_by(id=id, customer_id=current_user_id).first_or_404()
        
        data = order.to_dict()
        data['items'] = [i.to_dict() for i in order.items]
        if order.pickup_address_id:
             from app.models import Address
             addr = Address.query.get(order.pickup_address_id)
             data['pickup_address'] = addr.to_dict() if addr else None
        return data, 200
