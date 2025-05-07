import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
import time
import random
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user
from app.models import PortfolioData

# Create a simple file-based cache system
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

def get_available_securities():
    """Retrieves the portfolio data for the current user"""
    try:
        # Check if the current user has portfolio data
        if not current_user.is_authenticated:
            # If not authenticated, return demo data
            return get_demo_securities()
            
        portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
        
        if portfolio is None:
            # If user has no portfolio data yet, return demo data
            return get_demo_securities()
            
        # Convert stored JSON to Python dict
        portfolio_data = portfolio.get_data()
        
        securities = []
        
        # ETFs hinzufügen
        for etf in portfolio_data.get('etf', []):
            securities.append({
                'ticker': etf['ticker'],
                'name': etf['name'],
                'category': 'ETF',
                'currency': etf.get('currency', 'EUR'),
                'amount': etf.get('amount', 0),
            })
        
        # Aktien hinzufügen
        for stock in portfolio_data.get('stocks', []):
            securities.append({
                'ticker': stock['ticker'],
                'name': stock['name'],
                'category': 'Aktie',
                'currency': stock.get('currency', 'USD'),
                'amount': stock.get('amount', 0),
            })
        
        # Anleihen hinzufügen
        for bond in portfolio_data.get('bonds', []):
            securities.append({
                'ticker': bond['ticker'],
                'name': bond['name'],
                'category': 'Anleihe',
                'currency': bond.get('currency', 'USD'),
                'amount': bond.get('amount', 0),
            })
        
        # Rohstoffe hinzufügen
        for commodity in portfolio_data.get('commodities', []):
            securities.append({
                'ticker': commodity['ticker'],
                'name': commodity['name'],
                'category': 'Rohstoff',
                'currency': commodity.get('currency', 'USD'),
                'amount': commodity.get('amount', 0),
            })
        
        # Immobilien hinzufügen
        for realestate in portfolio_data.get('realEstate', []):
            securities.append({
                'ticker': realestate['ticker'],
                'name': realestate['name'],
                'category': 'Immobilien',
                'currency': realestate.get('currency', 'USD'),
                'amount': realestate.get('amount', 0),
            })
        
        return securities
    
    except Exception as e:
        print(f"Fehler beim Lesen der Portfolio-Daten: {e}")
        # Fallback: Standardwerte zurückgeben, wenn die Datei nicht gelesen werden kann
        return get_demo_securities()

def get_demo_securities():
    """Returns demo securities data for new users or non-authenticated users"""
    return [
        {
            'ticker': 'EUNL.DE',
            'name': 'iShares Core MSCI World UCITS ETF',
            'category': 'ETF',
            'currency': 'EUR',
            'amount': 14,
        },
        {
            'ticker': 'LIRU.DE',
            'name': 'Amundi STOXX Europe 600 Insurance UCITS ETF Acc',
            'category': 'ETF',
            'currency': 'EUR',
            'amount': 4,
        },
        {
            'ticker': 'SXR8.DE',
            'name': 'iShares Core S&P 500 UCITS ETF USD (Acc)',
            'category': 'ETF',
            'currency': 'USD',
            'amount': 1,
        }
    ]

def get_portfolio_data():
    """Retrieves the full portfolio data for the current user"""
    try:
        if not current_user.is_authenticated:
            # If not authenticated, return demo data
            return get_demo_portfolio_data()
            
        portfolio = PortfolioData.query.filter_by(user_id=current_user.id).first()
        
        if portfolio is None:
            # If user has no portfolio data yet, return demo data
            return get_demo_portfolio_data()
            
        # Return the stored data
        return portfolio.get_data()
    
    except Exception as e:
        print(f"Fehler beim Lesen der Portfolio-Daten: {e}")
        return get_demo_portfolio_data()

