from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    clasa = db.Column(db.String(10), default='9')
    
    # Premium fields
    is_premium = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime)
    premium_granted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    premium_granted_at = db.Column(db.DateTime)
    premium_reason = db.Column(db.String(200))  # "admin_grant", "existing_user", etc.

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_premium_active(self):
        """Check if user has active premium subscription"""
        if not self.is_premium:
            return False
        if self.premium_until and datetime.utcnow() > self.premium_until:
            self.is_premium = False
            db.session.commit()
            return False
        return True
    
    def grant_premium(self, granted_by_id, duration_days=365, reason="admin_grant"):
        """Grant premium to user"""
        from datetime import timedelta
        self.is_premium = True
        self.premium_until = datetime.utcnow() + timedelta(days=duration_days)
        self.premium_granted_by = granted_by_id
        self.premium_granted_at = datetime.utcnow()
        self.premium_reason = reason
        db.session.commit()
    
    def revoke_premium(self):
        """Revoke premium from user"""
        self.is_premium = False
        self.premium_until = None
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>' 