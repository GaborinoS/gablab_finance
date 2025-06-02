# app/modules/wl_ticker/services.py
import requests
import pandas as pd
import os
import time
import random
import re
from datetime import datetime
from fuzzywuzzy import process
from flask import current_app

class WLTickerService:
    """Service class for Wiener Linien API operations"""
    
    def __init__(self):
        # Use the exact same URL as your working test
        self.base_url = "http://www.wienerlinien.at/ogd_realtime/monitor"
        self.stations_file = os.path.join(current_app.root_path, 'data', 'wienerlinien-ogd-haltepunkte.csv')
        self._stations_df = None
        
        # Simple headers - just like your test script
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Moderate rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
    
    @property
    def stations_df(self):
        """Lazy load stations data"""
        if self._stations_df is None:
            try:
                self._stations_df = pd.read_csv(self.stations_file, sep=';')
            except FileNotFoundError:
                current_app.logger.error(f"Stations file not found: {self.stations_file}")
                self._stations_df = pd.DataFrame()
        return self._stations_df
    
    def search_stations(self, search_term, limit=10):
        """Search for stations using fuzzy matching"""
        if self.stations_df.empty:
            return []
        
        unique_stations = self.stations_df['StopText'].unique()
        matches = process.extract(search_term, unique_stations, limit=limit)
        
        results = []
        for station_name, score in matches:
            if score >= 50:
                station_data = self.stations_df[
                    self.stations_df['StopText'] == station_name
                ]
                
                stop_ids = station_data['StopID'].unique()
                
                results.append({
                    'station_name': station_name,
                    'stop_id': int(stop_ids[0]),
                    'all_stop_ids': [int(sid) for sid in stop_ids],
                    'similarity_score': score
                })
        
        return results
    
    def _remove_duplicates(self, departures):
        """Remove duplicate departures while preserving different lines"""
        seen = set()
        unique_departures = []
        
        for dep in departures:
            # Create key that distinguishes different lines and times
            # but removes exact duplicates
            dedup_key = f"{dep['line']}_{dep['direction']}_{dep['countdown']}"
            
            if dedup_key not in seen:
                seen.add(dedup_key)
                unique_departures.append(dep)
        
        return unique_departures
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_departures(self, stop_id):
        """Get departures for a station - fetch ALL stop IDs"""
        # Get all stop IDs for this station
        all_stop_ids = self._get_all_stop_ids_for_station(stop_id)
        
        current_app.logger.info(f"Found {len(all_stop_ids)} stop IDs for station: {all_stop_ids}")
        
        all_departures = []
        successful_fetches = 0
        
        # Fetch from ALL stop IDs to get complete data (like your test script)
        for i, sid in enumerate(all_stop_ids):
            current_app.logger.info(f"Fetching departures for stop ID {sid} ({i+1}/{len(all_stop_ids)})")
            
            # Add small delay between requests to avoid overwhelming API
            if i > 0:
                time.sleep(1.5)
            
            departures = self._fetch_departures_for_stop(sid)
            
            if departures:
                current_app.logger.info(f"SUCCESS: Got {len(departures)} departures from stop {sid}")
                all_departures.extend(departures)
                successful_fetches += 1
            else:
                current_app.logger.warning(f"FAILED: No departures from stop {sid}")
        
        current_app.logger.info(f"SUMMARY: {successful_fetches}/{len(all_stop_ids)} stops returned data")
        
        if not all_departures:
            current_app.logger.error(f"NO DEPARTURES FOUND from any of the {len(all_stop_ids)} stop IDs")
            return []
        
        # Remove duplicates while preserving all lines
        unique_departures = self._remove_duplicates(all_departures)
        
        # Sort by line type and countdown
        unique_departures.sort(key=lambda x: (
            self._get_line_type_priority(x['line']),
            self._get_line_number(x['line']),
            x['countdown']
        ))
        
        # Log what lines we found
        lines_found = set(dep['line'] for dep in unique_departures)
        current_app.logger.info(f"FINAL RESULT: Found lines {sorted(lines_found)} with {len(unique_departures)} total departures")
        
        return unique_departures  # Return ALL departures, don't limit here
    
    def _get_all_stop_ids_for_station(self, stop_id):
        """Get all stop IDs for a station (different directions)"""
        if self.stations_df.empty:
            return [stop_id]
        
        # Find station name
        station_row = self.stations_df[self.stations_df['StopID'] == stop_id]
        if station_row.empty:
            return [stop_id]
        
        station_name = station_row['StopText'].iloc[0]
        
        # Get all stop IDs for this station
        all_rows = self.stations_df[self.stations_df['StopText'] == station_name]
        stop_ids = all_rows['StopID'].unique().tolist()
        
        return stop_ids
    
    def _fetch_departures_for_stop(self, stop_id):
        """Fetch departures for a single stop ID with detailed logging like test script"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}?stopId={stop_id}"
            print(f"\n========================================")
            print(f"Haltestelle: {stop_id}")
            print(f"URL: {url}")
            print(f"========================================")
            current_app.logger.info(f"Making request to: {url}")
            
            # Exactly like your test script
            response = requests.get(url, headers=self.headers, timeout=10)
            
            print(f"Response status: {response.status_code}")
            current_app.logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"ERROR: HTTP {response.status_code} for stop {stop_id}")
                current_app.logger.error(f"HTTP {response.status_code} for stop {stop_id}")
                return []
            
            data = response.json()
            
            # Check data structure like your test
            if "data" not in data:
                print(f"ERROR: No 'data' field in response for stop {stop_id}")
                current_app.logger.warning(f"No 'data' field in response for stop {stop_id}")
                return []
                
            if "monitors" not in data["data"]:
                print(f"ERROR: No 'monitors' field in response for stop {stop_id}")
                current_app.logger.warning(f"No 'monitors' field in response for stop {stop_id}")
                return []
            
            monitors = data["data"]["monitors"]
            print(f"Found {len(monitors)} monitors for stop {stop_id}")
            current_app.logger.info(f"Found {len(monitors)} monitors for stop {stop_id}")
            
            if not monitors:
                print(f"WARNING: Empty monitors list for stop {stop_id}")
                return []
            
            departures = []
            departure_count = 0
            
            # Process exactly like your test script
            for monitor_idx, monitor in enumerate(monitors):
                try:
                    location = monitor["locationStop"]["properties"]["title"]
                    print(f"Monitor {monitor_idx}: Location = {location}")
                    
                    if "lines" not in monitor:
                        print(f"  No 'lines' in monitor {monitor_idx}")
                        continue
                        
                    lines = monitor["lines"]
                    print(f"  Found {len(lines)} lines in monitor {monitor_idx}")
                    
                    for line_idx, line in enumerate(lines):
                        try:
                            line_name = line["name"]
                            towards = line["towards"]
                            print(f"    Line {line_idx}: {line_name} → {towards}")
                            
                            if "departures" not in line:
                                print(f"      No 'departures' field for line {line_name}")
                                continue
                                
                            if "departure" not in line["departures"]:
                                print(f"      No 'departure' field in departures for line {line_name}")
                                continue
                                
                            line_departures = line["departures"]["departure"]
                            print(f"      Found {len(line_departures)} departures for {line_name}")
                            
                            for dep_idx, departure in enumerate(line_departures):
                                try:
                                    countdown = departure["departureTime"]["countdown"]
                                    departure_count += 1
                                    
                                    # Print like your test script
                                    print(f"        Linie: {line_name} - Richtung: {towards} - Abfahrt in {countdown} Minuten")
                                    
                                    # Format time display
                                    if countdown == 0:
                                        time_display = "Jetzt"
                                    elif countdown < 60:
                                        time_display = f"{countdown} min"
                                    else:
                                        time_display = f"{countdown // 60}h {countdown % 60}min"
                                    
                                    # Check for realtime data
                                    planned_time = departure.get('departureTime', {}).get('timePlanned')
                                    real_time = departure.get('departureTime', {}).get('timeReal')
                                    is_realtime = planned_time != real_time and real_time is not None
                                    
                                    departure_info = {
                                        'line': line_name,
                                        'direction': towards,
                                        'countdown': countdown,
                                        'time_display': time_display,
                                        'platform': departure.get('platform', {}).get('text', ''),
                                        'realtime': is_realtime,
                                        'stop_id': stop_id,
                                        'location': location,
                                        'unique_id': f"{line_name}_{towards}_{countdown}_{stop_id}"
                                    }
                                    
                                    departures.append(departure_info)
                                    
                                except Exception as e:
                                    print(f"        ERROR processing departure {dep_idx}: {e}")
                                    continue
                                    
                        except Exception as e:
                            print(f"    ERROR processing line {line_idx}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"  ERROR processing monitor {monitor_idx}: {e}")
                    continue
            
            print(f"TOTAL DEPARTURES PARSED: {len(departures)} (raw count: {departure_count})")
            print(f"========================================\n")
            
            current_app.logger.info(f"Parsed {len(departures)} departures from stop {stop_id}")
            return departures
            
        except requests.exceptions.RequestException as e:
            print(f"REQUEST ERROR for stop {stop_id}: {e}")
            current_app.logger.error(f"Request error for stop {stop_id}: {e}")
            return []
        except Exception as e:
            print(f"UNEXPECTED ERROR for stop {stop_id}: {e}")
            current_app.logger.error(f"Unexpected error for stop {stop_id}: {e}")
            return []
    
    def _get_line_type_priority(self, line):
        """Get priority for line type sorting"""
        if line.startswith('U'): 
            return 1  # U-Bahn first
        if line.startswith('S'): 
            return 2  # S-Bahn
        if re.match(r'^\d+$', line): 
            return 3  # Tram
        if re.match(r'^[0-9]+[AB]$', line): 
            return 4  # Bus
        return 5  # Other
    
    def _get_line_number(self, line):
        """Extract numeric part for sorting"""
        match = re.match(r'^[A-Z]*(\d+)', line)
        return int(match.group(1)) if match else 999
    
    def get_current_time(self):
        """Get current time formatted for display"""
        return datetime.now().strftime('%H:%M:%S')
    
    def get_station_info(self, stop_id):
        """Get station information"""
        if self.stations_df.empty:
            return None
        
        station_row = self.stations_df[self.stations_df['StopID'] == stop_id]
        if station_row.empty:
            return None
        
        station_name = station_row['StopText'].iloc[0]
        all_stops = self.stations_df[self.stations_df['StopText'] == station_name]
        
        return {
            'station_name': station_name,
            'stop_count': len(all_stops),
            'all_stop_ids': all_stops['StopID'].tolist(),
            'platforms': all_stops[['StopID', 'StopText']].to_dict('records')
        }