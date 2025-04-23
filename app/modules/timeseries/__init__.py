from flask import Blueprint

bp = Blueprint('timeseries', __name__, template_folder='templates')

from app.modules.timeseries import routes