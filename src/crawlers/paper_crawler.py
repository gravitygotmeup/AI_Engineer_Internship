import aiohttp
import asyncio
import re
import os
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from loguru import logger
import json
from pathlib import Path
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
from src.utils.date_parser import parse_date

class PaperCrawler(BaseCrawler):
    
    def __init__(self):
        super().__init__(source_name="arXiv")
        self.base_url = "http://export.arxiv.org/api/query"
        self.category = "cs.AI"  
        self.github_pattern = re.compile(r'https?://github\.com/[\w-]+/[\w-]+')
        
    
        self.github_token = os.getenv('GITHUB_TOKEN')  
        self.github_cache = {} 
        self.cache_file = Path(Config.OUTPUT_DIR) / 'github_cache.json'
        self._load_cache()
        
        self.github_semaphore = asyncio.Semaphore(10)  
        self.github_rate_limit = 60  
        self.github_last_request = datetime.now()
        self.github_request_count = 0
    
    def _load_cache(self):
        """Loading GitHub stars cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.github_cache = json.load(f)
                logger.info(f"Loaded {len(self.github_cache)} cached GitHub entries")
        except Exception as e:
            logger.warning(f"Could not load GitHub cache: {e}")
            self.github_cache = {}
    
    def _save_cache(self):
        """Saving GitHub stars cache to file"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.github_cache, f, indent=2)
            logger.debug(f"Saved {len(self.github_cache)} GitHub entries to cache")
        except Exception as e:
            logger.warning(f"Could not save GitHub cache: {e}")
    
    async def fetch(self, limit: int = 1000) -> List[Dict]:
        
        logger.info(f"Fetching {limit} papers from arXiv")
        
        all_papers = []
        batch_size = 50 
        total_batches = (limit + batch_size - 1) // batch_size
        
        if limit > 2000:
            logger.warning(f"Reducing limit from {limit} to 2000 for performance")
            limit = 2000
            total_batches = (limit + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start = batch_num * batch_size
            current_batch_size = min(batch_size, limit - start)
            
            params = {
                "search_query": f"cat:{self.category}",
                "start": start,
                "max_results": current_batch_size,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            xml_data = await response.text()
                            batch_papers = self._parse_arxiv_response(xml_data)
                            all_papers.extend(batch_papers)
                            logger.debug(f"Fetched batch {batch_num + 1}/{total_batches}: {len(batch_papers)} papers")
                        else:
                            logger.error(f"Arxiv API error: {response.status}")
            except Exception as e:
                logger.error(f"Error fetching arXiv batch: {e}")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"Fetched {len(all_papers)} papers from arXiv")
        return all_papers
    
    def _parse_arxiv_response(self, xml_data: str) -> List[Dict]:
        root = ET.fromstring(xml_data)
        papers = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            try:
                title = entry.find('atom:title', ns).text.strip()
                paper_id = entry.find('atom:id', ns).text.strip()
                published_date = entry.find('atom:published', ns).text.strip()
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text.strip())
                
                abstract = entry.find('atom:summary', ns)
                abstract_text = abstract.text.strip() if abstract is not None else ""
                
                github_url = self._extract_github_url(abstract_text)
                
                paper = {
                    'arxiv_id': paper_id.split('/')[-1],
                    'title': title,
                    'authors': authors,
                    'paper_url': paper_id,
                    'abstract': abstract_text,
                    'published_date': published_date,
                    'github_url': github_url,
                    'github_stars': None,
                }
                papers.append(paper)
                
            except Exception as e:
                logger.error(f"Error parsing paper entry: {e}")
                continue
        
        return papers
    
    def _extract_github_url(self, text: str) -> Optional[str]:
        match = self.github_pattern.search(text)
        return match.group(0) if match else None
    
    async def _fetch_github_stars_optimized(self, repo_urls: List[Optional[str]]) -> Dict[str, int]:
        
        results = {}
        
        unique_urls = list(set([url for url in repo_urls if url]))
        
        if not unique_urls:
            return results
        
        logger.info(f"Fetching GitHub stars for {len(unique_urls)} unique repositories")
        
        urls_to_fetch = []
        for url in unique_urls:
            if url in self.github_cache:
                results[url] = self.github_cache[url]
                logger.debug(f"Cache hit: {url} -> {self.github_cache[url]} stars")
            else:
                urls_to_fetch.append(url)
        
        if not urls_to_fetch:
            logger.info(f"All {len(unique_urls)} URLs found in cache")
            return results
        
        logger.info(f"Fetching {len(urls_to_fetch)} URLs from GitHub API")
        
        batch_size = 10  
        for i in range(0, len(urls_to_fetch), batch_size):
            batch = urls_to_fetch[i:i+batch_size]
            
            await self._check_github_rate_limit()
            
            tasks = []
            for url in batch:
                tasks.append(self._fetch_single_github_stars(url))
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch stars for {url}: {result}")
                    results[url] = self.github_cache.get(url, 0)
                else:
                    stars = result
                    results[url] = stars
                    self.github_cache[url] = stars
            
            self.github_request_count += len(batch)
            
            if i % 50 == 0:
                self._save_cache()
            
            await asyncio.sleep(0.5)
        
        self._save_cache()
        
        logger.info(f"Fetched {len(results)} GitHub star counts")
        return results
    
    async def _check_github_rate_limit(self):
        rate_limit = 5000 if self.github_token else 60
        window_seconds = 3600  
        elapsed = (datetime.now() - self.github_last_request).total_seconds()
        
        if elapsed > window_seconds:
            self.github_request_count = 0
            self.github_last_request = datetime.now()
        
        if self.github_request_count >= rate_limit - 10:  
            wait_time = window_seconds - elapsed + 60 
            logger.warning(f"GitHub rate limit approaching. Waiting {wait_time:.0f} seconds...")
            await asyncio.sleep(wait_time)
            self.github_request_count = 0
            self.github_last_request = datetime.now()
    
    async def _fetch_single_github_stars(self, repo_url: str) -> int:
        
        if not repo_url:
            return 0
        
        if repo_url in self.github_cache:
            return self.github_cache[repo_url]
        
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            return 0
        
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AI-Engineer-Demo/1.0'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        async with self.github_semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            stars = data.get('stargazers_count', 0)
                            logger.debug(f"GitHub: {repo_url} -> {stars} stars")
                            return stars
                        elif response.status == 403:
                            
                            reset_time = response.headers.get('X-RateLimit-Reset')
                            if reset_time:
                                reset_datetime = datetime.fromtimestamp(int(reset_time))
                                wait_time = (reset_datetime - datetime.now()).total_seconds() + 10
                                logger.warning(f"GitHub rate limit. Waiting {wait_time:.0f} seconds...")
                                await asyncio.sleep(max(0, wait_time))
                            return self.github_cache.get(repo_url, 0)
                        elif response.status == 404:
                            logger.debug(f"Repository not found: {repo_url}")
                            return 0
                        else:
                            logger.debug(f"GitHub API returned {response.status} for {repo_url}")
                            return self.github_cache.get(repo_url, 0)
            except asyncio.TimeoutError:
                logger.debug(f"Timeout fetching GitHub stars for {repo_url}")
                return self.github_cache.get(repo_url, 0)
            except Exception as e:
                logger.error(f"Error fetching GitHub stars for {repo_url}: {e}")
                return self.github_cache.get(repo_url, 0)
    
    def parse(self, raw_paper: Dict) -> Dict:
        return {
            'schemaVersion': '1.0',
            'recordType': 'RESEARCH_PAPER',
            'source': {
                'name': 'arXiv',
                'url': raw_paper.get('paper_url', '')
            },
            'content': {
                'title': raw_paper.get('title', ''),
                'authors': raw_paper.get('authors', []),
                'paper_url': raw_paper.get('paper_url', ''),
                'github_url': raw_paper.get('github_url', ''),
                'github_stars': raw_paper.get('github_stars', 0),
                'published_date': parse_date(raw_paper.get('published_date', ''))
            },
            'collectedAt': datetime.now().isoformat()
        }
    
    async def run(self, limit: int = 1000) -> List[Dict]:
        
        papers = await self.fetch(limit)
        
        if not papers:
            return []
        
        github_urls = [paper.get('github_url') for paper in papers]
        
        logger.info(f"Fetching GitHub stars for {len(github_urls)} papers (optimized)")
        stars_map = await self._fetch_github_stars_optimized(github_urls)
        
        for paper in papers:
            url = paper.get('github_url')
            if url and url in stars_map:
                paper['github_stars'] = stars_map[url]
            else:
                paper['github_stars'] = 0
        
        parsed_papers = [self.parse(paper) for paper in papers]
        
        logger.success(f"Successfully processed {len(parsed_papers)} papers")
        return parsed_papers
    
    def get_github_stats(self) -> Dict:
        return {
            'cache_size': len(self.github_cache),
            'request_count': self.github_request_count,
            'cached_entries': len([k for k in self.github_cache if self.github_cache[k] > 0])
        }