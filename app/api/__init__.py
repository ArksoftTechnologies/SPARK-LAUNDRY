from flask import Blueprint
from flask_restx import Api

from .auth import auth_ns
from .customer import customer_ns
from .staff import staff_ns
from .rider import rider_ns
from .admin import admin_ns

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint, 
          title='Laundry Service API', 
          version='1.0', 
          description='API for the Premium Laundry Management System',
          doc='/docs')

api.add_namespace(auth_ns, path='/auth')
api.add_namespace(customer_ns, path='/customer')
api.add_namespace(staff_ns, path='/staff')
api.add_namespace(rider_ns, path='/rider')
api.add_namespace(admin_ns, path='/admin')
