from app import db

class LaundryItem(db.Model):
    __tablename__ = 'laundry_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Clothing') # Clothing, Household, Bedding
    price_wash = db.Column(db.Float, default=0.0)
    price_dryclean = db.Column(db.Float, default=0.0)
    price_iron = db.Column(db.Float, default=0.0)
    image_url = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price_wash': self.price_wash,
            'price_dryclean': self.price_dryclean,
            'price_iron': self.price_iron,
            'image_url': self.image_url
        }
