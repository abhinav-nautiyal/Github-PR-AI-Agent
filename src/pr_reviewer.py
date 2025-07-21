import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.github_client import GitHubClient
from src.ai_clients import AIModelManager
from src.config import Config

logger = logging.getLogger(__name__)

class PRReviewer:
    """Main class for reviewing pull requests"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_client = GitHubClient(github_token)
        self.ai_manager = AIModelManager()
        
    def review_pull_request(self, repo_name: str, pr_number: int, 
                          model_name: Optional[str] = None, 
                          force_review: bool = False) -> Dict:
        """
        Review a pull request and post comments
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            model_name: AI model to use (optional)
            force_review: Force review even if already reviewed
            
        Returns:
            Dict with review results
        """
        try:
            logger.info(f"Starting review for PR #{pr_number} in {repo_name}")
            
            # Check if already reviewed (unless forced)
            if not force_review and self.github_client.check_pr_reviewed_by_bot(repo_name, pr_number):
                logger.info(f"PR #{pr_number} already reviewed by bot")
                return {
                    'success': True,
                    'message': 'PR already reviewed',
                    'skipped': True
                }
            
            # Get PR details
            pr_data = self.github_client.get_pr_details(repo_name, pr_number)
            logger.info(f"Retrieved PR details: {pr_data['title']}")
            
            # Skip draft PRs unless forced
            if pr_data['draft'] and not force_review:
                logger.info(f"Skipping draft PR #{pr_number}")
                return {
                    'success': True,
                    'message': 'Skipped draft PR',
                    'skipped': True
                }
            
            # Get changed files and diffs
            files_data = self.github_client.get_pr_files_and_diffs(repo_name, pr_number)
            logger.info(f"Retrieved {len(files_data)} changed files")
            
            # Filter files for review (skip certain file types)
            reviewable_files = self._filter_reviewable_files(files_data)
            
            if not reviewable_files:
                logger.info(f"No reviewable files found in PR #{pr_number}")
                return {
                    'success': True,
                    'message': 'No reviewable files found',
                    'skipped': True
                }
            
            # Generate AI review
            logger.info(f"Generating AI review using model: {model_name or Config.DEFAULT_AI_MODEL}")
            review_content = self.ai_manager.generate_review(pr_data, reviewable_files, model_name)
            
            # Add metadata to review
            review_with_metadata = self._add_review_metadata(review_content, model_name)
            
            # Post review comment
            success = self.github_client.post_pr_comment(repo_name, pr_number, review_with_metadata)
            
            if success:
                logger.info(f"Successfully posted review for PR #{pr_number}")
                return {
                    'success': True,
                    'message': 'Review posted successfully',
                    'review_content': review_content,
                    'files_reviewed': len(reviewable_files)
                }
            else:
                logger.error(f"Failed to post review for PR #{pr_number}")
                return {
                    'success': False,
                    'message': 'Failed to post review',
                    'error': 'GitHub API error'
                }
                
        except Exception as e:
            logger.error(f"Error reviewing PR #{pr_number} in {repo_name}: {e}")
            return {
                'success': False,
                'message': f'Review failed: {str(e)}',
                'error': str(e)
            }
    
    def _filter_reviewable_files(self, files_data: List[Dict]) -> List[Dict]:
        """Filter files that should be reviewed"""
        # File extensions to review
        reviewable_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.sql', '.html', '.css', '.scss', '.less', '.vue', '.svelte'
        }
        
        # File patterns to skip
        skip_patterns = {
            'package-lock.json', 'yarn.lock', 'Pipfile.lock', 'poetry.lock',
            '.min.js', '.min.css', 'bundle.js', 'dist/', 'build/', 'node_modules/',
            '.git/', '__pycache__/', '.pyc', '.class', '.jar', '.war'
        }
        
        reviewable_files = []
        
        for file_data in files_data:
            filename = file_data['filename']
            
            # Skip deleted files
            if file_data['status'] == 'removed':
                continue
            
            # Skip files without patches (binary files, etc.)
            if not file_data['patch']:
                continue
            
            # Skip files matching skip patterns
            if any(pattern in filename for pattern in skip_patterns):
                continue
            
            # Check file extension
            file_ext = '.' + filename.split('.')[-1] if '.' in filename else ''
            if file_ext.lower() in reviewable_extensions:
                reviewable_files.append(file_data)
            
            # Also include files without extensions that might be scripts
            elif '.' not in filename.split('/')[-1]:
                # Check if it might be a script by looking at the patch
                patch = file_data['patch']
                if any(indicator in patch for indicator in ['#!/', 'import ', 'from ', 'function ', 'class ']):
                    reviewable_files.append(file_data)
        
        return reviewable_files
    
    def _add_review_metadata(self, review_content: str, model_name: Optional[str]) -> str:
        """Add metadata to the review content"""
        model_used = model_name or Config.DEFAULT_AI_MODEL
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        metadata = f"""
---
*🤖 This review was generated by AI using the {model_used} model on {timestamp}*
*This is an automated code review. Please use your judgment and consider the suggestions carefully.*

"""
        
        return metadata + review_content
    
    def review_recent_prs(self, repo_name: str, limit: int = 5, 
                         model_name: Optional[str] = None) -> List[Dict]:
        """Review recent PRs in a repository"""
        try:
            logger.info(f"Reviewing recent PRs in {repo_name}")
            
            # Get recent PRs
            recent_prs = self.github_client.get_recent_prs(repo_name, limit=limit)
            
            results = []
            for pr_data in recent_prs:
                result = self.review_pull_request(
                    repo_name, 
                    pr_data['number'], 
                    model_name=model_name
                )
                result['pr_title'] = pr_data['title']
                result['pr_number'] = pr_data['number']
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error reviewing recent PRs in {repo_name}: {e}")
            return [{'success': False, 'error': str(e)}]
    
    def get_review_status(self, repo_name: str, pr_number: int) -> Dict:
        """Get the review status of a PR"""
        try:
            pr_data = self.github_client.get_pr_details(repo_name, pr_number)
            already_reviewed = self.github_client.check_pr_reviewed_by_bot(repo_name, pr_number)
            
            return {
                'pr_number': pr_number,
                'title': pr_data['title'],
                'state': pr_data['state'],
                'draft': pr_data['draft'],
                'already_reviewed': already_reviewed,
                'changed_files': pr_data['changed_files'],
                'additions': pr_data['additions'],
                'deletions': pr_data['deletions']
            }
            
        except Exception as e:
            logger.error(f"Error getting review status for PR #{pr_number}: {e}")
            return {'error': str(e)}
    
    def get_available_models(self) -> List[str]:
        """Get list of available AI models"""
        return self.ai_manager.get_available_models()

