import sys
import os
import json
import pandas as pd
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, PortfolioData, CostIncomeEntry
from werkzeug.security import generate_password_hash

# Initialize the Flask application
app = create_app()

def create_admin_user():
    """Create an admin user if no users exist"""
    with app.app_context():
        # Check if any users exist
        if User.query.count() == 0:
            print("Creating admin user...")
            
            # Create admin user
            admin = User(
                username="admin",
                email="admin@example.com"
            )
            admin.set_password("adminpassword")
            
            # Add to database
            db.session.add(admin)
            db.session.commit()
            
            print(f"Admin user created with ID: {admin.id}")
            return admin
        else:
            print("Users already exist, skipping admin creation")
            return User.query.first()

def import_portfolio_data(user_id):
    """Import portfolio data from JSON file"""
    with app.app_context():
        # Check if portfolio already exists for user
        existing_portfolio = PortfolioData.query.filter_by(user_id=user_id).first()
        if existing_portfolio:
            print(f"Portfolio data already exists for user {user_id}")
            return False
        
        # Path to portfolio data
        json_path = os.path.join(app.root_path, 'data', 'portfolio_data.json')
        
        # Check if file exists
        if not os.path.exists(json_path):
            print(f"Portfolio data file not found at {json_path}")
            return False
        
        try:
            # Read portfolio data
            with open(json_path, 'r') as file:
                portfolio_data = json.load(file)
            
            # Create portfolio entry
            portfolio = PortfolioData(user_id=user_id)
            portfolio.set_data(portfolio_data)
            
            # Save to database
            db.session.add(portfolio)
            db.session.commit()
            
            print(f"Portfolio data imported for user {user_id}")
            return True
        except Exception as e:
            print(f"Error importing portfolio data: {e}")
            return False

def import_costincome_data(user_id):
    """Import cost/income data from CSV file"""
    with app.app_context():
        # Check if any entries already exist for user
        existing_entries = CostIncomeEntry.query.filter_by(user_id=user_id).count()
        if existing_entries > 0:
            print(f"Cost/income data already exists for user {user_id} ({existing_entries} entries)")
            return False
        
        # Path to cost/income data
        csv_path = os.path.join(app.root_path, 'data', 'costincome.csv')
        
        # Check if file exists
        if not os.path.exists(csv_path):
            print(f"Cost/income data file not found at {csv_path}")
            return False
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Check for required columns
            required_columns = ['date', 'type', 'amount', 'category']
            if not all(col in df.columns for col in required_columns):
                print(f"Required columns missing in CSV file")
                return False
            
            entries_count = 0
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    # Convert date string to date object
                    date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    
                    # Create entry
                    entry = CostIncomeEntry(
                        user_id=user_id,
                        date=date_obj,
                        type=row['type'],
                        amount=float(row['amount']),
                        category=row['category'],
                        description=row.get('description', '')
                    )
                    
                    # Add to database
                    db.session.add(entry)
                    entries_count += 1
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
            
            # Commit changes
            db.session.commit()
            
            print(f"Cost/income data imported for user {user_id} ({entries_count} entries)")
            return True
        except Exception as e:
            print(f"Error importing cost/income data: {e}")
            db.session.rollback()
            return False

def create_test_users():
    """Create test users with separate data"""
    with app.app_context():
        # Create first test user
        user1 = User.query.filter_by(username="user1").first()
        if not user1:
            user1 = User(
                username="user1",
                email="user1@example.com"
            )
            user1.set_password("password1")
            db.session.add(user1)
            db.session.commit()
            print(f"Test user1 created with ID: {user1.id}")
        
        # Create second test user
        user2 = User.query.filter_by(username="user2").first()
        if not user2:
            user2 = User(
                username="user2",
                email="user2@example.com"
            )
            user2.set_password("password2")
            db.session.add(user2)
            db.session.commit()
            print(f"Test user2 created with ID: {user2.id}")
        
        return user1, user2

def main():
    """Main function to run all setup tasks"""
    print("Starting initial setup...")
    
    # Create admin user
    admin = create_admin_user()
    
    # Import data for admin user
    import_portfolio_data(admin.id)
    import_costincome_data(admin.id)
    
    # Create test users
    user1, user2 = create_test_users()
    
    # Clone admin's portfolio data for user1 (with modifications)
    admin_portfolio = PortfolioData.query.filter_by(user_id=admin.id).first()
    if admin_portfolio:
        # Get admin's portfolio data
        portfolio_data = admin_portfolio.get_data()
        
        # Modify portfolio data for user1
        if 'etf' in portfolio_data:
            for etf in portfolio_data['etf']:
                etf['amount'] = etf['amount'] * 0.5  # Half the amount
                etf['acquisition_cost'] = etf['acquisition_cost'] * 0.5
        
        # Create portfolio for user1
        user1_portfolio = PortfolioData(user_id=user1.id)
        user1_portfolio.set_data(portfolio_data)
        db.session.add(user1_portfolio)
        db.session.commit()
        print(f"Portfolio data cloned for user1")
    
    # Create empty portfolio for user2
    empty_portfolio = {
        "etf": [],
        "stocks": [],
        "bonds": [],
        "commodities": [],
        "realEstate": [],
        "savings": [
            {
                "name": "Sparbuch",
                "amount": 2000,
                "interest_rate": 0.01,
                "currency": "EUR",
                "acquisition_cost": 2000
            }
        ]
    }
    user2_portfolio = PortfolioData(user_id=user2.id)
    user2_portfolio.set_data(empty_portfolio)
    db.session.add(user2_portfolio)
    db.session.commit()
    print(f"Empty portfolio created for user2")
    
    # Split cost/income data between user1 and user2
    admin_entries = CostIncomeEntry.query.filter_by(user_id=admin.id).all()
    
    for i, entry in enumerate(admin_entries):
        # Copy even entries to user1, odd entries to user2
        new_entry = CostIncomeEntry(
            user_id=user1.id if i % 2 == 0 else user2.id,
            date=entry.date,
            type=entry.type,
            amount=entry.amount,
            category=entry.category,
            description=entry.description
        )
        db.session.add(new_entry)
    
    db.session.commit()
    print(f"Cost/income data divided between user1 and user2")
    
    print("Initial setup completed successfully!")

if __name__ == "__main__":
    main()