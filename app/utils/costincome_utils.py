import pandas as pd
import os
from datetime import datetime
from app import db
from app.models import CostIncomeEntry, User
from flask import current_app

def import_costincome_from_csv(user_id, csv_path):
    """Import cost/income data from a CSV file for a specific user"""
    try:
        # Check if file exists
        if not os.path.exists(csv_path):
            return False
            
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Check for required columns
        required_columns = ['date', 'type', 'amount', 'category', 'description']
        if not all(col in df.columns for col in required_columns):
            return False
            
        # Process each row
        for _, row in df.iterrows():
            # Convert date string to date object
            try:
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
            except ValueError:
                # Skip rows with invalid dates
                continue
                
            # Check if this entry already exists
            existing_entry = CostIncomeEntry.query.filter_by(
                user_id=user_id,
                date=date_obj,
                type=row['type'],
                amount=row['amount'],
                category=row['category']
            ).first()
            
            if existing_entry is None:
                # Create new entry
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
        
        # Commit all changes
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error importing cost/income data: {e}")
        db.session.rollback()
        return False

def export_costincome_to_csv(user_id, output_path):
    """Export a user's cost/income data to a CSV file"""
    try:
        # Get user's entries
        entries = CostIncomeEntry.query.filter_by(user_id=user_id).all()
        
        if not entries:
            return False
            
        # Convert to DataFrame
        data = []
        for entry in entries:
            data.append({
                'id': entry.id,
                'date': entry.date.strftime('%Y-%m-%d'),
                'type': entry.type,
                'amount': entry.amount,
                'category': entry.category,
                'description': entry.description
            })
            
        df = pd.DataFrame(data)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to CSV file
        df.to_csv(output_path, index=False)
        
        return True
    except Exception as e:
        print(f"Error exporting cost/income data: {e}")
        return False

def migrate_existing_costincome_data():
    """Migrate existing cost/income data from the CSV file to the database for all users"""
    try:
        # Get the path to the existing CSV file
        csv_path = os.path.join(current_app.root_path, 'data', 'costincome.csv')
        
        # Check if the file exists
        if not os.path.exists(csv_path):
            return False
            
        # Get all users
        users = User.query.all()
        
        if not users:
            return False
            
        # For demo purposes, import all data for the first user only
        first_user = users[0]
        
        return import_costincome_from_csv(first_user.id, csv_path)
    except Exception as e:
        print(f"Error migrating cost/income data: {e}")
        return False