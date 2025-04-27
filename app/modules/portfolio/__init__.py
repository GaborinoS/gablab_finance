from flask import Blueprint

bp = Blueprint('portfolio', __name__, template_folder='templates')

from app.modules.portfolio import routes