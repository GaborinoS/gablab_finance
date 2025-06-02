# app/modules/wl_ticker/routes.py
from flask import render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.modules.wl_ticker import bp
from app.modules.wl_ticker.services import WLTickerService
from app.models import db, WLTickerStation
import json

@bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    user_stations = WLTickerStation.query.filter_by(user_id=current_user.id).all()
    return render_template('wl_ticker/index.html', stations=user_stations)

@bp.route('/search_stations')
@login_required
def search_stations():
    """Search for stations by name"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': []})
    
    service = WLTickerService()
    results = service.search_stations(query)
    return jsonify({'results': results})

@bp.route('/add_station', methods=['POST'])
@login_required
def add_station():
    """Add a new station to user's dashboard"""
    data = request.get_json()
    
    station_name = data.get('station_name')
    stop_id = data.get('stop_id')
    
    if not station_name or not stop_id:
        return jsonify({'success': False, 'message': 'Missing required data'})
    
    # Check if station already exists for user (by station name, not stop_id)
    # This prevents adding the same station multiple times even with different stop_ids
    existing = WLTickerStation.query.filter_by(
        user_id=current_user.id, 
        station_name=station_name
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Station bereits hinzugefügt'})
    
    # Add new station
    new_station = WLTickerStation(
        user_id=current_user.id,
        station_name=station_name,
        stop_id=stop_id
    )
    
    try:
        db.session.add(new_station)
        db.session.commit()
        
        # Get station info for logging
        service = WLTickerService()
        station_info = service.get_station_info(stop_id)
        if station_info:
            print(f"Added station '{station_name}' with {station_info['stop_count']} platforms/directions")
        
        return jsonify({'success': True, 'station_id': new_station.id})
    except Exception as e:
        db.session.rollback()
        print(f"Error adding station: {e}")
        return jsonify({'success': False, 'message': 'Database error'})

@bp.route('/remove_station/<int:station_id>', methods=['DELETE'])
@login_required
def remove_station(station_id):
    """Remove a station from user's dashboard"""
    station = WLTickerStation.query.filter_by(
        id=station_id, 
        user_id=current_user.id
    ).first()
    
    if not station:
        return jsonify({'success': False, 'message': 'Station not found'})
    
    try:
        db.session.delete(station)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Database error'})

@bp.route('/departures/<int:station_id>')
@login_required
def get_departures(station_id):
    """Get live departures for a specific station (all directions)"""
    station = WLTickerStation.query.filter_by(
        id=station_id, 
        user_id=current_user.id
    ).first()
    
    if not station:
        return jsonify({'error': 'Station not found'})
    
    service = WLTickerService()
    departures = service.get_departures(station.stop_id)
    
    # Get additional station info
    station_info = service.get_station_info(station.stop_id)
    
    return jsonify({
        'station_name': station.station_name,
        'departures': departures,
        'last_updated': service.get_current_time(),
        'station_info': station_info,
        'platform_count': station_info['stop_count'] if station_info else 1
    })

@bp.route('/departures/all')
@login_required
def get_all_departures():
    """Get departures for all user stations (all directions)"""
    user_stations = WLTickerStation.query.filter_by(user_id=current_user.id).all()
    service = WLTickerService()
    
    results = {}
    for station in user_stations:
        departures = service.get_departures(station.stop_id)
        station_info = service.get_station_info(station.stop_id)
        
        results[station.id] = {
            'station_name': station.station_name,
            'departures': departures,
            'last_updated': service.get_current_time(),
            'station_info': station_info,
            'platform_count': station_info['stop_count'] if station_info else 1
        }
    
    return jsonify(results)

@bp.route('/station_info/<int:station_id>')
@login_required
def get_station_info(station_id):
    """Get detailed information about a station"""
    station = WLTickerStation.query.filter_by(
        id=station_id, 
        user_id=current_user.id
    ).first()
    
    if not station:
        return jsonify({'error': 'Station not found'})
    
    service = WLTickerService()
    station_info = service.get_station_info(station.stop_id)
    
    return jsonify(station_info)