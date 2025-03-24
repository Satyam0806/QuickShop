from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def reset_admin_passwords():
    with app.app_context():
        admin_users = User.query.filter_by(is_admin=True).all()
        
        if not admin_users:
            print("No admin users found.")
            return
        
        print("Resetting passwords for admin users:")
        
        for admin in admin_users:
            try:
                passwords = {
                    'admin': 'admin123',
                    'admin2': 'admin456',
                    'admin3': 'admin789',
                }
                
                password = passwords.get(admin.username, 'admindefault')
                
                admin.is_admin = True
                admin.is_delivery_partner = False
                admin.password = generate_password_hash(password)
                
                print(f"\nUpdating admin user: {admin.username}")
                print(f"New password set to: {password}")
                print(f"Is Admin: {admin.is_admin}")
                print(f"Is Delivery Partner: {admin.is_delivery_partner}")
            
            except Exception as e:
                print(f"Error updating {admin.username}: {e}")
        
        try:
            db.session.commit()
            print("\nAll admin passwords reset successfully")
        except Exception as commit_error:
            print(f"Error committing changes: {commit_error}")
            db.session.rollback()
        
        print("\nVerifying updated admin users:")
        updated_admins = User.query.filter_by(is_admin=True).all()
        for admin in updated_admins:
            print(f"Username: {admin.username}")
            print(f"Is Admin: {admin.is_admin}")
            print(f"Is Delivery Partner: {admin.is_delivery_partner}")
            print("---")

def create_missing_admin_users():
    with app.app_context():
        admin_users_to_create = [
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
            }
        ]
        
        for user_data in admin_users_to_create:
            existing_user = User.query.filter_by(username=user_data['username']).first()
            
            if not existing_user:
                new_admin = User(
                    username=user_data['username'],
                    password=generate_password_hash(user_data['password']),
                    is_admin=user_data['is_admin'],
                    is_delivery_partner=user_data['is_delivery_partner']
                )
                
                try:
                    db.session.add(new_admin)
                    print(f"Created missing admin user: {user_data['username']}")
                except Exception as e:
                    print(f"Error creating {user_data['username']}: {e}")
            else:
                print(f"Admin user {user_data['username']} already exists")
        
        try:
            db.session.commit()
            print("Admin user creation/verification complete")
        except Exception as commit_error:
            print(f"Error committing changes: {commit_error}")
            db.session.rollback()

def comprehensive_admin_reset():
    print("Starting comprehensive admin user reset...")
    
    create_missing_admin_users()
    
    reset_admin_passwords()

if __name__ == '__main__':
    comprehensive_admin_reset()
