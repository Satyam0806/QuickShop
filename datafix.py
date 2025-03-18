from app import app, db
from models import User  # Make sure to import your User model
from werkzeug.security import generate_password_hash

def recreate_database():
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        
        # Create all tables with the new schema
        db.create_all()
        
        # Create an admin user with the new column
        admin_password = generate_password_hash('your_admin_password')  # Use a secure password
        admin = User(
            username='admin', 
            password=admin_password,
            is_admin=True,
            is_delivery_partner=False  # Add this new column
        )
        
        # Add and commit the admin user
        db.session.add(admin)
        db.session.commit()

    print("Database recreated successfully!")

if __name__ == '__main__':
    recreate_database()