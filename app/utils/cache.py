from datetime import datetime, timedelta
import json
import os
from sqlalchemy import Column, String, DateTime, Text
from app import db

class TickerCache(db.Model):
    """Model for caching ticker data"""
    __tablename__ = 'ticker_cache'
    
    ticker = Column(String(20), primary_key=True)
    last_updated = Column(DateTime, default=datetime.now)
    data = Column(Text)  # JSON string of the ticker data
    
    @staticmethod
    def get_cached_data(ticker):
        """Get cached data for a ticker if it exists and is fresh"""
        cache_entry = TickerCache.query.get(ticker)
        
        if cache_entry is None:
            return None
            
        # Check if data is stale (older than 6 hours)
        time_diff = datetime.now() - cache_entry.last_updated
        if time_diff > timedelta(hours=6):
            return None
            
        return json.loads(cache_entry.data)
    
    @staticmethod
    def update_cache(ticker, data):
        """Update the cache for a ticker"""
        cache_entry = TickerCache.query.get(ticker)
        
        if cache_entry is None:
            cache_entry = TickerCache(ticker=ticker)
            db.session.add(cache_entry)
            
        cache_entry.data = json.dumps(data)
        cache_entry.last_updated = datetime.now()
        db.session.commit()
        
    @staticmethod
    def is_cache_fresh(ticker):
        """Check if the cache for a ticker is fresh (updated within the last 6 hours)"""
        cache_entry = TickerCache.query.get(ticker)
        
        if cache_entry is None:
            return False
            
        time_diff = datetime.now() - cache_entry.last_updated
        return time_diff <= timedelta(hours=6)

def get_cache_dir():
    """Get the directory for file-based cache (as an alternative to DB)"""
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir

def get_cached_file_data(ticker):
    """Get cached data from file for a ticker if it exists and is fresh"""
    cache_dir = get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{ticker}.json")
    
    if not os.path.exists(cache_file):
        return None
        
    # Check if file is stale (older than 6 hours)
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

def update_file_cache(ticker, data):
    """Update the file cache for a ticker"""
    cache_dir = get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{ticker}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing cache file for {ticker}: {e}")

def is_file_cache_fresh(ticker):
    """Check if the file cache for a ticker is fresh (updated within the last 6 hours)"""
    cache_dir = get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{ticker}.json")
    
    if not os.path.exists(cache_file):
        return False
        
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    time_diff = datetime.now() - file_time
    return time_diff <= timedelta(hours=6)