from flask import Blueprint

bp = Blueprint('costincome', __name__, template_folder='templates')

from app.modules.costincome import routes