import os
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class Config:

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', 20))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    REQUEST_DELAY_MIN = float(os.getenv('REQUEST_DELAY_MIN', 0.5))
    REQUEST_DELAY_MAX = float(os.getenv('REQUEST_DELAY_MAX', 2.0))
    
    RATE_LIMITS = {
        'arxiv': int(os.getenv('RATE_LIMIT_ARXIV', 3)),
        'github': int(os.getenv('RATE_LIMIT_GITHUB', 60)),
        'yc': int(os.getenv('RATE_LIMIT_YC', 10)),
        'news': int(os.getenv('RATE_LIMIT_NEWS', 20)),
    }
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/ai_engineer.db')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', './data/output'))
    SEED_DATA_DIR = Path(os.getenv('SEED_DATA_DIR', './data/seed'))

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/pipeline.log')

    PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []
    PLAYWRIGHT_HEADLESS = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
    
    @classmethod
    def validate(cls):
        required_keys = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'DEEPSEEK_API_KEY']
        missing = [key for key in required_keys if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        return True

Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Config.SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)