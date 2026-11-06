from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request
from app.models import User, Order, OrderItem, Address, OrderStatusLog
from app.models.order import Payment
from app import db
from app.api.utils import admin_required
from app.utils.email import send_email
from sqlalchemy import func
import random, string, datetime

admin_ns = Namespace('admin', description='Admin operations')

# ─── Analytics ────────────────────────────────────────────────────────────────

@admin_ns.route('/analytics')
class AdminAnalytics(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """Get system analytics — revenue based on actual payments received"""
        from app.models.order import Payment
        from datetime import date

        total_orders = Order.query.count()
        total_users  = User.query.count()

        # Revenue = sum of all completed payments (actual money received)
        total_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter_by(status='Completed').scalar() or 0.0

        # Today's revenue
        today_start = datetime.datetime.combine(date.today(), datetime.time.min)
        today_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.status == 'Completed',
            Payment.created_at >= today_start
        ).scalar() or 0.0

        # This month's revenue
        month_start = datetime.datetime(date.today().year, date.today().month, 1)
        month_revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.status == 'Completed',
            Payment.created_at >= month_start
        ).scalar() or 0.0

        # Outstanding balance (orders not fully paid)
        outstanding = db.session.query(
            func.sum(Order.total_amount - Order.amount_paid)
        ).filter(
            Order.payment_status.in_(['Unpaid', 'Part Paid'])
        ).scalar() or 0.0

        status_counts = db.session.query(
            Order.status, func.count(Order.status)
        ).group_by(Order.status).all()

        total_riders = User.query.filter_by(role='rider').count()

        return {
            'total_orders':   total_orders,
            'total_users':    total_users,
            'total_revenue':  total_revenue,
            'today_revenue':  today_revenue,
            'month_revenue':  month_revenue,
            'outstanding':    outstanding,
            'total_riders':   total_riders,
            'status_breakdown': dict(status_counts)
        }, 200


# ─── Users ────────────────────────────────────────────────────────────────────

