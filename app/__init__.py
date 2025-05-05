from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Bitte loggen Sie sich ein, um diese Seite zu sehen.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    # Register main blueprint
    # Blueprint-Import in der Funktion, um zirkuläre Imports zu vermeiden
    from app.routes import main
    app.register_blueprint(main)
    
    # Register auth blueprint
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register modules
    from app.modules.timeseries import bp as timeseries_bp
    app.register_blueprint(timeseries_bp, url_prefix='/timeseries')
    
    # Register costincome module
    from app.modules.costincome import bp as costincome_bp
    app.register_blueprint(costincome_bp, url_prefix='/costincome')
    
    # Register portfolio module
    from app.modules.portfolio import bp as portfolio_bp
    app.register_blueprint(portfolio_bp, url_prefix='/portfolio')

        # Register odoo module
    from app.modules.odoo import bp as odoo_bp
    app.register_blueprint(odoo_bp, url_prefix='/odoo')
    
    # Create database tables - only needed for development
    with app.app_context():
        db.create_all()
    
    return app

from app.models import User

@login.user_loader
def load_user(id):
    return User.query.get(int(id))