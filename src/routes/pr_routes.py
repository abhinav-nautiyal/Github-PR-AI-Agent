import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.pr_reviewer import PRReviewer
from src.webhook_handler import EventManager
from src.config import Config

logger = logging.getLogger(__name__)

# Create blueprint
pr_bp = Blueprint('pr_reviewer', __name__)

# Initialize components
event_manager = EventManager()
pr_reviewer = PRReviewer()

@pr_bp.route('/webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events"""
    try:
        result = event_manager.webhook_handler.handle_webhook()
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/review', methods=['POST'])
def review_pr():
    """Manually trigger PR review"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        repo_name = data.get('repo_name')
        pr_number = data.get('pr_number')
        model_name = data.get('model_name')
        force_review = data.get('force_review', False)
        
        if not repo_name or not pr_number:
            return jsonify({'error': 'repo_name and pr_number are required'}), 400
        
        result = pr_reviewer.review_pull_request(
            repo_name=repo_name,
            pr_number=pr_number,
            model_name=model_name,
            force_review=force_review
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Review error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/review/recent', methods=['POST'])
def review_recent_prs():
    """Review recent PRs in a repository"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        repo_name = data.get('repo_name')
        limit = data.get('limit', 5)
        model_name = data.get('model_name')
        
        if not repo_name:
            return jsonify({'error': 'repo_name is required'}), 400
        
        results = pr_reviewer.review_recent_prs(
            repo_name=repo_name,
            limit=limit,
            model_name=model_name
        )
        
        return jsonify({
            'repo_name': repo_name,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Recent review error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/status/<repo_name>/<int:pr_number>', methods=['GET'])
def get_pr_status(repo_name, pr_number):
    """Get PR review status"""
    try:
        status = pr_reviewer.get_review_status(repo_name, pr_number)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/models', methods=['GET'])
def get_available_models():
    """Get available AI models"""
    try:
        models = pr_reviewer.get_available_models()
        return jsonify({
            'available_models': models,
            'default_model': Config.DEFAULT_AI_MODEL
        })
    except Exception as e:
        logger.error(f"Models error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/config', methods=['GET'])
def get_config():
    """Get configuration status"""
    try:
        validation = Config.validate_config()
        return jsonify({
            'valid': validation['valid'],
            'errors': validation['errors'],
            'warnings': validation['warnings'],
            'available_models': Config.get_available_models(),
            'default_model': Config.DEFAULT_AI_MODEL,
            'polling_enabled': Config.ENABLE_POLLING,
            'monitored_repos': Config.MONITORED_REPOS
        })
    except Exception as e:
        logger.error(f"Config error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/config', methods=['POST'])
def update_config():
    """Update configuration (runtime only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        # Update runtime configuration
        updated_fields = []
        
        if 'default_model' in data:
            Config.DEFAULT_AI_MODEL = data['default_model']
            updated_fields.append('default_model')
        
        if 'polling_enabled' in data:
            Config.ENABLE_POLLING = data['polling_enabled']
            updated_fields.append('polling_enabled')
        
        if 'monitored_repos' in data:
            Config.MONITORED_REPOS = data['monitored_repos']
            updated_fields.append('monitored_repos')
        
        return jsonify({
            'message': 'Configuration updated',
            'updated_fields': updated_fields
        })
        
    except Exception as e:
        logger.error(f"Config update error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/polling/status', methods=['GET'])
def get_polling_status():
    """Get polling status"""
    try:
        status = event_manager.polling_manager.get_polling_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Polling status error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/polling/start', methods=['POST'])
def start_polling():
    """Start polling"""
    try:
        event_manager.polling_manager.start_polling()
        return jsonify({'message': 'Polling started'})
    except Exception as e:
        logger.error(f"Start polling error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/polling/stop', methods=['POST'])
def stop_polling():
    """Stop polling"""
    try:
        event_manager.polling_manager.stop_polling_process()
        return jsonify({'message': 'Polling stopped'})
    except Exception as e:
        logger.error(f"Stop polling error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/polling/repos', methods=['POST'])
def manage_monitored_repos():
    """Add or remove monitored repositories"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        action = data.get('action')  # 'add' or 'remove'
        repo_name = data.get('repo_name')
        
        if not action or not repo_name:
            return jsonify({'error': 'action and repo_name are required'}), 400
        
        if action == 'add':
            event_manager.polling_manager.add_repository(repo_name)
            message = f'Repository {repo_name} added to monitoring'
        elif action == 'remove':
            event_manager.polling_manager.remove_repository(repo_name)
            message = f'Repository {repo_name} removed from monitoring'
        else:
            return jsonify({'error': 'action must be "add" or "remove"'}), 400
        
        return jsonify({
            'message': message,
            'monitored_repos': event_manager.polling_manager.monitored_repos
        })
        
    except Exception as e:
        logger.error(f"Manage repos error: {e}")
        return jsonify({'error': str(e)}), 500

@pr_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        status = event_manager.get_status()
        validation = Config.validate_config()
        
        return jsonify({
            'status': 'healthy' if validation['valid'] else 'unhealthy',
            'timestamp': str(datetime.now()),
            'config_valid': validation['valid'],
            'config_errors': validation['errors'],
            'system_status': status
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Initialize event manager when blueprint is registered
def init_event_manager():
    """Initialize the event manager"""
    event_manager.start()

# Add this to be called when the app starts
pr_bp.record_once(lambda state: init_event_manager())

