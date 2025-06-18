from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_test_user():
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username='test').first()
        if existing_user:
            print("User 'test' already exists!")
            return
        
        # Create new user
        test_user = User(
            username='test',
            email='test@example.com',
            password_hash=generate_password_hash('test123'),
            clasa='10'  # Set default class to 10
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        print("Test user created successfully!")
        print("Username: test")
        print("Password: test123")
        print("Class: 10")

if __name__ == "__main__":
    create_test_user() 