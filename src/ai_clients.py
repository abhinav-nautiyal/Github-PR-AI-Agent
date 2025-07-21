import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import google.generativeai as genai
import requests
from src.config import Config

logger = logging.getLogger(__name__)

class AIClient(ABC):
    """Abstract base class for AI clients"""
    
    @abstractmethod
    def generate_review(self, pr_data: Dict, files_data: List[Dict]) -> str:
        """Generate a code review for the given PR and files"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the AI client is properly configured and available"""
        pass

class GeminiClient(AIClient):
    """Google Gemini AI client for code review"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
    def is_available(self) -> bool:
        """Check if Gemini client is available"""
        try:
            # Test with a simple prompt
            response = self.model.generate_content("Hello")
            return True
        except Exception as e:
            logger.error(f"Gemini client not available: {e}")
            return False
    
    def generate_review(self, pr_data: Dict, files_data: List[Dict]) -> str:
        """Generate code review using Gemini"""
        try:
            prompt = self._build_review_prompt(pr_data, files_data)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating review with Gemini: {e}")
            raise
    
    def _build_review_prompt(self, pr_data: Dict, files_data: List[Dict]) -> str:
        """Build the prompt for code review"""
        prompt = f"""
You are an expert code reviewer. Please review the following pull request and provide constructive feedback.

**Pull Request Details:**
- Title: {pr_data['title']}
- Description: {pr_data['body']}
- Author: {pr_data['author']}
- Base Branch: {pr_data['base_branch']}
- Head Branch: {pr_data['head_branch']}
- Files Changed: {pr_data['changed_files']}
- Additions: {pr_data['additions']}
- Deletions: {pr_data['deletions']}

**Changed Files and Diffs:**
"""
        
        for file_data in files_data:
            prompt += f"""
**File: {file_data['filename']}**
- Status: {file_data['status']}
- Additions: {file_data['additions']}
- Deletions: {file_data['deletions']}

```diff
{file_data['patch'][:2000]}  # Limit patch size
```
"""
        
        prompt += """

Please provide a comprehensive code review covering:
1. **Code Quality**: Check for best practices, code style, and maintainability
2. **Security**: Identify potential security vulnerabilities
3. **Performance**: Suggest performance improvements if applicable
4. **Logic**: Review the logic and algorithm correctness
5. **Testing**: Comment on test coverage and quality
6. **Documentation**: Check if code is well-documented

Format your response as follows:
## 🤖 AI Code Review

### Summary
[Brief summary of the changes and overall assessment]

### Positive Aspects
[What's good about this PR]

### Issues and Suggestions
[Detailed feedback with specific line references when possible]

### Security Considerations
[Any security-related observations]

### Performance Notes
[Performance-related feedback]

### Recommendations
[Final recommendations for the PR]

Be constructive, specific, and helpful in your feedback.
"""
        return prompt

class PerplexityClient(AIClient):
    """Perplexity AI client for code review"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.PERPLEXITY_API_KEY
        if not self.api_key:
            raise ValueError("Perplexity API key is required")
        
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def is_available(self) -> bool:
        """Check if Perplexity client is available"""
        try:
            # Test with a simple request
            test_payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            response = requests.post(self.base_url, headers=self.headers, json=test_payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Perplexity client not available: {e}")
            return False
    
    def generate_review(self, pr_data: Dict, files_data: List[Dict]) -> str:
        """Generate code review using Perplexity"""
        try:
            prompt = self._build_review_prompt(pr_data, files_data)
            
            payload = {
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer with deep knowledge of software engineering best practices, security, and performance optimization."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.2,
                "top_p": 0.9
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error generating review with Perplexity: {e}")
            raise
    
    def _build_review_prompt(self, pr_data: Dict, files_data: List[Dict]) -> str:
        """Build the prompt for code review"""
        prompt = f"""
Please review the following pull request and provide constructive, expert-level feedback.

**Pull Request Information:**
- Title: {pr_data['title']}
- Description: {pr_data['body']}
- Author: {pr_data['author']}
- Base Branch: {pr_data['base_branch']}
- Head Branch: {pr_data['head_branch']}
- Files Changed: {pr_data['changed_files']}
- Lines Added: {pr_data['additions']}
- Lines Deleted: {pr_data['deletions']}

**File Changes:**
"""
        
        for file_data in files_data:
            prompt += f"""
**{file_data['filename']}** ({file_data['status']})
- +{file_data['additions']} -{file_data['deletions']} lines

```diff
{file_data['patch'][:2000]}  # Truncated for length
```
"""
        
        prompt += """

Provide a comprehensive code review covering:
1. Code quality and best practices
2. Security vulnerabilities
3. Performance considerations
4. Logic and correctness
5. Testing adequacy
6. Documentation quality

Format your response as:
## 🤖 AI Code Review

### Overview
[Brief assessment of the changes]

### Strengths
[Positive aspects of the PR]

### Areas for Improvement
[Specific issues and suggestions]

### Security Analysis
[Security-related findings]

### Performance Impact
[Performance considerations]

### Final Verdict
[Overall recommendation]

Be specific, actionable, and constructive in your feedback.
"""
        return prompt

class AIModelManager:
    """Manager for switching between different AI models"""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available AI clients"""
        try:
            if Config.GEMINI_API_KEY:
                self.clients['gemini'] = GeminiClient()
                logger.info("Gemini client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")
        
        try:
            if Config.PERPLEXITY_API_KEY:
                self.clients['perplexity'] = PerplexityClient()
                logger.info("Perplexity client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Perplexity client: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available AI models"""
        available = []
        for name, client in self.clients.items():
            if client.is_available():
                available.append(name)
        return available
    
    def get_client(self, model_name: Optional[str] = None) -> AIClient:
        """Get AI client by name or default"""
        if not model_name:
            model_name = Config.DEFAULT_AI_MODEL
        
        if model_name not in self.clients:
            available = list(self.clients.keys())
            raise ValueError(f"Model '{model_name}' not available. Available models: {available}")
        
        client = self.clients[model_name]
        if not client.is_available():
            raise ValueError(f"Model '{model_name}' is not currently available")
        
        return client
    
    def generate_review(self, pr_data: Dict, files_data: List[Dict], 
                       model_name: Optional[str] = None) -> str:
        """Generate review using specified or default model"""
        client = self.get_client(model_name)
        return client.generate_review(pr_data, files_data)

