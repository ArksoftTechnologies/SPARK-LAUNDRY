from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    
    from app.utils.email import mail
    mail.init_app(app)

    # Register Blueprints (API)
    from .api import api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    from .web import web as web_blueprint
    app.register_blueprint(web_blueprint)

    # Main Routes are now in the 'web' blueprint

    return app
