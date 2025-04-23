from flask import render_template, request, redirect, url_for, flash
from app.modules.costincome import bp
from datetime import datetime
import os
import csv
import pandas as pd
import traceback

# Ensure the data directory exists
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
CSV_FILE = os.path.join(DATA_DIR, 'costincome.csv')

def ensure_data_file():
    """Ensure the data directory and CSV file exist"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    if not os.path.exists(CSV_FILE):
        # Create new CSV file with headers
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'type', 'amount', 'category', 'description'])

def get_all_entries():
    """Get all entries from the CSV file"""
    ensure_data_file()
    try:
        df = pd.read_csv(CSV_FILE)
        return df.sort_values(by=['date', 'id'], ascending=[False, False]).to_dict('records')
    except pd.errors.EmptyDataError:
        # If file is empty or only has headers
        return []

def add_entry(entry_type, amount, category, description, entry_date=None):
    """Add a new entry to the CSV file"""
    ensure_data_file()
    
    try:
        df = pd.read_csv(CSV_FILE)
        next_id = 1 if df.empty else df['id'].max() + 1
    except pd.errors.EmptyDataError:
        # If file is empty or only has headers
        next_id = 1
        df = pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'description'])
    
    # Use provided date or current date
    date_to_use = entry_date if entry_date else datetime.now().strftime('%Y-%m-%d')
    
    # Create new entry
    new_entry = {
        'id': next_id,
        'date': date_to_use,
        'type': entry_type,
        'amount': float(amount),
        'category': category,
        'description': description
    }
    
    # Append to dataframe and save
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    
    return next_id

def delete_entry(entry_id):
    """Delete an entry from the CSV file"""
    ensure_data_file()
    
    try:
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            df = df[df['id'] != int(entry_id)]
            df.to_csv(CSV_FILE, index=False)
            return True
    except Exception as e:
        print(f"Error deleting entry: {e}")
    return False

@bp.route('/')
def index():
    try:
        entries = get_all_entries()
        
        # Calculate summary statistics
        income_total = sum(entry['amount'] for entry in entries if entry['type'] == 'income')
        outcome_total = sum(entry['amount'] for entry in entries if entry['type'] == 'outcome')
        balance = income_total - outcome_total
        
        # Group by month for monthly stats
        monthly_stats = []
        monthly_stats_chrono = []
        
        if entries:
            df = pd.DataFrame(entries)
            # Ensure date column is properly formatted as datetime
            try:
                df['date'] = pd.to_datetime(df['date'])
                df['month'] = df['date'].dt.strftime('%Y-%m')
                
                # Group by month and calculate stats
                monthly_data = {}
                for _, row in df.iterrows():
                    month_key = row['month']
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {'income': 0, 'outcome': 0}
                    
                    if row['type'] == 'income':
                        monthly_data[month_key]['income'] += row['amount']
                    elif row['type'] == 'outcome':
                        monthly_data[month_key]['outcome'] += row['amount']
                
                # Create stats objects for each month
                for month_key, data in monthly_data.items():
                    month_income = data['income']
                    month_outcome = data['outcome']
                    month_balance = month_income - month_outcome
                    
                    # Convert month to readable format
                    date_obj = datetime.strptime(month_key, '%Y-%m')
                    month_name = date_obj.strftime('%B %Y')
                    
                    # Create a stats object
                    stats_obj = {
                        'month': month_name,
                        'month_key': month_key,
                        'income': month_income,
                        'outcome': month_outcome,
                        'balance': month_balance
                    }
                    
                    monthly_stats.append(stats_obj)
                
                # Sort by most recent month first for display table
                monthly_stats = sorted(monthly_stats, 
                                      key=lambda x: x['month_key'], 
                                      reverse=True)
                
                # Create a chronological copy for the chart (oldest to newest)
                monthly_stats_chrono = sorted([stat.copy() for stat in monthly_stats],
                                            key=lambda x: x['month_key'], 
                                            reverse=False)
            except Exception as e:
                print(f"Error processing dates: {e}")
                traceback.print_exc()
        
        return render_template('costincome/index.html', 
                              entries=entries,
                              income_total=income_total,
                              outcome_total=outcome_total,
                              balance=balance,
                              monthly_stats=monthly_stats,
                              monthly_stats_chrono=monthly_stats_chrono)
    except Exception as e:
        flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'danger')
        traceback.print_exc()
        return render_template('costincome/index.html', 
                              entries=[],
                              income_total=0,
                              outcome_total=0,
                              balance=0,
                              monthly_stats=[])

@bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        entry_type = request.form.get('type')
        amount = request.form.get('amount')
        category = request.form.get('category')
        description = request.form.get('description', '')
        entry_date = request.form.get('entry_date')
        
        # Validate input
        if not entry_type or entry_type not in ['income', 'outcome']:
            flash('Ungültiger Eintrags-Typ', 'danger')
            return redirect(url_for('costincome.add'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except:
            flash('Betrag muss eine positive Zahl sein', 'danger')
            return redirect(url_for('costincome.add'))
            
        if not category:
            flash('Kategorie ist erforderlich', 'danger')
            return redirect(url_for('costincome.add'))
        
        if not entry_date:
            flash('Datum ist erforderlich', 'danger')
            return redirect(url_for('costincome.add'))
        
        try:
            # Validate the date format
            datetime.strptime(entry_date, '%Y-%m-%d')
        except ValueError:
            flash('Ungültiges Datumsformat', 'danger')
            return redirect(url_for('costincome.add'))
        
        # Add entry to CSV
        add_entry(entry_type, amount, category, description, entry_date)
        
        flash(f'{"Einnahme" if entry_type == "income" else "Ausgabe"} erfolgreich hinzugefügt', 'success')
        return redirect(url_for('costincome.index'))
    
    return render_template('costincome/add.html')

@bp.route('/delete/<int:entry_id>', methods=['POST'])
def delete(entry_id):
    if delete_entry(entry_id):
        flash('Eintrag erfolgreich gelöscht', 'success')
    else:
        flash('Fehler beim Löschen des Eintrags', 'danger')
    
    return redirect(url_for('costincome.index'))