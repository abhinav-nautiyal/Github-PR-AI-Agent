import os
import sys
import logging
from datetime import datetime

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.pr_routes import pr_bp
from src.routes.agent_routes import agent_bp
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pr_reviewer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Correctly configure the static folder. Flask will handle the /static route automatically.
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(pr_bp, url_prefix='/api/pr')
# The agent_bp routes start with /api/agent, so we register it without a prefix
app.register_blueprint(agent_bp, url_prefix='/api')


# Database configuration (optional for this project)
# Ensure the 'database' directory exists
db_dir = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(db_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(db_dir, 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Main index route, returns API info"""
    return jsonify({
        'name': 'GitHub PR Reviewer',
        'version': '1.0.0',
        'description': 'AI-powered GitHub Pull Request reviewer with Gemini and Perplexity support',
        'endpoints': {
            'webhook': '/api/pr/webhook',
            'review': '/api/pr/review',
            'agent_ui': '/static/agent.html',
            'agent_files': '/api/agent/files',
        },
        'timestamp': datetime.now().isoformat()
    })

# The problematic custom serve route has been REMOVED.
# Flask's built-in static file handling is now active and will correctly serve
# files from the 'src/static' directory under the '/static/' URL path.

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Validate configuration on startup
    validation = Config.validate_config()
    if not validation['valid']:
        logger.error("Configuration validation failed:")
        for error in validation['errors']:
            logger.error(f"  - {error}")
        logger.info("Please check your environment variables and try again.")
    else:
        logger.info("Configuration validation passed")
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"  - {warning}")
    
    logger.info("Starting GitHub PR Reviewer server...")
    app.run(host='0.0.0.0', port=5001, debug=Config.DEBUG)