def get_demo_portfolio_data():
    """Returns demo portfolio data structure"""
    return {
        "etf": [
            {
                "ticker": "EUNL.DE",
                "name": "iShares Core MSCI World UCITS ETF",
                "currency": "EUR",
                "isin": "IE00B4L5Y983",
                "amount": 14,
                "acquisition_cost": 1258.73
            },
            {
                "ticker": "LIRU.DE",
                "name": "Amundi STOXX Europe 600 Insurance UCITS ETF Acc",
                "currency": "EUR",
                "isin": "IE00B6R52259",
                "amount": 4,
                "acquisition_cost": 315.92
            },
            {
                "ticker": "SXR8.DE",
                "name": "iShares Core S&P 500 UCITS ETF USD (Acc)",
                "currency": "USD",
                "isin": "IE00B5BMR087",
                "amount": 1,
                "acquisition_cost": 509.22
            }
        ],
        "stocks": [],
        "bonds": [],
        "commodities": [],
        "realEstate": [],
        "savings": [
            {
                "name": "Sparbuch",
                "amount": 1000,
                "interest_rate": 0.02,
                "currency": "EUR",
                "acquisition_cost": 1000
            }
        ]
    }

def fetch_ticker_data_safely(ticker_symbol):
    """Fetch ticker data with cache and rate limit protection"""
    # Try to get data from cache first
    cached_data = get_cached_data(ticker_symbol)
    if cached_data:
        print(f"Using cached data for {ticker_symbol}")
        return cached_data
    
    # If data not in cache, need to fetch from API
    print(f"Fetching fresh data for {ticker_symbol}")
    
    # Add random delay to avoid rate limiting
    time.sleep(random.uniform(1.0, 3.0))
    
    try:
        # Create Ticker object and fetch history
        ticker = yf.Ticker(ticker_symbol)
        historical_data = ticker.history(period="max")
        
        if historical_data.empty:
            raise ValueError(f"Keine Daten für Ticker {ticker_symbol} gefunden")
            
        # Process the data for storage/return
        historical_data.reset_index(inplace=True)
        
        # Convert to digestible format
        result = {
            'ticker': ticker_symbol,
            'dates': historical_data["Date"].dt.strftime('%Y-%m-%d').tolist(),
            'values': [float(val) for val in historical_data["Close"].tolist()],
            'last_close': float(historical_data["Close"].iloc[-1]) if not historical_data.empty else 0,
            'last_date': historical_data["Date"].iloc[-1].strftime('%Y-%m-%d') if not historical_data.empty else "Unknown",
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'full_history': True
        }
        
        # Save additional data if available
        if not historical_data.empty:
            if 'Open' in historical_data.columns:
                result['open_values'] = [float(val) for val in historical_data["Open"].tolist()]
            if 'High' in historical_data.columns:
                result['high_values'] = [float(val) for val in historical_data["High"].tolist()]
            if 'Low' in historical_data.columns:
                result['low_values'] = [float(val) for val in historical_data["Low"].tolist()]
            if 'Volume' in historical_data.columns:
                result['volume_values'] = [float(val) if not pd.isna(val) else 0 for val in historical_data["Volume"].tolist()]
        
        # Add full datetime if available
        if 'Datetime' in historical_data.columns and not historical_data.empty:
            result['last_datetime'] = historical_data["Datetime"].iloc[-1].strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Default to date with standard closing time
            result['last_datetime'] = f"{result['last_date']} 17:30:00"
        
        # Cache the data for future use
        update_cache(ticker_symbol, result)
        
        return result
    
    except Exception as e:
        print(f"Error fetching data from API for {ticker_symbol}: {e}")
        
        # Create fallback data with dummy values
        current_datetime = datetime.now()
        dates = [(current_datetime - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(365, 0, -1)]
        close_values = [100 + (i % 20) + (i // 20) for i in range(365)]  # Generate some pattern
        
        fallback_data = {
            'ticker': ticker_symbol,
            'dates': dates,
            'values': close_values,
            'last_close': close_values[-1],
            'last_date': dates[-1],
            'last_datetime': f"{dates[-1]} 17:30:00",
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'full_history': True,
            'error': str(e),
            'is_fallback': True
        }
        
        # Add more realistic OHLC data
        open_values = [val * (1 - random.uniform(-0.01, 0.01)) for val in close_values]
        high_values = [max(o, c) * (1 + random.uniform(0, 0.02)) for o, c in zip(open_values, close_values)]
        low_values = [min(o, c) * (1 - random.uniform(0, 0.02)) for o, c in zip(open_values, close_values)]
        volume_values = [random.randint(10000, 1000000) for _ in range(365)]
        
        fallback_data['open_values'] = open_values
        fallback_data['high_values'] = high_values
        fallback_data['low_values'] = low_values
        fallback_data['volume_values'] = volume_values
        
        # Cache the fallback data too, but with shorter expiry
        update_cache(ticker_symbol, fallback_data)
        
        return fallback_data

def get_timeseries_data(ticker_symbol=None):
    """Ruft Zeitreihendaten für das angegebene Ticker-Symbol ab mit Caching."""
    if ticker_symbol is None:
        ticker_symbol = "EUNL.DE"  # Standard-Ticker, falls keiner angegeben
    
    try:
        # Get ticker data with caching and rate limit protection
        ticker_data = fetch_ticker_data_safely(ticker_symbol)
        
        # Verify that we have full timeseries data
        if not ticker_data.get('full_history', False) or not ticker_data.get('dates') or not ticker_data.get('values'):
            print(f"Cache for {ticker_symbol} does not contain full history data. Refreshing...")
            
            # Force a refresh of the data
            cache_file = os.path.join(CACHE_DIR, f"{ticker_symbol.replace('/', '_').replace(':', '_')}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                
            # Add a delay to avoid rate limiting
            time.sleep(random.uniform(0.5, 2.0))
                
            # Fetch fresh data with full history
            ticker_data = fetch_ticker_data_safely(ticker_symbol)
        
        # Get portfolio-specific information
        return update_with_portfolio_info(ticker_data, ticker_symbol)
        
    except Exception as e:
        print(f"Fehler beim Abrufen der Daten für {ticker_symbol}: {e}")
        # Fallback mit Dummy-Daten
        current_datetime = datetime.now()
        dummy_dates = [(current_datetime - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(365, 0, -1)]
        dummy_values = [100 + (i % 20) + (i // 20) for i in range(365)]  # Generate some pattern
        
        return {
            'ticker': ticker_symbol,
            'dates': dummy_dates,
            'values': dummy_values,
            'last_close': dummy_values[-1],
            'last_date': dummy_dates[-1],
            'last_datetime': f"{dummy_dates[-1]} 17:30:00",
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'full_history': True,
            'error': str(e),
            'is_fallback': True
        }

def update_with_portfolio_info(data, ticker_symbol):
    """Updates the data with portfolio-specific information."""
    try:
        # Get portfolio data
        portfolio_data = get_portfolio_data()
        
        # Find security info in portfolio
        security_info = None
        for asset_class in ['etf', 'stocks', 'bonds', 'commodities', 'realEstate']:
            for asset in portfolio_data.get(asset_class, []):
                if asset.get('ticker') == ticker_symbol:
                    security_info = asset
                    break
            if security_info:
                break
                
        # If we found security info, add it to the data
        if security_info:
            data.update({
                'name': security_info.get('name', ''),
                'currency': security_info.get('currency', 'EUR'),
                'isin': security_info.get('isin', ''),
                'amount': security_info.get('amount', 0),
                'acquisition_cost': security_info.get('acquisition_cost', 0)
            })
            
            # Calculate current value and gain/loss
            last_close = data.get('last_close', 0)
            amount = security_info.get('amount', 0)
            data['current_value'] = last_close * amount
            
            # Calculate gain/loss if acquisition cost is available
            if 'acquisition_cost' in security_info and security_info['acquisition_cost'] > 0:
                data['gain_loss'] = data['current_value'] - security_info['acquisition_cost']
                data['gain_loss_percent'] = (data['gain_loss'] / security_info['acquisition_cost']) * 100
                
                # Generate earnings data for visualization (performance relative to acquisition cost over time)
                if 'values' in data and len(data['values']) > 0:
                    # Ensure we have the values as float
                    values = [float(val) for val in data['values']]
                    
                    # Calculate earnings for each point in time (current value - acquisition cost)
                    earnings_values = []
                    for value in values:
                        earnings = (value * amount) - security_info['acquisition_cost']
                        earnings_values.append(earnings)
                    
                    data['earnings_values'] = earnings_values
                    
                    # Add relative performance to the acquisition cost (percentage gain/loss)
                    performance_percent = []
                    for value in values:
                        current_value = value * amount
                        perf = ((current_value / security_info['acquisition_cost']) - 1) * 100 if security_info['acquisition_cost'] > 0 else 0
                        performance_percent.append(perf)
                    
                    data['performance_percent'] = performance_percent
                
        return data
        
    except Exception as e:
        print(f"Error updating portfolio info: {e}")
        return data

def process_timeseries(params):
    # Ticker-Symbol aus den Parametern extrahieren
    ticker_symbol = params.get('ticker', 'EUNL.DE')
    
    # Daten für das ausgewählte Wertpapier abrufen
    data = get_timeseries_data(ticker_symbol)
    
    # Sicherstellen, dass wir Daten haben und diese in ein DataFrame konvertieren
    if not data.get('dates') or not data.get('values') or len(data['dates']) != len(data['values']):
        raise ValueError(f"Unvollständige Daten für {ticker_symbol}")
    
    df = pd.DataFrame({
        'date': pd.to_datetime(data['dates']),
        'value': data['values']
    })
    
    # Zusätzliche OHLC-Daten hinzufügen, wenn verfügbar
    if 'open_values' in data and len(data['open_values']) == len(data['dates']):
        df['open'] = data['open_values']
    if 'high_values' in data and len(data['high_values']) == len(data['dates']):
        df['high'] = data['high_values']
    if 'low_values' in data and len(data['low_values']) == len(data['dates']):
        df['low'] = data['low_values']
    if 'volume_values' in data and len(data['volume_values']) == len(data['dates']):
        df['volume'] = data['volume_values']
    
    # Nach Zeitraum filtern
    timeframe = params.get('timeframe', '1y')
    end_date = datetime.now()
    
    if timeframe == '1m':
        start_date = end_date - timedelta(days=30)
    elif timeframe == '3m':
        start_date = end_date - timedelta(days=90)
    elif timeframe == '6m':
        start_date = end_date - timedelta(days=180)
    elif timeframe == '1y':
        start_date = end_date - timedelta(days=365)
    else:  # 'all'
        start_date = df['date'].min()
    
    filtered_df = df[df['date'] >= pd.Timestamp(start_date)]
    
    # Wenn nach dem Filtern keine Daten übrig sind, einen Fehler ausgeben
    if filtered_df.empty:
        raise ValueError(f"Keine Daten für {ticker_symbol} im ausgewählten Zeitraum")
    
    # Indikator berechnen
    indicator = params.get('indicator', 'sma')
    indicator_values = []
    indicator_dates = filtered_df['date'].dt.strftime('%Y-%m-%d').tolist()
    
    if indicator == 'sma':
        # Simple Moving Average (20 Perioden)
        window = 20
        sma = filtered_df['value'].rolling(window=window).mean()
        # NaN-Werte entfernen und sicherstellen, dass die Listen gleich lang sind
        indicator_values = sma.fillna(method='bfill').tolist()
    
    elif indicator == 'ema':
        # Exponential Moving Average (20 Perioden)
        window = 20
        ema = filtered_df['value'].ewm(span=window, adjust=False).mean()
        indicator_values = ema.tolist()
    
    elif indicator == 'bollinger':
        # Bollinger Bands (20 Perioden, 2 Standardabweichungen)
        window = 20
        std_dev = 2
        
        # Mittlere Linie (SMA)
        middle_band = filtered_df['value'].rolling(window=window).mean()
        
        # Obere und untere Bänder
        std = filtered_df['value'].rolling(window=window).std()
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        # NaN-Werte entfernen und sicherstellen, dass die Listen gleich lang sind
        middle_band = middle_band.fillna(method='bfill')
        upper_band = upper_band.fillna(method='bfill')
        lower_band = lower_band.fillna(method='bfill')
        
        # Speichere alle drei Linien
        indicator_values = {
            'middle': middle_band.tolist(),
            'upper': upper_band.tolist(),
            'lower': lower_band.tolist()
        }
    
    # Statistiken berechnen
    stats = {
        'mean': float(filtered_df['value'].mean()),
        'std': float(filtered_df['value'].std()),
        'min': float(filtered_df['value'].min()),
        'max': float(filtered_df['value'].max()),
        'latest': float(filtered_df['value'].iloc[-1]) if not filtered_df.empty else 0,
        'first': float(filtered_df['value'].iloc[0]) if not filtered_df.empty else 0,
        'change': float(filtered_df['value'].iloc[-1] - filtered_df['value'].iloc[0]) if not filtered_df.empty else 0,
        'change_percent': float((filtered_df['value'].iloc[-1] / filtered_df['value'].iloc[0] - 1) * 100) if not filtered_df.empty and filtered_df['value'].iloc[0] > 0 else 0,
        'data_points': len(filtered_df)
    }
    
    # OHLC Statistiken hinzufügen, wenn verfügbar
    if 'open' in filtered_df.columns:
        stats['open_latest'] = float(filtered_df['open'].iloc[-1]) if not filtered_df.empty else 0
    if 'high' in filtered_df.columns:
        stats['high_max'] = float(filtered_df['high'].max()) if not filtered_df.empty else 0
    if 'low' in filtered_df.columns:
        stats['low_min'] = float(filtered_df['low'].min()) if not filtered_df.empty else 0
    if 'volume' in filtered_df.columns:
        stats['volume_avg'] = float(filtered_df['volume'].mean()) if not filtered_df.empty else 0
        stats['volume_latest'] = float(filtered_df['volume'].iloc[-1]) if not filtered_df.empty else 0
    
    # Portfolio-Informationen in die Statistiken einfügen
    if 'amount' in data:
        stats['amount'] = data.get('amount', 0)
    if 'last_close' in data:
        stats['last_close'] = data.get('last_close', 0)
    if 'last_date' in data:
        stats['last_date'] = data.get('last_date', '')
    if 'last_datetime' in data:
        stats['last_datetime'] = data.get('last_datetime', '')
    if 'current_value' in data:
        stats['current_value'] = data.get('current_value', 0)
    if 'acquisition_cost' in data:
        stats['acquisition_cost'] = data.get('acquisition_cost', 0)
    if 'gain_loss' in data:
        stats['gain_loss'] = data.get('gain_loss', 0)
        stats['gain_loss_percent'] = data.get('gain_loss_percent', 0)
    
    # Prepare earnings data if available
    earnings_values = None
    if 'earnings_values' in data and len(data['earnings_values']) == len(data['values']):
        # Filter earnings_values to match the timeframe
        if len(data['earnings_values']) == len(data['dates']):
            earnings_df = pd.DataFrame({
                'date': pd.to_datetime(data['dates']),
                'earnings': data['earnings_values']
            })
            filtered_earnings_df = earnings_df[earnings_df['date'] >= pd.Timestamp(start_date)]
            earnings_values = filtered_earnings_df['earnings'].tolist()
    
    # Ergebnisse zurückgeben
    result = {
        'dates': indicator_dates,
        'values': filtered_df['value'].tolist(),
        'indicator': indicator,
        'indicator_values': indicator_values,
        'stats': stats,
        'ticker': ticker_symbol,  # Ticker-Symbol zurückgeben für Frontend-Anzeige
        'timeframe': timeframe,
        'full_history': data.get('full_history', False),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    # OHLC-Daten hinzufügen, wenn verfügbar
    if 'open' in filtered_df.columns:
        result['open_values'] = filtered_df['open'].tolist()
    if 'high' in filtered_df.columns:
        result['high_values'] = filtered_df['high'].tolist()
    if 'low' in filtered_df.columns:
        result['low_values'] = filtered_df['low'].tolist()
    if 'volume' in filtered_df.columns:
        result['volume_values'] = filtered_df['volume'].tolist()
    
    # Add earnings values if available
    if earnings_values:
        result['earnings_values'] = earnings_values
    
    # Zusätzliche Informationen aus data übernehmen
    for key in ['name', 'currency', 'isin', 'amount', 'acquisition_cost', 'current_value', 
                'gain_loss', 'gain_loss_percent', 'last_date', 'last_datetime', 'fetch_time']:
        if key in data:
            result[key] = data[key]
    
    return result