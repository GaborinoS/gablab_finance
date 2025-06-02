from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.modules.portfolio import bp
from app import db
from app.models import PortfolioData
import json
import yfinance as yf
from datetime import datetime, timedelta
import os
import time
import random

# Create a simple local file-based cache system
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cached_data(ticker):
    """Get cached data for a ticker if it exists and is fresh"""
    cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('/', '_').replace(':', '_')}.json")
    
    if not os.path.exists(cache_file):
        return None
        
    # Check if data is stale (older than 6 hours)
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    time_diff = datetime.now() - file_time
    if time_diff > timedelta(hours=6):
        return None
        
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading cache file for {ticker}: {e}")
        return None

def update_cache(ticker, data):
    """Update the cache for a ticker"""
    cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('/', '_').replace(':', '_')}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing cache file for {ticker}: {e}")

def is_cache_fresh(ticker):
    """Check if the cache for a ticker is fresh (updated within the last 6 hours)"""
    cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('/', '_').replace(':', '_')}.json")
    
    if not os.path.exists(cache_file):
        return False
        
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    time_diff = datetime.now() - file_time
    return time_diff <= timedelta(hours=6)

def fetch_price_safely(ticker_symbol):
    """Fetch price data with cache and rate limit protection"""
    # Check cache first
    cached_data = get_cached_data(ticker_symbol)
    if cached_data:
        print(f"Using cached data for {ticker_symbol}")
        return cached_data.get('last_close', 0), cached_data
        
    # If we have to fetch, introduce a random delay to avoid rate limiting
    delay = 0.1
    time.sleep(delay)
    
    try:
        print(f"Fetching fresh data for {ticker_symbol}")
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch complete historical data instead of just 1 day
        history = ticker.history(period="max")
        
        if not history.empty:
            current_price = float(history['Close'].iloc[-1])
            
            # Convert dates to string format for JSON serialization
            history.reset_index(inplace=True)
            dates = history["Date"].dt.strftime('%Y-%m-%d').tolist()
            close_values = history["Close"].tolist()
            
            # Create cache data with full timeseries
            cache_data = {
                'ticker': ticker_symbol,
                'last_close': current_price,
                'last_date': history["Date"].iloc[-1].strftime('%Y-%m-%d'),
                'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'dates': dates,
                'values': [float(val) for val in close_values],
                'full_history': True,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Update cache
            update_cache(ticker_symbol, cache_data)
            
            return current_price, cache_data
        else:
            print(f"No data found for {ticker_symbol}")
            
            # Create fallback cache data with dummy values
            fallback_data = {
                'ticker': ticker_symbol,
                'last_close': 100.0,  # Dummy value
                'last_date': datetime.now().strftime('%Y-%m-%d'),
                'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'dates': [datetime.now().strftime('%Y-%m-%d')],
                'values': [100.0],
                'full_history': False,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'No data found'
            }
            
            # Update cache with fallback data
            update_cache(ticker_symbol, fallback_data)
            
            return 0, fallback_data
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        
        # Create fallback cache data with dummy values
        fallback_data = {
            'ticker': ticker_symbol,
            'last_close': 100.0,  # Dummy value
            'last_date': datetime.now().strftime('%Y-%m-%d'),
            'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dates': [datetime.now().strftime('%Y-%m-%d')],
            'values': [100.0],
            'full_history': False,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e)
        }
        
        # Update cache with fallback data
        update_cache(ticker_symbol, fallback_data)
        
        return 0, fallback_data

