# __init__.py file
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Namma_Kadai.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize the LoginManager instance
login_manager = LoginManager()
login_manager.init_app(app)  # Correctly initialize login_manager

login_manager.login_view = 'login'  # Define the login view

# Import routes after app initialization
from Namma_Kadai import routes
