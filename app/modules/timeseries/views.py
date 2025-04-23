import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
from flask import current_app

def get_available_securities():
    """Liest die Portfolio-Daten aus der JSON-Datei und gibt eine Liste aller verfügbaren Wertpapiere zurück."""
    try:
        data_path = os.path.join(current_app.root_path, 'data', 'portfolio_data.json')
        with open(data_path, 'r') as file:
            portfolio_data = json.load(file)
            
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
        return None

def get_timeseries_data(ticker_symbol=None):
    """Ruft Zeitreihendaten für das angegebene Ticker-Symbol ab."""
    if ticker_symbol is None:
        ticker_symbol = "EUNL.DE"  # Standard-Ticker, falls keiner angegeben
    
    try:
        # Zunächst Informationen aus der Portfolio-JSON-Datei laden
        data_path = os.path.join(current_app.root_path, 'data', 'portfolio_data.json')
        with open(data_path, 'r') as file:
            portfolio_data = json.load(file)
        
        # Wertpapierinformationen suchen
        security_info = None
        
        # Alle Anlageklassen durchsuchen
        for asset_class in ['etf', 'stocks', 'bonds', 'commodities', 'realEstate']:
            for asset in portfolio_data.get(asset_class, []):
                if asset.get('ticker') == ticker_symbol:
                    security_info = asset
                    break
            if security_info:
                break
        
        # Ticker-Objekt erstellen und historische Daten abrufen
        ticker = yf.Ticker(ticker_symbol)
        historical_data = ticker.history(period="max")
        
        if historical_data.empty:
            raise ValueError(f"Keine Daten für Ticker {ticker_symbol} gefunden")
            
        historical_data.reset_index(inplace=True)
        
        # Konvertiere Zeitstempel in JSON-serialisierbare Strings
        dates = historical_data["Date"].dt.strftime('%Y-%m-%d').tolist()
        
        # Verwende die tatsächlichen Schlusskurse
        values = historical_data["Close"].tolist()
        
        # Letzter Schlusskurs und Zeitstempel für die Berechnung des aktuellen Werts
        last_close = values[-1] if values else 0
        
        # Zeitstempel des letzten Werts mit Datum und Uhrzeit
        if len(historical_data) > 0:
            last_date = historical_data["Date"].iloc[-1]
            last_date_str = last_date.strftime('%Y-%m-%d')
            
            # Für die Anzeige mit Uhrzeit
            # Yahoo Finance gibt lokale Börsenzeiten zurück, wir fügen die Uhrzeit hinzu,
            # sofern sie verfügbar ist, sonst verwenden wir Börsenschluss
            try:
                # Versuchen, die Uhrzeit aus den Daten zu extrahieren
                if 'Datetime' in historical_data.columns:
                    last_datetime = historical_data["Datetime"].iloc[-1]
                    last_datetime_str = last_datetime.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # Wenn keine Uhrzeit verfügbar ist, verwenden wir den Börsenschluss,
                    # der je nach Börse variieren kann (typischerweise 17:30 Uhr für europäische Börsen)
                    if security_info and security_info.get('currency') == 'USD':
                        # US-Börsen schließen um 16:00 Uhr EST
                        closing_time = "16:00"
                    else:
                        # Europäische Börsen schließen um 17:30 Uhr MEZ
                        closing_time = "17:30"
                    last_datetime_str = f"{last_date_str} {closing_time}"
            except Exception as e:
                print(f"Fehler beim Extrahieren der Uhrzeit: {e}")
                last_datetime_str = f"{last_date_str} 00:00:00"
        else:
            last_date_str = "Unbekannt"
            last_datetime_str = "Unbekannt"
        
        result = {
            'dates': dates,
            'values': values,
            'raw_data': historical_data,
            'ticker': ticker_symbol,
            'last_close': last_close,
            'last_date': last_date_str,
            'last_datetime': last_datetime_str
        }
        
        # Portfolio-Informationen hinzufügen, falls vorhanden
        if security_info:
            result.update({
                'name': security_info.get('name', ''),
                'currency': security_info.get('currency', 'EUR'),
                'isin': security_info.get('isin', ''),
                'amount': security_info.get('amount', 0),
                'acquisition_cost': security_info.get('acquisition_cost', 0)
            })
            
            # Berechne den aktuellen Gesamtwert (letzter Schlusskurs × Anzahl)
            result['current_value'] = last_close * security_info.get('amount', 0)
            
            # Gewinn/Verlust berechnen, falls Einstandswert vorhanden
            if 'acquisition_cost' in security_info and security_info['acquisition_cost'] > 0:
                result['gain_loss'] = result['current_value'] - security_info['acquisition_cost']
                result['gain_loss_percent'] = (result['gain_loss'] / security_info['acquisition_cost']) * 100
        
        return result
    
    except Exception as e:
        print(f"Fehler beim Abrufen der Daten für {ticker_symbol}: {e}")
        # Fallback mit Dummy-Daten
        current_datetime = datetime.now()
        dummy_dates = [(current_datetime - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
        dummy_values = [100 + i for i in range(30)]
        return {
            'dates': dummy_dates,
            'values': dummy_values,
            'ticker': ticker_symbol,
            'error': str(e),
            'last_date': current_datetime.strftime('%Y-%m-%d'),
            'last_datetime': current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
def process_timeseries(params):
    # Ticker-Symbol aus den Parametern extrahieren
    ticker_symbol = params.get('ticker', 'EUNL.DE')
    
    # Daten für das ausgewählte Wertpapier abrufen
    data = get_timeseries_data(ticker_symbol)
    
    df = pd.DataFrame({
        'date': pd.to_datetime(data['dates']),
        'value': data['values']
    })
    
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
        'mean': filtered_df['value'].mean(),
        'std': filtered_df['value'].std(),
        'min': filtered_df['value'].min(),
        'max': filtered_df['value'].max()
    }
    
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
    
    # Ergebnisse zurückgeben
    result = {
        'dates': indicator_dates,
        'values': filtered_df['value'].tolist(),
        'indicator': indicator,
        'indicator_values': indicator_values,
        'stats': stats,
        'ticker': ticker_symbol  # Ticker-Symbol zurückgeben für Frontend-Anzeige
    }
    
    # Zusätzliche Informationen aus data übernehmen
    for key in ['name', 'currency', 'isin', 'amount', 'acquisition_cost', 'current_value', 
                'gain_loss', 'gain_loss_percent', 'last_date', 'last_datetime']:
        if key in data:
            result[key] = data[key]
    
    return result
    # Ticker-Symbol aus den Parametern extrahieren
    ticker_symbol = params.get('ticker', 'EUNL.DE')
    
    # Daten für das ausgewählte Wertpapier abrufen
    data = get_timeseries_data(ticker_symbol)
    
    df = pd.DataFrame({
        'date': pd.to_datetime(data['dates']),
        'value': data['values']
    })
    
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
        'mean': filtered_df['value'].mean(),
        'std': filtered_df['value'].std(),
        'min': filtered_df['value'].min(),
        'max': filtered_df['value'].max()
    }
    
    # Portfolio-Informationen in die Statistiken einfügen
    if 'amount' in data:
        stats['amount'] = data.get('amount', 0)
    if 'last_close' in data:
        stats['last_close'] = data.get('last_close', 0)
    if 'last_date' in data:
        stats['last_date'] = data.get('last_date', '')
    if 'current_value' in data:
        stats['current_value'] = data.get('current_value', 0)
    if 'acquisition_cost' in data:
        stats['acquisition_cost'] = data.get('acquisition_cost', 0)
    if 'gain_loss' in data:
        stats['gain_loss'] = data.get('gain_loss', 0)
        stats['gain_loss_percent'] = data.get('gain_loss_percent', 0)
    
    # Ergebnisse zurückgeben
    result = {
        'dates': indicator_dates,
        'values': filtered_df['value'].tolist(),
        'indicator': indicator,
        'indicator_values': indicator_values,
        'stats': stats,
        'ticker': ticker_symbol  # Ticker-Symbol zurückgeben für Frontend-Anzeige
    }
    
    # Zusätzliche Informationen aus data übernehmen
    for key in ['name', 'currency', 'isin', 'amount', 'acquisition_cost', 'current_value', 'gain_loss', 'gain_loss_percent', 'last_date']:
        if key in data:
            result[key] = data[key]
    
    return result