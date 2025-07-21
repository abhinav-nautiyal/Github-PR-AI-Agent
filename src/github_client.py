import logging
from typing import Dict, List, Optional, Tuple
from github import Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.PullRequestComment import PullRequestComment
from src.config import Config

logger = logging.getLogger(__name__)

class GitHubClient:
    """GitHub API client for PR operations"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or Config.GITHUB_TOKEN
        if not self.token:
            raise ValueError("GitHub token is required")
        
        self.github = Github(self.token)
        self._validate_token()
    
    def _validate_token(self):
        """Validate GitHub token"""
        try:
            user = self.github.get_user()
            logger.info(f"GitHub client initialized for user: {user.login}")
        except GithubException as e:
            logger.error(f"Invalid GitHub token: {e}")
            raise ValueError("Invalid GitHub token")
    
    def get_repository(self, repo_name: str) -> Repository:
        """Get repository object"""
        try:
            return self.github.get_repo(repo_name)
        except GithubException as e:
            logger.error(f"Error accessing repository {repo_name}: {e}")
            raise
    
    def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get pull request object"""
        try:
            repo = self.get_repository(repo_name)
            return repo.get_pull(pr_number)
        except GithubException as e:
            logger.error(f"Error accessing PR #{pr_number} in {repo_name}: {e}")
            raise
    
    def get_pr_files_and_diffs(self, repo_name: str, pr_number: int) -> List[Dict]:
        """Get changed files and their diffs from a PR"""
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            files_data = []
            
            for file in pr.get_files():
                file_data = {
                    'filename': file.filename,
                    'status': file.status,  # added, modified, removed, renamed
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                    'patch': file.patch if hasattr(file, 'patch') and file.patch else '',
                    'blob_url': file.blob_url,
                    'raw_url': file.raw_url
                }
                files_data.append(file_data)
            
            return files_data
        except GithubException as e:
            logger.error(f"Error getting PR files for #{pr_number} in {repo_name}: {e}")
            raise
    
    def get_pr_details(self, repo_name: str, pr_number: int) -> Dict:
        """Get comprehensive PR details"""
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            
            return {
                'number': pr.number,
                'title': pr.title,
                'body': pr.body or '',
                'state': pr.state,
                'author': pr.user.login,
                'created_at': pr.created_at.isoformat(),
                'updated_at': pr.updated_at.isoformat(),
                'base_branch': pr.base.ref,
                'head_branch': pr.head.ref,
                'base_sha': pr.base.sha,
                'head_sha': pr.head.sha,
                'mergeable': pr.mergeable,
                'draft': pr.draft,
                'url': pr.html_url,
                'commits_count': pr.commits,
                'additions': pr.additions,
                'deletions': pr.deletions,
                'changed_files': pr.changed_files
            }
        except GithubException as e:
            logger.error(f"Error getting PR details for #{pr_number} in {repo_name}: {e}")
            raise
    
    def post_pr_comment(self, repo_name: str, pr_number: int, comment: str) -> bool:
        """Post a comment on a PR"""
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            pr.create_issue_comment(comment)
            logger.info(f"Posted comment on PR #{pr_number} in {repo_name}")
            return True
        except GithubException as e:
            logger.error(f"Error posting comment on PR #{pr_number} in {repo_name}: {e}")
            return False
    
    def post_pr_review(self, repo_name: str, pr_number: int, body: str, 
                      event: str = "COMMENT", comments: Optional[List[Dict]] = None) -> bool:
        """Post a review on a PR with optional line comments"""
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            
            review_comments = []
            if comments:
                for comment in comments:
                    review_comment = {
                        'path': comment['path'],
                        'line': comment['line'],
                        'body': comment['body']
                    }
                    if 'side' in comment:
                        review_comment['side'] = comment['side']
                    review_comments.append(review_comment)
            
            pr.create_review(
                body=body,
                event=event,  # APPROVE, REQUEST_CHANGES, or COMMENT
                comments=review_comments if review_comments else None
            )
            
            logger.info(f"Posted review on PR #{pr_number} in {repo_name}")
            return True
        except GithubException as e:
            logger.error(f"Error posting review on PR #{pr_number} in {repo_name}: {e}")
            return False
    
    def get_recent_prs(self, repo_name: str, state: str = "open", limit: int = 10) -> List[Dict]:
        """Get recent PRs from a repository"""
        try:
            repo = self.get_repository(repo_name)
            prs = repo.get_pulls(state=state, sort="updated", direction="desc")
            
            pr_list = []
            for pr in prs[:limit]:
                pr_data = {
                    'number': pr.number,
                    'title': pr.title,
                    'author': pr.user.login,
                    'created_at': pr.created_at.isoformat(),
                    'updated_at': pr.updated_at.isoformat(),
                    'state': pr.state,
                    'draft': pr.draft,
                    'url': pr.html_url
                }
                pr_list.append(pr_data)
            
            return pr_list
        except GithubException as e:
            logger.error(f"Error getting recent PRs for {repo_name}: {e}")
            raise
    
    def check_pr_reviewed_by_bot(self, repo_name: str, pr_number: int, bot_name: str = None) -> bool:
        """Check if PR has already been reviewed by the bot"""
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            bot_name = bot_name or self.github.get_user().login
            
            # Check issue comments
            for comment in pr.get_issue_comments():
                if comment.user.login == bot_name and "AI Code Review" in comment.body:
                    return True
            
            # Check review comments
            for review in pr.get_reviews():
                if review.user.login == bot_name:
                    return True
            
            return False
        except GithubException as e:
            logger.error(f"Error checking if PR #{pr_number} was reviewed: {e}")
            return False

