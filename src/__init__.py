# src/__init__.py
"""
AI Engineer Demo - Data Intelligence Pipeline
"""

# Expose main components for easier imports
from src.config import Config
from src.crawlers import PaperCrawler, StartupCrawler, NewsCrawler
from src.resolvers.entity_resolver import EntityResolver
from src.storage.output_generator import OutputGenerator

__version__ = "1.0.0"
__all__ = [
    'Config',
    'PaperCrawler',
    'StartupCrawler',
    'NewsCrawler',
    'EntityResolver',
    'OutputGenerator'
]