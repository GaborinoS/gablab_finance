from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.modules.costincome import bp
from app import db
from app.models import CostIncomeEntry
from datetime import datetime
import traceback
import pandas as pd
import json

@bp.route('/')
@login_required
def index():
    try:
        # Get current user's entries from the database
        entries = CostIncomeEntry.query.filter_by(user_id=current_user.id).order_by(CostIncomeEntry.date.desc()).all()
        
        # Get current month and year
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Convert entries to dictionary format for template
        entries_list = [
            {
                'id': entry.id,
                'date': entry.date.strftime('%Y-%m-%d'),
                'type': entry.type,
                'amount': entry.amount,
                'category': entry.category,
                'description': entry.description,
                # Add month and year info for filtering
                'month': entry.date.month,
                'year': entry.date.year,
                'is_current_month': (entry.date.month == current_month and entry.date.year == current_year)
            } for entry in entries
        ]
        
        # Calculate summary statistics for all time
        income_total_all = sum(entry.amount for entry in entries if entry.type == 'income')
        outcome_total_all = sum(entry.amount for entry in entries if entry.type == 'outcome')
        balance_all = income_total_all - outcome_total_all
        
        # Calculate summary statistics for current month
        income_total_current = sum(entry.amount for entry in entries 
                           if entry.type == 'income' 
                           and entry.date.month == current_month 
                           and entry.date.year == current_year)
        outcome_total_current = sum(entry.amount for entry in entries 
                             if entry.type == 'outcome' 
                             and entry.date.month == current_month 
                             and entry.date.year == current_year)
        balance_current = income_total_current - outcome_total_current
        
        # Format current month name for display
        current_month_name = datetime.now().strftime('%B %Y')
        
        # Group by month for monthly stats
        monthly_stats = []
        monthly_stats_chrono = []
        
        if entries:
            # Convert to pandas DataFrame for easier manipulation
            df = pd.DataFrame(entries_list)
            
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
        
        # Group entries by category for visualization
        income_by_category = {}
        outcome_by_category = {}
        
        for entry in entries_list:
            if entry['type'] == 'income':
                if entry['category'] not in income_by_category:
                    income_by_category[entry['category']] = 0
                income_by_category[entry['category']] += entry['amount']
            else:  # outcome
                if entry['category'] not in outcome_by_category:
                    outcome_by_category[entry['category']] = 0
                outcome_by_category[entry['category']] += entry['amount']
        
        return render_template('costincome/index.html', 
                              entries=entries_list,
                              income_total=income_total_current,
                              outcome_total=outcome_total_current,
                              balance=balance_current,
                              income_total_all=income_total_all,
                              outcome_total_all=outcome_total_all,
                              balance_all=balance_all,
                              monthly_stats=monthly_stats,
                              monthly_stats_chrono=monthly_stats_chrono,
                              income_by_category=income_by_category,
                              outcome_by_category=outcome_by_category,
                              current_month_name=current_month_name)
    except Exception as e:
        flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'danger')
        traceback.print_exc()
        return render_template('costincome/index.html', 
                              entries=[],
                              income_total=0,
                              outcome_total=0,
                              balance=0,
                              income_total_all=0,
                              outcome_total_all=0,
                              balance_all=0,
                              monthly_stats=[],
                              current_month_name=datetime.now().strftime('%B %Y'))

