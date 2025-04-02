from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_delivery_partner = db.Column(db.Boolean, default=False)  
    gender = db.Column(db.String(10), nullable=True) 
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)
    gender_tag = db.Column(db.String(20), nullable=True)
    size = db.Column(db.String(10), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    inventory_quantity = db.Column(db.Integer, default=10)
    # Add shared product ID field
    shared_product_id = db.Column(db.String(50), nullable=True, index=True)
    
    # Add a relationship to the admin user
    admin = db.relationship('User', backref='products')
    
    # Update this method to find products with the same shared_product_id
    @classmethod
    def find_at_other_outlets(cls, shared_product_id, current_size=None, current_admin_id=None, current_location=None):
        """Find same product at other outlets, possibly in different sizes"""
        query = cls.query.filter(
            cls.shared_product_id == shared_product_id,
            cls.inventory_quantity > 0
        )
        
        # If we want to exclude current size/admin/location
        if current_size and current_admin_id and current_location:
            query = query.filter(db.or_(
                cls.size != current_size,
                cls.admin_id != current_admin_id,
                cls.location != current_location
            ))
            
        return query.all()
    
    # New method to find available sizes at all outlets
    @classmethod
    def find_available_sizes(cls, shared_product_id):
        """Find all available sizes for a product across all outlets"""
        return cls.query.filter(
            cls.shared_product_id == shared_product_id,
            cls.inventory_quantity > 0
        ).with_entities(cls.size, cls.location, cls.admin_id).distinct().all()
    
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, shipped, delivered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Add delivery details
    delivery_fee = db.Column(db.Float, default=5.00)
    tax = db.Column(db.Float, default=0.0)
    estimated_delivery_time = db.Column(db.String(50), default="Delivered within 2 hours")
    # Delivery address fields
    delivery_full_name = db.Column(db.String(100), nullable=True)
    delivery_address_line1 = db.Column(db.String(200), nullable=True)
    delivery_address_line2 = db.Column(db.String(200), nullable=True)
    delivery_city = db.Column(db.String(100), nullable=True)
    delivery_state = db.Column(db.String(100), nullable=True)
    delivery_postal_code = db.Column(db.String(20), nullable=True)
    delivery_phone = db.Column(db.String(20), nullable=True)
        # Payment information fields
    payment_card_name = db.Column(db.String(100), nullable=True)
    payment_card_last4 = db.Column(db.String(4), nullable=True)
    payment_expiry_month = db.Column(db.String(2), nullable=True)
    payment_expiry_year = db.Column(db.String(4), nullable=True)
    
    # Add relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='orders')
    assigned_admin = db.relationship('User', foreign_keys=[assigned_admin_id], backref='assigned_orders')
    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Store the specific store/location for each order item
    store_location = db.Column(db.String(200), nullable=True)
    store_brand = db.Column(db.String(100), nullable=True)  # Zara, Marks & Spencer, etc.
    
    # Relationships
    product = db.relationship('Product')
    order = db.relationship('Order', backref='items')
