from flask import render_template, jsonify, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import requests
from app.modules.odoo import bp

# Odoo configuration
ODOO_HOST = '10.0.0.43'
ODOO_PORT = 8069  # Use 8069 or change to 8071 if you want to connect to the other instance

@bp.route('/')
@login_required
def index():
    # Point to the working Odoo instance on port 8069
    odoo_url = "http://localhost:8069"
    return render_template('odoo/index.html', odoo_url=odoo_url)
    
@bp.route('/proxy', defaults={'path': ''})
@bp.route('/proxy/<path:path>')
@login_required
def proxy(path):
    """Proxy requests to Odoo server with improved headers and cookie handling"""
    target_url = f'http://{ODOO_HOST}:{ODOO_PORT}/{path}'
    print(f"Proxying request to: {target_url}")
    
    try:
        # Copy request headers but exclude Host
        headers = {key: value for (key, value) in request.headers.items() 
                  if key.lower() not in ('host', 'content-length')}
        
        # Forward the request to Odoo with all cookies
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=True)
        
        print(f"Response status: {resp.status_code}")
        
        # Create response
        response = current_app.response_class(
            response=resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'text/html')
        )
        
        # Pass through all headers from the Odoo response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        for name, value in resp.headers.items():
            if name.lower() not in excluded_headers:
                response.headers[name] = value
                
        # Ensure cookie sessions are properly passed
        if 'set-cookie' in resp.headers:
            response.headers['Set-Cookie'] = resp.headers['set-cookie']
        
        return response
    except Exception as e:
        print(f"Proxy error: {str(e)}")
        return f"Error connecting to Odoo: {str(e)}", 500