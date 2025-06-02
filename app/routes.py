from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

@main.route('/')
def home():
    if not current_user.is_authenticated:
        modules = [
            {
                'name': 'Login',
                'description': 'Melden Sie sich an, um Ihre Finanzdaten zu verwalten',
                'url': '/auth/login',
                'icon': 'sign-in-alt'
            },
            {
                'name': 'Registrieren',
                'description': 'Erstellen Sie ein neues Konto',
                'url': '/auth/register',
                'icon': 'user-plus'
            }
            
        ]
    else:
        modules = [
            {
                'name': 'Zeitreihen',
                'description': 'Analysieren Sie Finanzdaten im Zeitverlauf',
                'url': '/timeseries',
                'icon': 'chart-line'
            },
            {
                'name': 'Kosten/Einkommen Visu',
                'description': 'Visualisieren Sie Ihre Einnahmen und Ausgaben',
                'url': '/costincome',
                'icon': 'chart-pie'
            },
            {
                'name': 'Portfolio',
                'description': 'Verwalten Sie Ihr Investment-Portfolio',
                'url': '/portfolio',
                'icon': 'briefcase'
            },
                       {
                'name': 'Odoo Integration',
                'description': 'Verbindung mit Ihrem Odoo-ERP-System',
                'url': '/odoo',
                'icon': 'plug'
            }
            ,{
                'name': 'WL Ticker',
                'description': 'Live Abfahrtszeiten der Wiener Linien',
                'icon': 'subway',
                'url': url_for('wl_ticker.index')
            }
        ]
    return render_template('home.html', modules=modules)

@main.route('/migrate_data')
@login_required
def migrate_data():
    """Admin route to migrate data from files to database - only for initial setup"""
    # Import utility functions
    from app.utils.portfolio_utils import migrate_existing_portfolio_data, create_default_portfolio
    from app.utils.costincome_utils import migrate_existing_costincome_data
    
    # Migrate existing portfolio data for logged-in user
    portfolio_migrated = False
    portfolio_created = False
    costincome_migrated = False
    
    # Try to migrate the existing portfolio, if not possible, create a default one
    portfolio_migrated = migrate_existing_portfolio_data()
    if not portfolio_migrated:
        portfolio_created = create_default_portfolio(current_user.id)
        
    # Migrate cost/income data
    costincome_migrated = migrate_existing_costincome_data()
    
    # Flash a message indicating the result
    if portfolio_migrated or portfolio_created:
        flash('Portfolio-Daten wurden erfolgreich migriert oder erstellt.', 'success')
    else:
        flash('Fehler bei der Migration der Portfolio-Daten.', 'danger')
        
    if costincome_migrated:
        flash('Kosten/Einkommen-Daten wurden erfolgreich migriert.', 'success')
    else:
        flash('Fehler bei der Migration der Kosten/Einkommen-Daten.', 'danger')
        
    return redirect(url_for('main.home'))