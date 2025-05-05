from flask import render_template, jsonify, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import requests
from app.modules.odoo import bp

# Odoo configuration
ODOO_HOST = '10.0.0.43'
ODOO_PORT = 8069

@bp.route('/')
@login_required
def index():
    """Main Odoo page that embeds the Odoo interface"""
    odoo_url = f"http://{ODOO_HOST}:{ODOO_PORT}"
    return render_template('odoo/index.html', odoo_url=odoo_url)

@bp.route('/proxy', defaults={'path': ''})
@bp.route('/proxy/<path:path>')
@login_required
def proxy(path):
    """Proxy requests to Odoo server"""
    target_url = f'http://{ODOO_HOST}:{ODOO_PORT}/{path}'
    print(f"Proxying request to: {target_url}")  # Debug print
    
    try:
        # Forward the request to Odoo
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)
        
        print(f"Response status: {resp.status_code}")  # Debug print
        
        # Create response
        response = current_app.response_class(
            response=resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'text/html')
        )
        
        # Pass through headers
        for key, value in resp.headers.items():
            if key.lower() not in ('content-length', 'transfer-encoding', 'connection'):
                response.headers[key] = value
                
        return response
    except Exception as e:
        print(f"Proxy error: {str(e)}")  # Debug print
        return f"Error connecting to Odoo: {str(e)}", 500