@admin_ns.route('/users')
class UserList(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """List all users"""
        users = User.query.all()
        return [user.to_dict() for user in users], 200

    @jwt_required()
    @admin_required
    @admin_ns.doc(body=None)
    def post(self):
        """Create a new user (Staff/Rider/Admin/Customer)"""
        from app.models import UserProfile

        data = request.get_json()

        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered'}, 400

        new_user = User(
            email=data['email'],
            password=data['password'],
            role=data.get('role', 'customer')
        )
        db.session.add(new_user)
        db.session.flush()

        profile = UserProfile(
            user_id=new_user.id,
            full_name=data.get('full_name'),
            phone=data.get('phone')
        )
        db.session.add(profile)
        db.session.commit()

        return new_user.to_dict(), 201


@admin_ns.route('/users/<int:user_id>')
class UserDetail(Resource):
    @jwt_required()
    @admin_required
    def get(self, user_id):
        """Get a single user"""
        user = User.query.get_or_404(user_id)
        return user.to_dict(), 200

    @jwt_required()
    @admin_required
    @admin_ns.doc(body=None)
    def put(self, user_id):
        """Update a user's profile (admin)"""
        from app.models import UserProfile

        user = User.query.get_or_404(user_id)
        data = request.get_json()

        # Update email
        new_email = data.get('email', '').strip()
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                return {'message': 'Email already in use by another account'}, 400
            user.email = new_email

        # Update role
        if 'role' in data and data['role'] in ['admin', 'staff', 'rider', 'customer']:
            user.role = data['role']

        # Update active status
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        # Reset password (admin can do this without current password)
        if data.get('new_password', '').strip():
            user.password = data['new_password'].strip()

        # Update profile
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
            db.session.add(user.profile)

        if 'full_name' in data:
            user.profile.full_name = data['full_name'].strip()
        if 'phone' in data:
            user.profile.phone = data['phone'].strip()

        db.session.commit()
        return user.to_dict(), 200

    @jwt_required()
    @admin_required
    def delete(self, user_id):
        """Deactivate a user (soft delete)"""
        user = User.query.get_or_404(user_id)
        user.is_active = False
        db.session.commit()
        return {'message': 'User deactivated'}, 200


# ─── Customers (for admin order creation) ────────────────────────────────────

@admin_ns.route('/customers')
class AdminCustomerList(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """List all customers with their addresses"""
        customers = User.query.filter_by(role='customer').all()
        result = []
        for c in customers:
            d = c.to_dict()
            d['addresses'] = [a.to_dict() for a in c.addresses.all()]
            result.append(d)
        return result, 200


# ─── Items ────────────────────────────────────────────────────────────────────

@admin_ns.route('/items')
class ItemList(Resource):
    def get(self):
        """Get all laundry items"""
        from app.models.items import LaundryItem
        items = LaundryItem.query.all()
        return [item.to_dict() for item in items], 200

    @jwt_required()
    @admin_required
    @admin_ns.doc(body=None)
    def post(self):
        """Create a new laundry item"""
        from app.models.items import LaundryItem

        try:
            data = request.get_json()

            def to_float(val):
                if val == "" or val is None:
                    return 0.0
                return float(val)

            new_item = LaundryItem(
                name=data.get('name'),
                category=data.get('category', 'Clothing'),
                price_wash=to_float(data.get('price_wash')),
                price_dryclean=to_float(data.get('price_dryclean')),
                price_iron=to_float(data.get('price_iron'))
            )
            db.session.add(new_item)
            db.session.commit()
            return new_item.to_dict(), 201
        except ValueError:
            return {'message': 'Invalid price format'}, 400
        except Exception as e:
            return {'message': str(e)}, 500


@admin_ns.route('/items/<int:item_id>')
class ItemResource(Resource):
    @jwt_required()
    @admin_required
    def put(self, item_id):
        """Update a laundry item"""
        from app.models.items import LaundryItem

        item = LaundryItem.query.get_or_404(item_id)
        try:
            data = request.get_json()

            def to_float(val):
                if val == "" or val is None:
                    return 0.0
                return float(val)

            item.name = data.get('name', item.name)
            item.category = data.get('category', item.category)
            item.price_wash = to_float(data.get('price_wash'))
            item.price_dryclean = to_float(data.get('price_dryclean'))
            item.price_iron = to_float(data.get('price_iron'))

            db.session.commit()
            return item.to_dict(), 200
        except ValueError:
            return {'message': 'Invalid price format'}, 400
        except Exception as e:
            return {'message': str(e)}, 500

    @jwt_required()
    @admin_required
    def delete(self, item_id):
        """Delete a laundry item"""
        from app.models.items import LaundryItem
        item = LaundryItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        return {'message': 'Item deleted successfully'}, 200


# ─── Orders ───────────────────────────────────────────────────────────────────

@admin_ns.route('/orders')
class AdminOrderList(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """Get all orders"""
        orders = Order.query.order_by(Order.created_at.desc()).all()
        result = []
        for o in orders:
            d = o.to_dict()
            d['customer_email'] = o.customer.email
            d['customer_name'] = (
                o.customer.profile.full_name
                if o.customer.profile and o.customer.profile.full_name
                else o.customer.email.split('@')[0]
            )
            if o.rider:
                d['rider_email'] = o.rider.email
                d['rider_name'] = (
                    o.rider.profile.full_name
                    if o.rider.profile and o.rider.profile.full_name
                    else o.rider.email.split('@')[0]
                )
            result.append(d)
        return result, 200

    @jwt_required()
    @admin_required
    @admin_ns.doc(body=None)
    def post(self):
        """Admin creates an order on behalf of a customer"""
        current_admin_id = get_jwt_identity()
        data = request.get_json()

        customer_id = data.get('customer_id')
        customer = User.query.get(customer_id)
        if not customer or customer.role != 'customer':
            return {'message': 'Invalid customer'}, 400

        items_data = data.get('items', [])
        if not items_data:
            return {'message': 'At least one item required'}, 400

        pickup_address_id = data.get('pickup_address_id')
        if pickup_address_id:
            addr = Address.query.get(pickup_address_id)
            if not addr or addr.user_id != customer.id:
                return {'message': 'Invalid address for this customer'}, 400
        else:
            # Auto-create address from provided fields
            addr_data = data.get('address')
            if not addr_data:
                return {'message': 'Pickup address required'}, 400
            addr = Address(
                user_id=customer.id,
                street=addr_data.get('street', ''),
                city=addr_data.get('city', ''),
                state=addr_data.get('state', ''),
                zip_code=addr_data.get('zip_code', ''),
                is_default=False
            )
            db.session.add(addr)
            db.session.flush()
            pickup_address_id = addr.id

        total_amount = sum(
            float(item.get('price', 0)) * int(item.get('quantity', 1))
            for item in items_data
        )

        tracking_id = 'ORD-' + ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )

        pickup_time = None
        if data.get('pickup_time'):
            try:
                pickup_time = datetime.datetime.fromisoformat(data['pickup_time'])
            except Exception:
                pickup_time = None

        new_order = Order(
            customer_id=customer.id,
            tracking_id=tracking_id,
            total_amount=total_amount,
            pickup_address_id=pickup_address_id,
            pickup_time=pickup_time,
            created_by_admin=True,
        )
        db.session.add(new_order)
        db.session.flush()

        for item_data in items_data:
            item = OrderItem(
                order_id=new_order.id,
                item_name=item_data['item_name'],
                quantity=int(item_data.get('quantity', 1)),
                service_type=item_data['service_type'],
                price_per_item=float(item_data['price'])
            )
            db.session.add(item)

        db.session.commit()

        # Email customer
        try:
            send_email(
                customer.email,
                f'Order Confirmation - {new_order.tracking_id}',
                'email/order_confirmation.html',
                order=new_order
            )
        except Exception as e:
            print(f"Customer order email failed: {e}")

        # Email all admins
        try:
            _notify_admins_new_order(new_order, placed_by='Admin')
        except Exception as e:
            print(f"Admin new-order email failed: {e}")

        return new_order.to_dict(), 201


@admin_ns.route('/orders/<int:id>')
class AdminOrderDetail(Resource):
    @jwt_required()
    @admin_required
    def get(self, id):
        """Get full order details"""
        order = Order.query.get_or_404(id)
        data = order.to_dict()
        data['items'] = [i.to_dict() for i in order.items]
        data['customer'] = order.customer.to_dict()
        data['rider'] = order.rider.to_dict() if order.rider else None
        data['payments'] = [p.to_dict() for p in order.payments.order_by(Payment.created_at.asc())]
        if order.pickup_address_id:
            addr = Address.query.get(order.pickup_address_id)
            data['pickup_address'] = addr.to_dict() if addr else None
        return data, 200


# ─── Payments ─────────────────────────────────────────────────────────────────

@admin_ns.route('/orders/<int:id>/payments')
class AdminOrderPayments(Resource):
    @jwt_required()
    @admin_required
    def get(self, id):
        """Get payment history for an order"""
        order = Order.query.get_or_404(id)
        return {
            'order_id': order.id,
            'tracking_id': order.tracking_id,
            'total_amount': order.total_amount,
            'amount_paid': order.amount_paid or 0.0,
            'balance_due': order.balance_due,
            'payment_status': order.payment_status or 'Unpaid',
            'payments': [p.to_dict() for p in order.payments.order_by(Payment.created_at.asc())]
        }, 200

    @jwt_required()
    @admin_required
    @admin_ns.doc(body=None)
    def post(self, id):
        """Record a payment (full or partial) for an order"""
        current_admin_id = get_jwt_identity()
        data = request.get_json()
        order = Order.query.get_or_404(id)

        amount = float(data.get('amount', 0))
        if amount <= 0:
            return {'message': 'Amount must be greater than zero'}, 400

        balance = order.balance_due
        if amount > balance + 0.01:  # small float tolerance
            return {
                'message': f'Payment amount ₦{amount:,.2f} exceeds balance due ₦{balance:,.2f}'
            }, 400

        # Generate unique reference
        ref = 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        payment = Payment(
            order_id=order.id,
            amount=amount,
            status='Completed',
            payment_method=data.get('payment_method', 'Cash'),
            note=data.get('note', ''),
            reference=ref,
            recorded_by_id=int(current_admin_id)
        )
        db.session.add(payment)

        # Update order totals
        order.amount_paid = (order.amount_paid or 0.0) + amount
        if order.amount_paid >= order.total_amount - 0.01:
            order.payment_status = 'Paid'
        elif order.amount_paid > 0:
            order.payment_status = 'Part Paid'
        else:
            order.payment_status = 'Unpaid'

        db.session.commit()

        return {
            'message': 'Payment recorded successfully',
            'payment': payment.to_dict(),
            'order_summary': {
                'total_amount': order.total_amount,
                'amount_paid': order.amount_paid,
                'balance_due': order.balance_due,
                'payment_status': order.payment_status
            }
        }, 201


# ─── Assign Rider ─────────────────────────────────────────────────────────────

@admin_ns.route('/orders/<int:id>/assign')
class AdminOrderAssign(Resource):
    @jwt_required()
    @admin_required
    def put(self, id):
        """Assign rider to order"""
        data = request.get_json()
        rider_id = data.get('rider_id')

        order = Order.query.get_or_404(id)
        rider = User.query.get_or_404(rider_id)

        if rider.role != 'rider':
            return {'message': 'User is not a rider'}, 400

        order.rider_id = rider.id
        order.status = 'Rider Assigned'
        db.session.commit()
        return {'message': 'Rider assigned successfully'}, 200


# ─── Riders ───────────────────────────────────────────────────────────────────

@admin_ns.route('/riders')
class AdminRiderList(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """Get all available riders"""
        riders = User.query.filter_by(role='rider').all()
        return [r.to_dict() for r in riders], 200


# ─── Settings ─────────────────────────────────────────────────────────────────

@admin_ns.route('/settings')
class AdminSettings(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """Get system settings"""
        from app.models.settings import SystemSetting
        commission = SystemSetting.get_value('rider_commission_rate', '0.15')
        admin_email = SystemSetting.get_value('admin_notification_email', '')
        return {
            'rider_commission_rate': float(commission),
            'admin_notification_email': admin_email,
        }, 200

    @jwt_required()
    @admin_required
    def put(self):
        """Update system settings"""
        from app.models.settings import SystemSetting

        data = request.get_json()

        if 'rider_commission_rate' in data:
            try:
                rate = float(data['rider_commission_rate'])
                if not (0 <= rate <= 1):
                    return {'message': 'Commission rate must be between 0 and 1'}, 400
                SystemSetting.set_value(
                    'rider_commission_rate', str(rate),
                    description='Global Rider Commission Rate'
                )
            except ValueError:
                return {'message': 'Invalid rate format'}, 400

        if 'admin_notification_email' in data:
            SystemSetting.set_value(
                'admin_notification_email',
                data['admin_notification_email'],
                description='Email address to receive new-order notifications'
            )

        return {'message': 'Settings updated successfully'}, 200


# ─── Finance ──────────────────────────────────────────────────────────────────

@admin_ns.route('/finance/riders')
class AdminFinanceRiders(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """Get rider wallet balances"""
        from app.models.finance import RiderTransaction

        riders = User.query.filter_by(role='rider').all()
        result = []

        for rider in riders:
            balance = db.session.query(
                func.sum(RiderTransaction.amount)
            ).filter_by(rider_id=rider.id).scalar() or 0.0

            result.append({
                'id': rider.id,
                'email': rider.email,
                'name': rider.profile.full_name if rider.profile and rider.profile.full_name else 'N/A',
                'balance': balance,
                'active_tasks': rider.assigned_orders.filter(
                    Order.status.notin_(['Delivered', 'Cancelled'])
                ).count()
            })

        return result, 200


@admin_ns.route('/finance/payout')
class AdminFinancePayout(Resource):
    @jwt_required()
    @admin_required
    def post(self):
        """Create a payout transaction"""
        from app.models.finance import RiderTransaction
        import time

        data = request.get_json()
        rider_id = data.get('rider_id')
        amount = float(data.get('amount', 0))
        note = data.get('note', 'Admin Payout')

        if amount <= 0:
            return {'message': 'Amount must be positive'}, 400

        payout_tx = RiderTransaction(
            rider_id=rider_id,
            amount=-amount,
            type='PAYOUT',
            description=note,
            reference_id=f'PAY-{int(time.time())}'
        )

        db.session.add(payout_tx)
        db.session.commit()

        return {'message': 'Payout processed successfully'}, 201


@admin_ns.route('/finance/history/<int:rider_id>')
class AdminFinanceHistory(Resource):
    @jwt_required()
    @admin_required
    def get(self, rider_id):
        """Get transaction history for a rider"""
        from app.models.finance import RiderTransaction

        txs = RiderTransaction.query.filter_by(rider_id=rider_id).order_by(
            RiderTransaction.created_at.desc()
        ).all()
        return [t.to_dict() for t in txs], 200


# ─── Revenue Report ───────────────────────────────────────────────────────────

@admin_ns.route('/reports/revenue')
class RevenueReport(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """
        Revenue report filterable by:
          ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
          &customer_id=INT
          &payment_method=Cash|Transfer|POS|Card
          &status=Unpaid|Part Paid|Paid
        """
        from app.models.order import Payment

        date_from      = request.args.get('date_from')
        date_to        = request.args.get('date_to')
        customer_id    = request.args.get('customer_id')
        payment_method = request.args.get('payment_method')
        pay_status     = request.args.get('status')

        # Base query — join Order + Payment
        query = db.session.query(Order).order_by(Order.created_at.desc())

        if date_from:
            try:
                df = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Order.created_at >= df)
            except ValueError:
                pass

        if date_to:
            try:
                dt = datetime.datetime.strptime(date_to, '%Y-%m-%d')
                dt = dt.replace(hour=23, minute=59, second=59)
                query = query.filter(Order.created_at <= dt)
            except ValueError:
                pass

        if customer_id:
            query = query.filter(Order.customer_id == int(customer_id))

        if pay_status:
            query = query.filter(Order.payment_status == pay_status)

        # Filter by payment_method means only orders that have at least one payment
        # with that method — do a subquery
        if payment_method:
            sub = db.session.query(Payment.order_id).filter(
                Payment.payment_method == payment_method
            ).subquery()
            query = query.filter(Order.id.in_(sub))

        orders = query.all()

        rows = []
        total_billed   = 0.0
        total_received = 0.0
        total_balance  = 0.0

        for o in orders:
            customer_name = (
                o.customer.profile.full_name
                if o.customer.profile and o.customer.profile.full_name
                else o.customer.email.split('@')[0]
            )

            # Payment methods used for this order
            methods = list({p.payment_method for p in o.payments})

            row = {
                'order_id':       o.id,
                'tracking_id':    o.tracking_id or f'#{o.id}',
                'date':           o.created_at.strftime('%Y-%m-%d %H:%M'),
                'customer_name':  customer_name,
                'customer_email': o.customer.email,
                'items_count':    o.items.count(),
                'order_status':   o.status,
                'total_amount':   o.total_amount,
                'amount_paid':    o.amount_paid or 0.0,
                'balance_due':    o.balance_due,
                'payment_status': o.payment_status or 'Unpaid',
                'payment_methods': ', '.join(methods) if methods else '—',
                'created_by_admin': o.created_by_admin or False,
            }
            rows.append(row)
            total_billed   += o.total_amount
            total_received += o.amount_paid or 0.0
            total_balance  += o.balance_due

        return {
            'rows': rows,
            'summary': {
                'total_orders':   len(rows),
                'total_billed':   total_billed,
                'total_received': total_received,
                'total_balance':  total_balance,
            }
        }, 200


# ─── Helper: notify admins on new order ──────────────────────────────────────

def _notify_admins_new_order(order, placed_by='Customer'):
    """Send new-order notification email to all admin users + settings email."""
    from app.models.settings import SystemSetting

    recipients = set()

    # All admin users
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        recipients.add(admin.email)

    # Optional extra email from settings
    extra = SystemSetting.get_value('admin_notification_email', '').strip()
    if extra:
        recipients.add(extra)

    for email in recipients:
        try:
            send_email(
                email,
                f'New Order Placed - {order.tracking_id}',
                'email/admin_new_order.html',
                order=order,
                placed_by=placed_by
            )
        except Exception as e:
            print(f"Admin notification to {email} failed: {e}")
