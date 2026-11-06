from functools import wraps
from flask_jwt_extended import get_jwt

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return {'message': 'Admins only!'}, 403
        return fn(*args, **kwargs)
    return wrapper

def customer_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'customer':
            return {'message': 'Customers only!'}, 403
        return fn(*args, **kwargs)
    return wrapper

def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        role = claims.get('role')
        if role not in ['staff', 'admin']:
            return {'message': 'Staff only!'}, 403
        return fn(*args, **kwargs)
    return wrapper
