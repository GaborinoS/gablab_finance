import json
import os
from app import db
from app.models import PortfolioData, User
from flask import current_app
from flask_login import current_user

def create_default_portfolio(user_id):
    """Create a default portfolio for a new user"""
    try:
        # Define default portfolio
        default_portfolio = {
            "etf": [
                {
                    "ticker": "EUNL.DE",
                    "name": "iShares Core MSCI World UCITS ETF",
                    "currency": "EUR",
                    "isin": "IE00B4L5Y983",
                    "amount": 0,
                    "acquisition_cost": 0
                }
            ],
            "stocks": [],
            "bonds": [],
            "commodities": [],
            "realEstate": [],
            "savings": [
                {
                    "name": "Sparbuch",
                    "amount": 0,
                    "interest_rate": 0.0,
                    "currency": "EUR",
                    "acquisition_cost": 0
                }
            ]
        }
        
        # Create portfolio entry
        portfolio = PortfolioData(user_id=user_id)
        portfolio.set_data(default_portfolio)
        
        # Save to database
        db.session.add(portfolio)
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error creating default portfolio: {e}")
        return False

def import_portfolio_from_json(user_id, json_path):
    """Import portfolio data from a JSON file for a specific user"""
    try:
        # Check if file exists
        if not os.path.exists(json_path):
            return False
            
        # Read JSON file
        with open(json_path, 'r') as file:
            portfolio_data = json.load(file)
            
        # Create or update portfolio entry
        portfolio = PortfolioData.query.filter_by(user_id=user_id).first()
        
        if portfolio is None:
            portfolio = PortfolioData(user_id=user_id)
            
        portfolio.set_data(portfolio_data)
        
        # Save to database
        db.session.add(portfolio)
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error importing portfolio: {e}")
        return False

def export_portfolio_to_json(user_id, output_path):
    """Export a user's portfolio data to a JSON file"""
    try:
        # Get user's portfolio
        portfolio = PortfolioData.query.filter_by(user_id=user_id).first()
        
        if portfolio is None:
            return False
            
        # Get data as dictionary
        portfolio_data = portfolio.get_data()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to JSON file
        with open(output_path, 'w') as file:
            json.dump(portfolio_data, file, indent=4)
            
        return True
    except Exception as e:
        print(f"Error exporting portfolio: {e}")
        return False

def migrate_existing_portfolio_data():
    """Migrate existing portfolio data from the JSON file to the database for all users"""
    try:
        # Get the path to the existing portfolio data file
        json_path = os.path.join(current_app.root_path, 'data', 'portfolio_data.json')
        
        # Check if the file exists
        if not os.path.exists(json_path):
            return False
            
        # Read the existing data
        with open(json_path, 'r') as file:
            portfolio_data = json.load(file)
            
        # Get all users
        users = User.query.all()
        
        # Import the data for each user
        for user in users:
            # Check if the user already has portfolio data
            existing_portfolio = PortfolioData.query.filter_by(user_id=user.id).first()
            
            if existing_portfolio is None:
                # Create new portfolio entry
                portfolio = PortfolioData(user_id=user.id)
                portfolio.set_data(portfolio_data)
                
                # Save to database
                db.session.add(portfolio)
                
        # Commit all changes
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error migrating portfolio data: {e}")
        return False