from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from models import db, User
from routes import routes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'routes.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(routes)

with app.app_context():
    # Create all tables first - THIS IS THE KEY MISSING PART
    db.create_all()
    
    # Now you can add columns or query tables
    try:
        # Try a simple query that would fail if the column doesn't exist
        db.session.execute("SELECT gender FROM user LIMIT 1")
        print("Gender column exists, skipping modification")
    except:
        try:
            # Column doesn't exist, add it
            db.session.execute("ALTER TABLE user ADD COLUMN gender VARCHAR(10)")
            db.session.commit()
            print("Added gender column to user table")
        except Exception as e:
            print(f"Error adding column: {e}")
            print("Proceeding with existing schema")
    
    # Create main admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            is_admin=True,
            is_delivery_partner=False
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    
    # Create a second admin user if not exists
    admin2 = User.query.filter_by(username='admin2').first()
    if not admin2:
        admin2 = User(
            username='admin2',
            password=generate_password_hash('admin456'),
            is_admin=True,
            is_delivery_partner=False
        )
        db.session.add(admin2)
        db.session.commit()
        print("Second admin user created")

    # Create regular user if not exists
    customer = User.query.filter_by(username='customer').first()
    if not customer:
        customer = User(
            username='customer',
            password=generate_password_hash('password123'),
            is_admin=False,
            is_delivery_partner=False
        )
        db.session.add(customer)
        db.session.commit()
        print("Customer user created")
        
    # Create delivery partner user if not exists
    delivery_partner = User.query.filter_by(username='delivery').first()
    if not delivery_partner:
        delivery_partner = User(
            username='delivery',
            password=generate_password_hash('delivery123'),
            is_admin=False,
            is_delivery_partner=True
        )
        db.session.add(delivery_partner)
        db.session.commit()
        print("Delivery partner user created")

if __name__ == '__main__':
    app.run(debug=True)