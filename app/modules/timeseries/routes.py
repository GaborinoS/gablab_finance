from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.modules.timeseries.views import get_timeseries_data, process_timeseries, get_available_securities
from app.modules.timeseries import bp

@bp.route('/')
@login_required
def index():
    # Alle verfügbaren Wertpapiere abrufen
    securities = get_available_securities()
    return render_template('timeseries/index.html', securities=securities)

@bp.route('/data')
@login_required
def data():
    # Ticker-Symbol aus der Anfrage extrahieren
    ticker = request.args.get('ticker', 'EUNL.DE')
    return jsonify(get_timeseries_data(ticker))

@bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    params = request.json
    results = process_timeseries(params)
    return jsonify(results)

@bp.route('/securities')
@login_required
def securities():
    # API-Endpunkt, um die Liste der Wertpapiere als JSON zurückzugeben
    return jsonify(get_available_securities())