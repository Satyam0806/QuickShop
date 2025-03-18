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
    # Add gender_tag column
    gender_tag = db.Column(db.String(20), nullable=True)
    # Existing fields
    size = db.Column(db.String(10), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Add a relationship to the admin user
    admin = db.relationship('User', backref='products')
    
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
    # Add admin_id to track which admin is assigned to this order
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Add relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='orders')
    assigned_admin = db.relationship('User', foreign_keys=[assigned_admin_id], backref='assigned_orders')
    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Store price at time of purchase

