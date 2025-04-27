from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio_data = db.relationship('PortfolioData', backref='user', lazy='dynamic')
    cost_income_entries = db.relationship('CostIncomeEntry', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class PortfolioData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    data = db.Column(db.Text)  # JSON data stored as text
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_data(self):
        """Convert JSON string to Python dictionary"""
        return json.loads(self.data)
    
    def set_data(self, portfolio_dict):
        """Convert Python dictionary to JSON string"""
        self.data = json.dumps(portfolio_dict)
        self.updated_at = datetime.utcnow()
        
class CostIncomeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date)
    type = db.Column(db.String(10))  # 'income' or 'outcome'
    amount = db.Column(db.Float)
    category = db.Column(db.String(64))
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)