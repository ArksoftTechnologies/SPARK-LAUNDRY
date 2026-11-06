from app import create_app, db
from app.models import User, UserProfile, Address

app = create_app()

def seed_users():
    with app.app_context():
        print("Creating database tables if they don't exist...")
        db.create_all()
        print("Creating seed users...")
        
        # 1. Admin User
        if not User.query.filter_by(email='admin@spark.com').first():
            admin = User(email='admin@spark.com', role='admin', is_active=True)
            admin.password = 'password123'
            admin.profile = UserProfile(full_name='System Administrator', phone='08000000000')
            db.session.add(admin)
            print("Created Admin: admin@spark.com / password123")
            
        # 2. Staff User
        if not User.query.filter_by(email='staff@spark.com').first():
            staff = User(email='staff@spark.com', role='staff', is_active=True)
            staff.password = 'password123'
            staff.profile = UserProfile(full_name='Sarah Staff', phone='08011111111')
            db.session.add(staff)
            print("Created Staff: staff@spark.com / password123")

        # 3. Rider User
        if not User.query.filter_by(email='rider@spark.com').first():
            rider = User(email='rider@spark.com', role='rider', is_active=True)
            rider.password = 'password123'
            rider.profile = UserProfile(full_name='Ralph Rider', phone='08022222222')
            db.session.add(rider)
            print("Created Rider: rider@spark.com / password123")
            
        # 4. Customer User (with address)
        if not User.query.filter_by(email='customer@spark.com').first():
            customer = User(email='customer@spark.com', role='customer', is_active=True)
            customer.password = 'password123'
            customer.profile = UserProfile(full_name='Charlie Customer', phone='08033333333')
            
            # Add default address for testing orders
            addr = Address(
                street='123 Spark Avenue, VI',
                city='Lagos',
                state='Lagos',
                zip_code='100001',
                is_default=True
            )
            customer.addresses.append(addr)
            
            db.session.add(customer)
            print("Created Customer: customer@spark.com / password123")

        db.session.commit()
        print("Seed complete!")

if __name__ == '__main__':
    seed_users()
