"""
Centralized configuration module for PROpitashka Bot
Loads all settings from environment variables
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Config:
    """Main configuration class"""
    
    # ============================================
    # Telegram Bot Configuration
    # ============================================
    TELEGRAM_TOKEN: str = os.getenv('TOKEN', '')
    
    # ============================================
    # AI Services Configuration (Google Gemini only)
    # ============================================
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    
    # ============================================
    # Database Configuration
    # ============================================
    DB_NAME: str = os.getenv('DB_NAME', 'propitashka')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: str = os.getenv('DB_PORT', '5432')
    DB_SSLMODE: str = os.getenv('DB_SSLMODE', 'prefer')
    DB_SSL_ENABLED: bool = os.getenv('DB_SSL_ENABLED', 'false').lower() == 'true'
    DB_SSL_CERT_PATH: Optional[str] = os.getenv('DB_SSL_CERT_PATH')
    
    # ============================================
    # Redis Configuration (for caching)
    # ============================================
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD: Optional[str] = os.getenv('REDIS_PASSWORD')
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    
    # ============================================
    # Admin Panel Configuration
    # ============================================
    ADMIN_DB_USER: str = os.getenv('ADMIN_DB_USER', 'admin_user')
    ADMIN_DB_PASSWORD: str = os.getenv('ADMIN_DB_PASSWORD', '')
    ADMIN_SECRET_KEY: str = os.getenv('ADMIN_SECRET_KEY', 'change-me-in-production')
    
    # ============================================
    # Application Settings
    # ============================================
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    DEBUG: bool = ENVIRONMENT == 'development'
    
    # ============================================
    # Feature Flags
    # ============================================
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    ANALYTICS_ENABLED: bool = os.getenv('ANALYTICS_ENABLED', 'false').lower() == 'true'
    REFERRAL_ENABLED: bool = os.getenv('REFERRAL_ENABLED', 'false').lower() == 'true'
    
    # ============================================
    # External Services
    # ============================================
    SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')
    
    # ============================================
    # Timeouts and Retries
    # ============================================
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '30'))
    API_RETRY_ATTEMPTS: int = int(os.getenv('API_RETRY_ATTEMPTS', '3'))
    API_RETRY_DELAY: float = float(os.getenv('API_RETRY_DELAY', '1.0'))
    
    DB_TIMEOUT: int = int(os.getenv('DB_TIMEOUT', '10'))
    
    # ============================================
    # Cache Settings
    # ============================================
    CACHE_TTL_FOOD_RECOGNITION: int = int(os.getenv('CACHE_TTL_FOOD_RECOGNITION', '604800'))  # 7 days
    CACHE_TTL_RECIPES: int = int(os.getenv('CACHE_TTL_RECIPES', '86400'))  # 1 day
    CACHE_TTL_AI_RESPONSES: int = int(os.getenv('CACHE_TTL_AI_RESPONSES', '3600'))  # 1 hour
    
    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate required configuration values
        Returns list of missing/invalid configuration keys
        """
        errors = []
        
        # Required fields
        if not cls.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_TOKEN is required")
        

        if not cls.DB_PASSWORD:
            errors.append("DB_PASSWORD is required")
        
        # Validate environment
        if cls.ENVIRONMENT not in ['development', 'staging', 'production']:
            errors.append(f"Invalid ENVIRONMENT: {cls.ENVIRONMENT}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}")
        
        return errors
    
    @classmethod
    def get_db_config(cls, admin: bool = False) -> dict:
        """
        Get database configuration dictionary
        
        Args:
            admin: If True, use admin credentials
        
        Returns:
            Dictionary with database connection parameters
        """
        config = {
            'dbname': cls.DB_NAME,
            'user': cls.ADMIN_DB_USER if admin else cls.DB_USER,
            'password': cls.ADMIN_DB_PASSWORD if admin else cls.DB_PASSWORD,
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
        }
        
        # Add SSL configuration if enabled
        if cls.DB_SSL_ENABLED:
            config['sslmode'] = cls.DB_SSLMODE
            if cls.DB_SSL_CERT_PATH:
                config['sslrootcert'] = cls.DB_SSL_CERT_PATH
        
        return config
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis connection URL"""
        if cls.REDIS_PASSWORD:
            return f"redis://:{cls.REDIS_PASSWORD}@{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def print_config(cls, hide_secrets: bool = True):
        """Print current configuration (for debugging)"""
        print("=" * 60)
        print("PROpitashka Configuration")
        print("=" * 60)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"Debug Mode: {cls.DEBUG}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print()
        print("Features:")
        print(f"  - Caching: {cls.CACHE_ENABLED}")
        print(f"  - Analytics: {cls.ANALYTICS_ENABLED}")
        print(f"  - Referrals: {cls.REFERRAL_ENABLED}")
        print()
        print("Database:")
        print(f"  - Host: {cls.DB_HOST}:{cls.DB_PORT}")
        print(f"  - Database: {cls.DB_NAME}")
        print(f"  - User: {cls.DB_USER}")
        print(f"  - SSL: {cls.DB_SSL_ENABLED}")
        print()
        if not hide_secrets:
            print("Secrets:")
            print(f"  - Telegram Token: {cls.TELEGRAM_TOKEN[:10]}...")
            print(f"  - Gemini API Key: {cls.GEMINI_API_KEY[:10]}...")
        print("=" * 60)


# Create singleton instance
config = Config()

# Validate configuration on import
validation_errors = config.validate()
if validation_errors and config.ENVIRONMENT == 'production':
    raise ValueError(f"Configuration errors: {', '.join(validation_errors)}")
elif validation_errors:
    print(f"⚠️  Configuration warnings: {', '.join(validation_errors)}")