@bp.route('/get_month_data/<month_key>', methods=['GET'])
@login_required
def get_month_data(month_key):
    try:
        # Get current user's entries from the database
        entries = CostIncomeEntry.query.filter_by(user_id=current_user.id).all()
        
        # Parse the month_key to get month and year
        date_obj = datetime.strptime(month_key, '%Y-%m')
        selected_month = date_obj.month
        selected_year = date_obj.year
        month_name = date_obj.strftime('%B %Y')
        
        # Convert entries to dictionary format
        entries_list = [
            {
                'id': entry.id,
                'date': entry.date.strftime('%Y-%m-%d'),
                'type': entry.type,
                'amount': float(entry.amount),  # Ensure amount is float for JSON serialization
                'category': entry.category,
                'description': entry.description or '',
                'month': entry.date.month,
                'year': entry.date.year,
                'is_selected_month': (entry.date.month == selected_month and entry.date.year == selected_year)
            } for entry in entries
        ]
        
        # Calculate summary statistics for the selected month
        income_total = sum(entry.amount for entry in entries 
                       if entry.type == 'income' 
                       and entry.date.month == selected_month 
                       and entry.date.year == selected_year)
        
        outcome_total = sum(entry.amount for entry in entries 
                        if entry.type == 'outcome' 
                        and entry.date.month == selected_month 
                        and entry.date.year == selected_year)
        
        balance = income_total - outcome_total
        
        # Group entries by category for the selected month only
        income_by_category = {}
        outcome_by_category = {}
        
        for entry in entries_list:
            if entry['month'] == selected_month and entry['year'] == selected_year:
                if entry['type'] == 'income':
                    if entry['category'] not in income_by_category:
                        income_by_category[entry['category']] = 0
                    income_by_category[entry['category']] += entry['amount']
                else:  # outcome
                    if entry['category'] not in outcome_by_category:
                        outcome_by_category[entry['category']] = 0
                    outcome_by_category[entry['category']] += entry['amount']
        
        # Prepare the response data
        response_data = {
            'success': True,
            'month_name': month_name,
            'income_total': round(income_total, 2),
            'outcome_total': round(outcome_total, 2),
            'balance': round(balance, 2),
            'income_by_category': {k: round(v, 2) for k, v in income_by_category.items()},
            'outcome_by_category': {k: round(v, 2) for k, v in outcome_by_category.items()},
            'entries': [entry for entry in entries_list if entry['month'] == selected_month and entry['year'] == selected_year]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/add', methods=['GET', 'POST'])
@login_required
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
            # Validate and convert the date format
            date_obj = datetime.strptime(entry_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Ungültiges Datumsformat', 'danger')
            return redirect(url_for('costincome.add'))
        
        # Create new entry in the database
        new_entry = CostIncomeEntry(
            user_id=current_user.id,
            date=date_obj,
            type=entry_type,
            amount=amount,
            category=category,
            description=description
        )
        
        db.session.add(new_entry)
        db.session.commit()
        
        flash(f'{"Einnahme" if entry_type == "income" else "Ausgabe"} erfolgreich hinzugefügt', 'success')
        return redirect(url_for('costincome.index'))
    
    return render_template('costincome/add.html')

@bp.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit(entry_id):
    # Get the entry from the database
    entry = CostIncomeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        entry_type = request.form.get('type')
        amount = request.form.get('amount')
        category = request.form.get('category')
        description = request.form.get('description', '')
        entry_date = request.form.get('entry_date')
        
        # Validate input
        if not entry_type or entry_type not in ['income', 'outcome']:
            flash('Ungültiger Eintrags-Typ', 'danger')
            return redirect(url_for('costincome.edit', entry_id=entry_id))
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except:
            flash('Betrag muss eine positive Zahl sein', 'danger')
            return redirect(url_for('costincome.edit', entry_id=entry_id))
            
        if not category:
            flash('Kategorie ist erforderlich', 'danger')
            return redirect(url_for('costincome.edit', entry_id=entry_id))
        
        if not entry_date:
            flash('Datum ist erforderlich', 'danger')
            return redirect(url_for('costincome.edit', entry_id=entry_id))
        
        try:
            # Validate and convert the date format
            date_obj = datetime.strptime(entry_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Ungültiges Datumsformat', 'danger')
            return redirect(url_for('costincome.edit', entry_id=entry_id))
        
        # Update the entry
        entry.type = entry_type
        entry.amount = amount
        entry.category = category
        entry.description = description
        entry.date = date_obj
        
        db.session.commit()
        
        flash(f'Eintrag erfolgreich aktualisiert', 'success')
        return redirect(url_for('costincome.index'))
    
    # For GET request, render the edit form with the current entry data
    return render_template('costincome/edit.html', entry=entry)

@bp.route('/get_entry/<int:entry_id>', methods=['GET'])
@login_required
def get_entry(entry_id):
    try:
        # Get the entry from the database
        entry = CostIncomeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
        
        # Convert entry to dictionary
        entry_data = {
            'id': entry.id,
            'date': entry.date.strftime('%Y-%m-%d'),
            'type': entry.type,
            'amount': float(entry.amount),
            'category': entry.category,
            'description': entry.description or ''
        }
        
        return jsonify({'success': True, 'entry': entry_data})
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/update_entry/<int:entry_id>', methods=['POST'])
@login_required
def update_entry(entry_id):
    try:
        # Get the entry from the database
        entry = CostIncomeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
        
        # Get the data from the request
        data = request.json
        
        # Validate input
        if not data.get('type') or data.get('type') not in ['income', 'outcome']:
            return jsonify({'success': False, 'error': 'Ungültiger Eintrags-Typ'})
        
        try:
            amount = float(data.get('amount', 0))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except:
            return jsonify({'success': False, 'error': 'Betrag muss eine positive Zahl sein'})
            
        if not data.get('category'):
            return jsonify({'success': False, 'error': 'Kategorie ist erforderlich'})
        
        if not data.get('date'):
            return jsonify({'success': False, 'error': 'Datum ist erforderlich'})
        
        try:
            # Validate and convert the date format
            date_obj = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Ungültiges Datumsformat'})
        
        # Update the entry
        entry.type = data.get('type')
        entry.amount = amount
        entry.category = data.get('category')
        entry.description = data.get('description', '')
        entry.date = date_obj
        
        db.session.commit()
        
        # Get month key for the updated entry
        month_key = entry.date.strftime('%Y-%m')
        
        return jsonify({
            'success': True,
            'message': 'Eintrag erfolgreich aktualisiert',
            'month_key': month_key
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete(entry_id):
    entry = CostIncomeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(entry)
    db.session.commit()
    
    flash('Eintrag erfolgreich gelöscht', 'success')
    return redirect(url_for('costincome.index'))