import logging
import hmac
import hashlib
import json
import threading
import time
import schedule
from typing import Dict, Optional
from flask import request, jsonify
from src.pr_reviewer import PRReviewer
from src.config import Config

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handle GitHub webhooks for PR events"""
    
    def __init__(self, pr_reviewer: PRReviewer):
        self.pr_reviewer = pr_reviewer
        self.webhook_secret = Config.GITHUB_WEBHOOK_SECRET
    
    def verify_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """Verify GitHub webhook signature"""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping signature verification")
            return True
        
        if not signature_header:
            return False
        
        hash_object = hmac.new(
            self.webhook_secret.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        return hmac.compare_digest(expected_signature, signature_header)
    
    def handle_webhook(self) -> Dict:
        """Handle incoming GitHub webhook"""
        try:
            # Get signature for verification
            signature = request.headers.get('X-Hub-Signature-256')
            
            # Get payload
            payload_body = request.get_data()
            
            # Verify signature
            if not self.verify_signature(payload_body, signature):
                logger.warning("Invalid webhook signature")
                return {'error': 'Invalid signature'}, 401
            
            # Parse payload
            try:
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error("Invalid JSON payload")
                return {'error': 'Invalid JSON'}, 400
            
            # Get event type
            event_type = request.headers.get('X-GitHub-Event')
            
            if event_type == 'pull_request':
                return self._handle_pull_request_event(payload)
            elif event_type == 'pull_request_review':
                return self._handle_pull_request_review_event(payload)
            elif event_type == 'ping':
                return {'message': 'Webhook received successfully'}
            else:
                logger.info(f"Ignoring event type: {event_type}")
                return {'message': f'Event type {event_type} ignored'}
        
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {'error': str(e)}, 500
    
    def _handle_pull_request_event(self, payload: Dict) -> Dict:
        """Handle pull request events"""
        action = payload.get('action')
        pr = payload.get('pull_request', {})
        repository = payload.get('repository', {})
        
        repo_name = repository.get('full_name')
        pr_number = pr.get('number')
        
        logger.info(f"Received PR event: {action} for PR #{pr_number} in {repo_name}")
        
        # Only review on opened, reopened, or synchronize (new commits)
        if action in ['opened', 'reopened', 'synchronize']:
            try:
                # Review the PR
                result = self.pr_reviewer.review_pull_request(
                    repo_name=repo_name,
                    pr_number=pr_number,
                    force_review=(action == 'synchronize')  # Force review on new commits
                )
                
                return {
                    'message': f'PR #{pr_number} processed',
                    'action': action,
                    'result': result
                }
                
            except Exception as e:
                logger.error(f"Error reviewing PR #{pr_number}: {e}")
                return {
                    'error': f'Failed to review PR #{pr_number}: {str(e)}'
                }, 500
        
        return {
            'message': f'PR action {action} ignored'
        }
    
    def _handle_pull_request_review_event(self, payload: Dict) -> Dict:
        """Handle pull request review events"""
        action = payload.get('action')
        logger.info(f"Received PR review event: {action}")
        
        # For now, we just log these events
        # Could be extended to handle review responses
        return {
            'message': f'PR review action {action} received'
        }

class PollingManager:
    """Manage polling for PR updates"""
    
    def __init__(self, pr_reviewer: PRReviewer):
        self.pr_reviewer = pr_reviewer
        self.polling_thread = None
        self.stop_polling = False
        self.monitored_repos = Config.MONITORED_REPOS
        self.polling_interval = Config.POLLING_INTERVAL
        
    def start_polling(self):
        """Start the polling process"""
        if not Config.ENABLE_POLLING:
            logger.info("Polling is disabled")
            return
        
        if not self.monitored_repos:
            logger.warning("No repositories configured for polling")
            return
        
        logger.info(f"Starting polling for repositories: {self.monitored_repos}")
        logger.info(f"Polling interval: {self.polling_interval} seconds")
        
        # Schedule polling job
        schedule.every(self.polling_interval).seconds.do(self._poll_repositories)
        
        # Start polling thread
        self.stop_polling = False
        self.polling_thread = threading.Thread(target=self._run_polling, daemon=True)
        self.polling_thread.start()
        
        logger.info("Polling started successfully")
    
    def stop_polling_process(self):
        """Stop the polling process"""
        logger.info("Stopping polling process")
        self.stop_polling = True
        schedule.clear()
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
    
    def _run_polling(self):
        """Run the polling loop"""
        while not self.stop_polling:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _poll_repositories(self):
        """Poll repositories for new PRs"""
        logger.info("Polling repositories for new PRs")
        
        for repo_name in self.monitored_repos:
            if self.stop_polling:
                break
                
            try:
                logger.info(f"Polling repository: {repo_name}")
                
                # Review recent PRs (limit to 3 to avoid rate limiting)
                results = self.pr_reviewer.review_recent_prs(
                    repo_name=repo_name,
                    limit=3
                )
                
                # Log results
                for result in results:
                    if result.get('success'):
                        if result.get('skipped'):
                            logger.info(f"PR #{result.get('pr_number')} skipped: {result.get('message')}")
                        else:
                            logger.info(f"PR #{result.get('pr_number')} reviewed successfully")
                    else:
                        logger.error(f"Failed to review PR: {result.get('error')}")
                
                # Small delay between repositories
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error polling repository {repo_name}: {e}")
    
    def get_polling_status(self) -> Dict:
        """Get current polling status"""
        return {
            'enabled': Config.ENABLE_POLLING,
            'running': self.polling_thread is not None and self.polling_thread.is_alive(),
            'interval': self.polling_interval,
            'monitored_repos': self.monitored_repos,
            'next_run': schedule.next_run().isoformat() if schedule.jobs else None
        }
    
    def add_repository(self, repo_name: str):
        """Add a repository to monitoring"""
        if repo_name not in self.monitored_repos:
            self.monitored_repos.append(repo_name)
            logger.info(f"Added repository to monitoring: {repo_name}")
    
    def remove_repository(self, repo_name: str):
        """Remove a repository from monitoring"""
        if repo_name in self.monitored_repos:
            self.monitored_repos.remove(repo_name)
            logger.info(f"Removed repository from monitoring: {repo_name}")

class EventManager:
    """Manage both webhook and polling events"""
    
    def __init__(self):
        self.pr_reviewer = PRReviewer()
        self.webhook_handler = WebhookHandler(self.pr_reviewer)
        self.polling_manager = PollingManager(self.pr_reviewer)
    
    def start(self):
        """Start event management"""
        logger.info("Starting event manager")
        
        # Start polling if enabled
        self.polling_manager.start_polling()
        
        logger.info("Event manager started")
    
    def stop(self):
        """Stop event management"""
        logger.info("Stopping event manager")
        self.polling_manager.stop_polling_process()
        logger.info("Event manager stopped")
    
    def get_status(self) -> Dict:
        """Get overall status"""
        return {
            'webhook': {
                'configured': bool(Config.GITHUB_WEBHOOK_SECRET),
                'endpoint': '/webhook'
            },
            'polling': self.polling_manager.get_polling_status(),
            'ai_models': self.pr_reviewer.get_available_models()
        }

