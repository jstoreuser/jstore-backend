import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS # Import CORS

# Initialize SQLAlchemy instance without app
db = SQLAlchemy()
from src.routes.payment_routes import payment_bp
from src.routes.order_routes import order_bp
from src.routes.download_routes import download_bp
# from src.routes.game import game_bp # Optional

app = Flask(__name__, static_folder=None) # Disable default static folder handling
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key-for-dev") # Use environment variable

# Enable CORS for all domains on all routes, adjust origins for production
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

# Configure Database URI - Use DATABASE_URL from Render environment, fallback for local dev (optional)
database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"): # Render provides postgresql://, SQLAlchemy needs postgresql://
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Fallback to MySQL for local development if DATABASE_URL is not set (adjust as needed)
if not database_url:
    db_user = os.getenv("DB_USERNAME", "root")
    db_pass = os.getenv("DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "jstore_db")
    database_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    current_app.logger.warning("DATABASE_URL not set, falling back to local MySQL config.")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Register Blueprints
app.register_blueprint(payment_bp, url_prefix="/api/payment")
app.register_blueprint(order_bp, url_prefix="/api/order")
app.register_blueprint(download_bp, url_prefix="/api/download")
# app.register_blueprint(game_bp, url_prefix=	"/api/game	") # OptionalBasic route to check if API is running
@app.route('/api/health')
def health_check():
    return {"status": "ok"}

# Create database tables if they don't exist
# This is suitable for development, consider using migrations (Flask-Migrate) for production
with app.app_context():
    # Import models here to ensure they are registered with SQLAlchemy
    from src.models.order import Order # Import the Order model
    db.create_all()
    print(f"Database tables created (if not exist).")

# Remove the default static file serving, Next.js will handle the frontend
# @app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
# def serve(path):
#     # ... (removed default static serving logic)

if __name__ == '__main__':
    # Use environment variable for port, default to 5001 to avoid conflict with Next.js dev server (often 3000)
    port = int(os.getenv('PORT', 5001))
    # Listen on 0.0.0.0 to be accessible externally
    app.run(host='0.0.0.0', port=port, debug=True)

