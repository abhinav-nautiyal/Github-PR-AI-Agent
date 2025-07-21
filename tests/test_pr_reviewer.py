import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config
from src.github_client import GitHubClient
from src.ai_clients import AIModelManager, GeminiClient, PerplexityClient
from src.pr_reviewer import PRReviewer

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        # Store original values
        self.original_github_token = os.environ.get('GITHUB_TOKEN')
        self.original_gemini_key = os.environ.get('GEMINI_API_KEY')
        
    def tearDown(self):
        # Restore original values
        if self.original_github_token:
            os.environ['GITHUB_TOKEN'] = self.original_github_token
        elif 'GITHUB_TOKEN' in os.environ:
            del os.environ['GITHUB_TOKEN']
            
        if self.original_gemini_key:
            os.environ['GEMINI_API_KEY'] = self.original_gemini_key
        elif 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
    
    def test_config_validation_missing_github_token(self):
        """Test config validation with missing GitHub token"""
        if 'GITHUB_TOKEN' in os.environ:
            del os.environ['GITHUB_TOKEN']
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        if 'PERPLEXITY_API_KEY' in os.environ:
            del os.environ['PERPLEXITY_API_KEY']
            
        # Reload config
        Config.GITHUB_TOKEN = None
        Config.GEMINI_API_KEY = None
        Config.PERPLEXITY_API_KEY = None
        
        validation = Config.validate_config()
        self.assertFalse(validation['valid'])
        self.assertIn('GITHUB_TOKEN is required', validation['errors'])
    
    def test_config_validation_valid(self):
        """Test config validation with valid configuration"""
        os.environ['GITHUB_TOKEN'] = 'test_token'
        os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
        
        # Reload config
        Config.GITHUB_TOKEN = 'test_token'
        Config.GEMINI_API_KEY = 'test_gemini_key'
        Config.DEFAULT_AI_MODEL = 'gemini'
        
        validation = Config.validate_config()
        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['errors']), 0)

class TestGitHubClient(unittest.TestCase):
    """Test GitHub client functionality"""
    
    @patch('src.github_client.Github')
    def test_github_client_initialization(self, mock_github):
        """Test GitHub client initialization"""
        mock_user = Mock()
        mock_user.login = 'testuser'
        mock_github.return_value.get_user.return_value = mock_user
        
        client = GitHubClient('test_token')
        self.assertEqual(client.token, 'test_token')
        mock_github.assert_called_once_with('test_token')
    
    @patch('src.github_client.Github')
    def test_get_pr_details(self, mock_github):
        """Test getting PR details"""
        # Mock GitHub objects
        mock_user = Mock()
        mock_user.login = 'testuser'
        mock_github.return_value.get_user.return_value = mock_user
        
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = 'Test PR'
        mock_pr.body = 'Test description'
        mock_pr.state = 'open'
        mock_pr.user.login = 'author'
        mock_pr.created_at.isoformat.return_value = '2023-01-01T00:00:00'
        mock_pr.updated_at.isoformat.return_value = '2023-01-01T00:00:00'
        mock_pr.base.ref = 'main'
        mock_pr.head.ref = 'feature'
        mock_pr.base.sha = 'abc123'
        mock_pr.head.sha = 'def456'
        mock_pr.mergeable = True
        mock_pr.draft = False
        mock_pr.html_url = 'https://github.com/test/repo/pull/123'
        mock_pr.commits = 3
        mock_pr.additions = 10
        mock_pr.deletions = 5
        mock_pr.changed_files = 2
        
        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.return_value.get_repo.return_value = mock_repo
        
        client = GitHubClient('test_token')
        pr_details = client.get_pr_details('test/repo', 123)
        
        self.assertEqual(pr_details['number'], 123)
        self.assertEqual(pr_details['title'], 'Test PR')
        self.assertEqual(pr_details['author'], 'author')

class TestAIClients(unittest.TestCase):
    """Test AI client functionality"""
    
    def test_ai_model_manager_initialization(self):
        """Test AI model manager initialization"""
        with patch('src.ai_clients.Config') as mock_config:
            mock_config.GEMINI_API_KEY = 'test_key'
            mock_config.PERPLEXITY_API_KEY = None
            
            with patch('src.ai_clients.GeminiClient') as mock_gemini:
                mock_gemini.return_value.is_available.return_value = True
                
                manager = AIModelManager()
                self.assertIn('gemini', manager.clients)
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_gemini_client_initialization(self, mock_model, mock_configure):
        """Test Gemini client initialization"""
        client = GeminiClient('test_key')
        mock_configure.assert_called_once_with(api_key='test_key')
        mock_model.assert_called_once_with('gemini-pro')
    
    @patch('requests.post')
    def test_perplexity_client_availability(self, mock_post):
        """Test Perplexity client availability check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        client = PerplexityClient('test_key')
        self.assertTrue(client.is_available())

class TestPRReviewer(unittest.TestCase):
    """Test PR reviewer functionality"""
    
    @patch('src.pr_reviewer.GitHubClient')
    @patch('src.pr_reviewer.AIModelManager')
    def test_pr_reviewer_initialization(self, mock_ai_manager, mock_github_client):
        """Test PR reviewer initialization"""
        reviewer = PRReviewer('test_token')
        mock_github_client.assert_called_once_with('test_token')
        mock_ai_manager.assert_called_once()
    
    @patch('src.pr_reviewer.GitHubClient')
    @patch('src.pr_reviewer.AIModelManager')
    def test_filter_reviewable_files(self, mock_ai_manager, mock_github_client):
        """Test filtering of reviewable files"""
        reviewer = PRReviewer('test_token')
        
        files_data = [
            {
                'filename': 'src/main.py',
                'status': 'modified',
                'patch': 'diff content',
                'additions': 5,
                'deletions': 2
            },
            {
                'filename': 'package-lock.json',
                'status': 'modified',
                'patch': 'diff content',
                'additions': 100,
                'deletions': 50
            },
            {
                'filename': 'deleted_file.py',
                'status': 'removed',
                'patch': 'diff content',
                'additions': 0,
                'deletions': 10
            }
        ]
        
        reviewable = reviewer._filter_reviewable_files(files_data)
        
        # Should only include the Python file, not package-lock.json or deleted file
        self.assertEqual(len(reviewable), 1)
        self.assertEqual(reviewable[0]['filename'], 'src/main.py')

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestConfig))
    test_suite.addTest(unittest.makeSuite(TestGitHubClient))
    test_suite.addTest(unittest.makeSuite(TestAIClients))
    test_suite.addTest(unittest.makeSuite(TestPRReviewer))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

