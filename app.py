from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from sqlalchemy import text
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

def create_users():
    # Create all tables first
    db.create_all()
    
    # List of users to create or update
    users_to_create = [
        {
            'username': 'admin',
            'password': 'admin123',
            'is_admin': True,
            'is_delivery_partner': False
        },
        {
            'username': 'admin2',
            'password': 'admin456',
            'is_admin': True,
            'is_delivery_partner': False
        },
        {
            'username': 'admin3',
            'password': 'admin789',
            'is_admin': True,
            'is_delivery_partner': False
        },
        {
            'username': 'customer',
            'password': 'password123',
            'is_admin': False,
            'is_delivery_partner': False
        },
        {
            'username': 'delivery',
            'password': 'delivery123',
            'is_admin': False,
            'is_delivery_partner': True
        }
    ]
    
    # Try to add gender column safely
    try:
        # Check if gender column exists
        db.session.execute(text("SELECT gender FROM user LIMIT 1"))
        print("Gender column already exists")
    except Exception as e:
        try:
            # Add gender column if it doesn't exist
            db.session.execute(text("ALTER TABLE user ADD COLUMN gender VARCHAR(10)"))
            db.session.commit()
            print("Added gender column to user table")
        except Exception as alter_error:
            print(f"Error adding gender column: {alter_error}")
    
    # Create or update users
    for user_data in users_to_create:
        try:
            # Try to find existing user
            existing_user = User.query.filter_by(username=user_data['username']).first()
            
            if existing_user:
                # Update existing user to ensure correct admin status
                existing_user.is_admin = user_data['is_admin']
                existing_user.is_delivery_partner = user_data['is_delivery_partner']
                print(f"Updated user: {user_data['username']}")
            else:
                # Create new user if not exists
                new_user = User(
                    username=user_data['username'],
                    password=generate_password_hash(user_data['password']),
                    is_admin=user_data['is_admin'],
                    is_delivery_partner=user_data['is_delivery_partner']
                )
                db.session.add(new_user)
                print(f"Created user: {user_data['username']}")
        
        except Exception as user_error:
            print(f"Error creating/updating user {user_data['username']}: {user_error}")
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as commit_error:
        print(f"Error committing changes: {commit_error}")
        db.session.rollback()
    
    # Print all existing users for verification
    print("\nExisting Users:")
    users = User.query.all()
    for user in users:
        print(f"Username: {user.username}, Is Admin: {user.is_admin}, Is Delivery Partner: {user.is_delivery_partner}")

# Run user creation within app context
with app.app_context():
    create_users()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
