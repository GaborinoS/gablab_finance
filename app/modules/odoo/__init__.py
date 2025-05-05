from flask import Blueprint

bp = Blueprint('odoo', __name__)

from app.modules.odoo import routes