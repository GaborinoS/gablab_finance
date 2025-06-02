# app/modules/wl_ticker/__init__.py
from flask import Blueprint

bp = Blueprint('wl_ticker', __name__, template_folder='templates')

from app.modules.wl_ticker import routes