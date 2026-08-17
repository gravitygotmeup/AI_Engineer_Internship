import asyncio
import random
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import aiohttp
from src.config import Config
from src.utils.anti_bot import AntiBot
from src.utils.logger import setup_logger

setup_logger()

class BaseCrawler(ABC):

    def __init__(self, source_name: str, max_concurrent: Optional[int] = None):
       
        self.source_name = source_name
        self.max_concurrent = max_concurrent or Config.MAX_CONCURRENT_REQUESTS
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
        self.anti_bot = AntiBot()

        self.headers = {
            'User-Agent': self.anti_bot.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        logger.info(f"Initialized {self.__class__.__name__} for {source_name}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
    )
    async def fetch_url(self, url: str, use_playwright: bool = False) -> Optional[str]:
        
        async with self.semaphore:
            await asyncio.sleep(random.uniform(
                Config.REQUEST_DELAY_MIN, 
                Config.REQUEST_DELAY_MAX
            ))
            
            try:
                if use_playwright:
                    content = await self.anti_bot.scrape_with_playwright(url)
                    logger.debug(f"Fetched {url} with Playwright")
                    return content
                else:
                    async with aiohttp.ClientSession(
                        timeout=self.timeout,
                        headers=self.headers
                    ) as session:
                        proxy = random.choice(Config.PROXY_LIST) if Config.PROXY_LIST else None
                        
                        async with session.get(url, proxy=proxy) as response:
                            if response.status == 200:
                                content = await response.text()
                                logger.debug(f"Fetched {url} (status: {response.status})")
                                return content
                            elif response.status == 429:
                                logger.warning(f"Rate limited on {url}")
                                raise aiohttp.ClientError("Rate limited")
                            else:
                                logger.warning(f"Failed to fetch {url}: {response.status}")
                                return None
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url}")
                raise
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                raise
    
    @abstractmethod
    async def fetch(self, limit: int = 1000) -> list:
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> Dict[str, Any]:
        pass
    
    async def run(self, limit: int = 1000) -> list:
        logger.info(f"Starting {self.source_name} crawler (limit: {limit})")
        raw_data = await self.fetch(limit)
        
        if not raw_data:
            logger.warning(f"No data fetched from {self.source_name}")
            return []
        
        parsed_data = []
        for item in raw_data:
            try:
                parsed = self.parse(item)
                if parsed:
                    parsed_data.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing item: {e}")
                continue
        
        logger.info(f"Parsed {len(parsed_data)} records from {self.source_name}")
        return parsed_data