@bp.route('/')
@login_required
def index():
    """Display portfolio overview page"""
    # Get current user's portfolio
    portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
    
    # If no portfolio found, create an empty one
    if portfolio is None:
        default_portfolio = {
            "etf": [],
            "stocks": [],
            "bonds": [],
            "commodities": [],
            "realEstate": [],
            "savings": []
        }
        portfolio = PortfolioData(user_id=current_user.id)
        portfolio.set_data(default_portfolio)
        db.session.add(portfolio)
        db.session.commit()
        
    # Get the portfolio data
    portfolio_data = portfolio.get_data()
    
    # Calculate totals and asset allocation
    total_value = 0
    total_acquisition_cost = 0
    asset_allocation = {}
    
    # Data for earnings chart
    performance_data = {
        'labels': [],
        'acquisition_costs': [],
        'current_values': [],
        'gains_losses': []
    }
    
    # Process ETFs
    etf_total = 0
    etf_current_value = 0
    try:
        # Get current market values for ETFs
        for i, etf in enumerate(portfolio_data.get('etf', [])):
            ticker_symbol = etf.get('ticker')
            amount = etf.get('amount', 0)
            acquisition_cost = etf.get('acquisition_cost', 0)
            
            if ticker_symbol and amount > 0:
                try:
                    # Get data with cache and rate limit protection
                    current_price, _ = fetch_price_safely(ticker_symbol)
                    
                    current_value = current_price * amount
                    
                    # Calculate gain/loss
                    gain_loss = current_value - acquisition_cost
                    gain_loss_percent = (gain_loss / acquisition_cost * 100) if acquisition_cost > 0 else 0
                    
                    # Update ETF with current data
                    portfolio_data['etf'][i]['current_price'] = round(current_price, 2)
                    portfolio_data['etf'][i]['current_value'] = round(current_value, 2)
                    portfolio_data['etf'][i]['gain_loss'] = round(gain_loss, 2)
                    portfolio_data['etf'][i]['gain_loss_percent'] = round(gain_loss_percent, 2)
                    
                    etf_current_value += current_value
                    
                    # Add data for performance chart
                    if acquisition_cost > 0:
                        performance_data['labels'].append(etf.get('name', ticker_symbol))
                        performance_data['acquisition_costs'].append(round(acquisition_cost, 2))
                        performance_data['current_values'].append(round(current_value, 2))
                        performance_data['gains_losses'].append(round(gain_loss, 2))
                    
                except Exception as e:
                    print(f"Error processing {ticker_symbol}: {e}")
                    # Use acquisition cost as fallback
                    portfolio_data['etf'][i]['current_price'] = 0
                    portfolio_data['etf'][i]['current_value'] = acquisition_cost
                    portfolio_data['etf'][i]['gain_loss'] = 0
                    portfolio_data['etf'][i]['gain_loss_percent'] = 0
                    
                    etf_current_value += acquisition_cost
            
            etf_total += acquisition_cost
    except Exception as e:
        print(f"Error processing ETFs: {e}")
    
    if etf_total > 0:
        asset_allocation['ETF'] = etf_current_value
        total_value += etf_current_value
        total_acquisition_cost += etf_total
    
    # Process stocks
    stocks_total = 0
    stocks_current_value = 0
    try:
        # Get current market values for stocks
        for i, stock in enumerate(portfolio_data.get('stocks', [])):
            ticker_symbol = stock.get('ticker')
            amount = stock.get('amount', 0)
            acquisition_cost = stock.get('acquisition_cost', 0)
            
            if ticker_symbol and amount > 0:
                try:
                    # Get data with cache and rate limit protection
                    current_price, _ = fetch_price_safely(ticker_symbol)
                    
                    current_value = current_price * amount
                    
                    # Calculate gain/loss
                    gain_loss = current_value - acquisition_cost
                    gain_loss_percent = (gain_loss / acquisition_cost * 100) if acquisition_cost > 0 else 0
                    
                    # Update stock with current data
                    portfolio_data['stocks'][i]['current_price'] = round(current_price, 2)
                    portfolio_data['stocks'][i]['current_value'] = round(current_value, 2)
                    portfolio_data['stocks'][i]['gain_loss'] = round(gain_loss, 2)
                    portfolio_data['stocks'][i]['gain_loss_percent'] = round(gain_loss_percent, 2)
                    
                    stocks_current_value += current_value
                    
                    # Add data for performance chart
                    if acquisition_cost > 0:
                        performance_data['labels'].append(stock.get('name', ticker_symbol))
                        performance_data['acquisition_costs'].append(round(acquisition_cost, 2))
                        performance_data['current_values'].append(round(current_value, 2))
                        performance_data['gains_losses'].append(round(gain_loss, 2))
                    
                except Exception as e:
                    print(f"Error processing {ticker_symbol}: {e}")
                    # Use acquisition cost as fallback
                    portfolio_data['stocks'][i]['current_price'] = 0
                    portfolio_data['stocks'][i]['current_value'] = acquisition_cost
                    portfolio_data['stocks'][i]['gain_loss'] = 0
                    portfolio_data['stocks'][i]['gain_loss_percent'] = 0
                    
                    stocks_current_value += acquisition_cost
            
            stocks_total += acquisition_cost
    except Exception as e:
        print(f"Error processing stocks: {e}")
    
    if stocks_total > 0:
        asset_allocation['Aktien'] = stocks_current_value
        total_value += stocks_current_value
        total_acquisition_cost += stocks_total
    
    # Process bonds
    bonds_total = 0
    for bond in portfolio_data.get('bonds', []):
        if 'amount' in bond and 'acquisition_cost' in bond:
            bonds_total += bond['acquisition_cost']
    
    if bonds_total > 0:
        asset_allocation['Anleihen'] = bonds_total
        total_value += bonds_total
        total_acquisition_cost += bonds_total
    
    # Process commodities
    commodities_total = 0
    for commodity in portfolio_data.get('commodities', []):
        if 'amount' in commodity and 'acquisition_cost' in commodity:
            commodities_total += commodity['acquisition_cost']
    
    if commodities_total > 0:
        asset_allocation['Rohstoffe'] = commodities_total
        total_value += commodities_total
        total_acquisition_cost += commodities_total
    
    # Process real estate
    realestate_total = 0
    for realestate in portfolio_data.get('realEstate', []):
        if 'amount' in realestate and 'acquisition_cost' in realestate:
            realestate_total += realestate['acquisition_cost']
    
    if realestate_total > 0:
        asset_allocation['Immobilien'] = realestate_total
        total_value += realestate_total
        total_acquisition_cost += realestate_total
    
    # Process savings
    savings_total = 0
    try:
        # Update savings with interest rates and current values
        for i, savings in enumerate(portfolio_data.get('savings', [])):
            amount = savings.get('amount', 0)
            
            # Make sure interest_rate is properly set
            if 'interest_rate' not in savings or savings['interest_rate'] is None:
                portfolio_data['savings'][i]['interest_rate'] = 0
                
            interest_rate = portfolio_data['savings'][i]['interest_rate']
            
            # Make sure acquisition_cost is set
            if 'acquisition_cost' not in savings or savings['acquisition_cost'] is None:
                portfolio_data['savings'][i]['acquisition_cost'] = amount
                
            acquisition_cost = portfolio_data['savings'][i]['acquisition_cost']
            
            # Set current value to be the same as amount for savings
            portfolio_data['savings'][i]['current_value'] = amount
            portfolio_data['savings'][i]['gain_loss'] = amount - acquisition_cost
            
            if acquisition_cost > 0:
                gain_loss_percent = (amount - acquisition_cost) / acquisition_cost * 100
                portfolio_data['savings'][i]['gain_loss_percent'] = round(gain_loss_percent, 2)
                
                # Add data for performance chart
                performance_data['labels'].append(savings.get('name', "Savings"))
                performance_data['acquisition_costs'].append(round(acquisition_cost, 2))
                performance_data['current_values'].append(round(amount, 2))
                performance_data['gains_losses'].append(round(amount - acquisition_cost, 2))
            else:
                portfolio_data['savings'][i]['gain_loss_percent'] = 0
                
            savings_total += amount
    except Exception as e:
        print(f"Error processing savings: {e}")
        
    if savings_total > 0:
        asset_allocation['Sparguthaben'] = savings_total
        total_value += savings_total
        total_acquisition_cost += savings_total
    
    # Convert asset allocation to percentages
    allocation_percentages = {}
    if total_value > 0:
        for asset_class, value in asset_allocation.items():
            allocation_percentages[asset_class] = (value / total_value) * 100
    
    # Calculate total gain/loss
    total_gain_loss = total_value - total_acquisition_cost
    total_gain_loss_percent = (total_gain_loss / total_acquisition_cost * 100) if total_acquisition_cost > 0 else 0
    
    # Save updated portfolio data
    portfolio.set_data(portfolio_data)
    db.session.commit()
    
    return render_template('portfolio/index.html', 
                          portfolio=portfolio_data,
                          total_value=total_value,
                          total_acquisition_cost=total_acquisition_cost,
                          total_gain_loss=total_gain_loss,
                          total_gain_loss_percent=total_gain_loss_percent,
                          asset_allocation=allocation_percentages,
                          performance_data=performance_data,
                          last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@bp.route('/add_asset', methods=['GET', 'POST'])
@login_required
def add_asset():
    """Handle adding a new asset to the portfolio"""
    if request.method == 'POST':
        # Get form data
        asset_class = request.form.get('asset_class')
        ticker = request.form.get('ticker', '')
        name = request.form.get('name')
        currency = request.form.get('currency', 'EUR')
        isin = request.form.get('isin', '')
        amount = float(request.form.get('amount', 0))
        acquisition_cost = float(request.form.get('acquisition_cost', 0))
        
        # Validate input
        if not asset_class or asset_class not in ['etf', 'stocks', 'bonds', 'commodities', 'realEstate', 'savings']:
            flash('Ungültige Anlageklasse', 'danger')
            return redirect(url_for('portfolio.add_asset'))
            
        if not name:
            flash('Name ist erforderlich', 'danger')
            return redirect(url_for('portfolio.add_asset'))
            
        if asset_class != 'savings' and not ticker:
            flash('Ticker ist erforderlich für diese Anlageklasse', 'danger')
            return redirect(url_for('portfolio.add_asset'))
        
        # Get current user's portfolio
        portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
        
        if portfolio is None:
            # Create a new portfolio if none exists
            default_portfolio = {
                "etf": [],
                "stocks": [],
                "bonds": [],
                "commodities": [],
                "realEstate": [],
                "savings": []
            }
            portfolio = PortfolioData(user_id=current_user.id)
            portfolio.set_data(default_portfolio)
            db.session.add(portfolio)
            db.session.commit()
        
        # Get the portfolio data
        portfolio_data = portfolio.get_data()
        
        # Create the new asset
        new_asset = {
            "name": name,
            "currency": currency,
            "amount": amount,
            "acquisition_cost": acquisition_cost
        }
        
        if asset_class != 'savings':
            new_asset["ticker"] = ticker
            new_asset["isin"] = isin
            
            # Pre-fetch and cache the ticker data if needed
            if ticker and not is_cache_fresh(ticker):
                try:
                    # Introduce a random delay to avoid rate limiting
                    time.sleep(0.2)
                    
                    ticker_obj = yf.Ticker(ticker)
                    # Fetch complete historical data instead of just 1 day
                    history = ticker_obj.history(period="max")
                    
                    if not history.empty:
                        current_price = float(history['Close'].iloc[-1])
                        
                        # Convert dates to string format for JSON serialization
                        history.reset_index(inplace=True)
                        dates = history["Date"].dt.strftime('%Y-%m-%d').tolist()
                        close_values = history["Close"].tolist()
                        
                        # Create cache data with full timeseries
                        cache_data = {
                            'ticker': ticker,
                            'last_close': current_price,
                            'last_date': history["Date"].iloc[-1].strftime('%Y-%m-%d'),
                            'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'dates': dates,
                            'values': [float(val) for val in close_values],
                            'full_history': True,
                            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        update_cache(ticker, cache_data)
                except Exception as e:
                    print(f"Failed to pre-fetch ticker data for {ticker}: {e}")
        else:
            # Handle interest rate for savings
            interest_rate = float(request.form.get('interest_rate', 0)) / 100.0  # Convert from percentage to decimal
            new_asset["interest_rate"] = interest_rate
        
        # Add to appropriate asset class
        if asset_class not in portfolio_data:
            portfolio_data[asset_class] = []
            
        portfolio_data[asset_class].append(new_asset)
        
        # Update the portfolio
        portfolio.set_data(portfolio_data)
        db.session.commit()
        
        flash(f'Asset wurde erfolgreich hinzugefügt', 'success')
        return redirect(url_for('portfolio.index'))
    
    return render_template('portfolio/add_asset.html')

@bp.route('/refresh')
@login_required
def refresh():
    """Refresh market data for all assets"""
    # Get current user's portfolio
    portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
    
    if portfolio is None:
        flash('Portfolio nicht gefunden', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Get portfolio data
    portfolio_data = portfolio.get_data()
    
    # Collect all tickers to refresh
    tickers = []
    for asset_class in ['etf', 'stocks', 'bonds', 'commodities', 'realEstate']:
        for asset in portfolio_data.get(asset_class, []):
            ticker = asset.get('ticker')
            if ticker:
                tickers.append(ticker)
    
    # Force refresh tickers with a delay to avoid rate limiting
    refresh_count = 0
    for ticker in tickers:
        try:
            # Clear existing cache
            cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('/', '_').replace(':', '_')}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                
            # Add a delay to avoid rate limiting
            time.sleep(0.3)
                
            # Fetch fresh data
            current_price, _ = fetch_price_safely(ticker)
            if current_price > 0:
                refresh_count += 1
        except Exception as e:
            print(f"Error refreshing data for {ticker}: {e}")
    
    flash(f'Marktdaten für {refresh_count} Assets wurden aktualisiert', 'success')
    return redirect(url_for('portfolio.index'))

@bp.route('/delete_asset/<asset_class>/<int:index>', methods=['POST'])
@login_required
def delete_asset(asset_class, index):
    """Delete an asset from the portfolio"""
    # Get current user's portfolio
    portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
    
    if portfolio is None:
        flash('Portfolio nicht gefunden', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Get the portfolio data
    portfolio_data = portfolio.get_data()
    
    # Check if asset class exists
    if asset_class not in portfolio_data:
        flash('Ungültige Anlageklasse', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Check if index is valid
    if index < 0 or index >= len(portfolio_data[asset_class]):
        flash('Ungültiger Asset-Index', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Remove the asset
    removed_asset = portfolio_data[asset_class].pop(index)
    
    # Update the portfolio
    portfolio.set_data(portfolio_data)
    db.session.commit()
    
    flash(f'Asset {removed_asset.get("name", "")} wurde gelöscht', 'success')
    return redirect(url_for('portfolio.index'))

@bp.route('/edit_asset/<asset_class>/<int:index>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_class, index):
    """Edit an asset in the portfolio"""
    # Get current user's portfolio
    portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
    
    if portfolio is None:
        flash('Portfolio nicht gefunden', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Get the portfolio data
    portfolio_data = portfolio.get_data()
    
    # Check if asset class exists
    if asset_class not in portfolio_data:
        flash('Ungültige Anlageklasse', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Check if index is valid
    if index < 0 or index >= len(portfolio_data[asset_class]):
        flash('Ungültiger Asset-Index', 'danger')
        return redirect(url_for('portfolio.index'))
    
    # Get the asset to edit
    asset = portfolio_data[asset_class][index]
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        amount = request.form.get('amount')
        acquisition_cost = request.form.get('acquisition_cost')
        
        # Additional fields based on asset class
        if asset_class != 'savings':
            ticker = request.form.get('ticker')
            isin = request.form.get('isin')
        else:
            interest_rate = request.form.get('interest_rate')
        
        # Validate input
        try:
            amount = float(amount)
            if amount < 0:
                raise ValueError("Amount must be non-negative")
                
            acquisition_cost = float(acquisition_cost)
            if acquisition_cost < 0:
                raise ValueError("Acquisition cost must be non-negative")
                
            if asset_class == 'savings' and interest_rate:
                interest_rate = float(interest_rate) / 100.0  # Convert from percentage to decimal
        except ValueError as e:
            flash(f'Ungültiger Wert: {str(e)}', 'danger')
            return redirect(url_for('portfolio.edit_asset', asset_class=asset_class, index=index))
        
        # Update asset data
        if name:
            asset['name'] = name
        asset['amount'] = amount
        asset['acquisition_cost'] = acquisition_cost
        
        if asset_class != 'savings':
            if ticker:
                old_ticker = asset.get('ticker', '')
                # Only update cache if ticker has changed
                if ticker != old_ticker:
                    # Pre-fetch and cache if needed
                    if not is_cache_fresh(ticker):
                        try:
                            # Introduce a random delay to avoid rate limiting
                            time.sleep(0.3)
                            
                            ticker_obj = yf.Ticker(ticker)
                            # Fetch complete historical data instead of just 1 day
                            history = ticker_obj.history(period="max")
                            
                            if not history.empty:
                                current_price = float(history['Close'].iloc[-1])
                                
                                # Convert dates to string format for JSON serialization
                                history.reset_index(inplace=True)
                                dates = history["Date"].dt.strftime('%Y-%m-%d').tolist()
                                close_values = history["Close"].tolist()
                                
                                # Create cache data with full timeseries
                                cache_data = {
                                    'ticker': ticker,
                                    'last_close': current_price,
                                    'last_date': history["Date"].iloc[-1].strftime('%Y-%m-%d'),
                                    'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'dates': dates,
                                    'values': [float(val) for val in close_values],
                                    'full_history': True,
                                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                update_cache(ticker, cache_data)
                        except Exception as e:
                            print(f"Failed to pre-fetch ticker data for {ticker}: {e}")
                
                asset['ticker'] = ticker
            if isin:
                asset['isin'] = isin
        else:
            asset['interest_rate'] = interest_rate
        
        # Update portfolio data
        portfolio_data[asset_class][index] = asset
        portfolio.set_data(portfolio_data)
        db.session.commit()
        
        flash(f'Asset {asset["name"]} wurde aktualisiert', 'success')
        return redirect(url_for('portfolio.index'))
    
    # Add asset class to the context for the template
    asset['asset_class'] = asset_class
    asset['index'] = index
    
    # For savings, convert interest rate from decimal to percentage for display
    if asset_class == 'savings' and 'interest_rate' in asset:
        asset['interest_rate_percent'] = asset['interest_rate'] * 100
    
    return render_template('portfolio/edit_asset.html', asset=asset)