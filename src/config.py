import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management for GitHub PR Reviewer"""
    
    # GitHub Configuration
    GITHUB_TOKEN: Optional[str] = os.getenv('GITHUB_TOKEN')
    GITHUB_WEBHOOK_SECRET: Optional[str] = os.getenv('GITHUB_WEBHOOK_SECRET')
    
    # AI Model Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv('GEMINI_API_KEY')
    PERPLEXITY_API_KEY: Optional[str] = os.getenv('PERPLEXITY_API_KEY')
    
    # Default AI Model (gemini or perplexity)
    DEFAULT_AI_MODEL: str = os.getenv('DEFAULT_AI_MODEL', 'gemini')
    
    # Polling Configuration
    POLLING_INTERVAL: int = int(os.getenv('POLLING_INTERVAL', '300'))  # 5 minutes default
    ENABLE_POLLING: bool = os.getenv('ENABLE_POLLING', 'false').lower() == 'true'
    
    # Repository Configuration
    MONITORED_REPOS: list = os.getenv('MONITORED_REPOS', '').split(',') if os.getenv('MONITORED_REPOS') else []
    
    # Flask Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    
    @classmethod
    def validate_config(cls) -> dict:
        """Validate configuration and return status"""
        errors = []
        warnings = []
        
        if not cls.GITHUB_TOKEN:
            errors.append("GITHUB_TOKEN is required")
        
        if not cls.GEMINI_API_KEY and not cls.PERPLEXITY_API_KEY:
            errors.append("At least one AI API key (GEMINI_API_KEY or PERPLEXITY_API_KEY) is required")
        
        if cls.DEFAULT_AI_MODEL not in ['gemini', 'perplexity']:
            warnings.append("DEFAULT_AI_MODEL should be 'gemini' or 'perplexity'")
        
        if cls.DEFAULT_AI_MODEL == 'gemini' and not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required when DEFAULT_AI_MODEL is 'gemini'")
        
        if cls.DEFAULT_AI_MODEL == 'perplexity' and not cls.PERPLEXITY_API_KEY:
            errors.append("PERPLEXITY_API_KEY is required when DEFAULT_AI_MODEL is 'perplexity'")
        
        if not cls.MONITORED_REPOS and cls.ENABLE_POLLING:
            warnings.append("MONITORED_REPOS should be specified when polling is enabled")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @classmethod
    def get_available_models(cls) -> list:
        """Get list of available AI models based on API keys"""
        models = []
        if cls.GEMINI_API_KEY:
            models.append('gemini')
        if cls.PERPLEXITY_API_KEY:
            models.append('perplexity')
        return models

