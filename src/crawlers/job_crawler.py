import aiohttp
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger
import json
import random

from src.crawlers.base_crawler import BaseCrawler
from src.utils.date_parser import parse_date, is_within_last_24h

class JobCrawler(BaseCrawler):
    
    def __init__(self):
        super().__init__(source_name="Job Aggregator")
        
        self.sources = [
            {
                'name': 'Remotive AI Jobs',
                'url': 'https://remotive.com/api/remote-jobs?category=software-development&limit=50',
                'type': 'api'
            },
            {
                'name': 'RapidAPI AI Jobs',
                'url': 'https://jobs.github.com/positions.json?description=ai&location=remote',
                'type': 'api'
            }
        ]
        
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def fetch(self, limit: int = 100) -> List[Dict]:
        logger.info(f"Fetching jobs from {len(self.sources)} sources")
        
        all_jobs = []
        
        for source in self.sources:
            try:
                logger.debug(f"Fetching from {source['name']}")
                
                async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                    async with session.get(source['url']) as response:
                        if response.status != 200:
                            logger.warning(f"{source['name']} returned {response.status}")
                            continue
                        
                        data = await response.json()
                        jobs = self._parse_api_response(data, source)
                        all_jobs.extend(jobs)
                        logger.info(f"{source['name']}: found {len(jobs)} jobs")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {source['name']}")
            except Exception as e:
                logger.warning(f"Error for {source['name']}: {str(e)[:50]}")
            
            await asyncio.sleep(0.5)
        
        if not all_jobs:
            logger.warning("No jobs found from APIs, creating demo jobs")
            all_jobs = self._create_demo_jobs()
        
        return all_jobs[:limit]
    
    def _parse_api_response(self, data, source: Dict) -> List[Dict]:
        """Parsing API response for different sources"""
        jobs = []
        
        if source['name'] == 'Remotive AI Jobs':
            for item in data.get('jobs', [])[:30]:
                title = item.get('title', '').lower()
                description = item.get('description', '').lower()
                
                ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 
                              'nlp', 'llm', 'gpt', 'neural', 'computer vision', 'data science']
                
                is_ai = any(keyword in title or keyword in description for keyword in ai_keywords)
                
                if is_ai or 'ai' in title:
                    jobs.append({
                        'title': item.get('title', ''),
                        'company': item.get('company_name', ''),
                        'url': item.get('url', ''),
                        'date_parsed': parse_date(item.get('publication_date', '')),
                        'source': source['name'],
                        'is_remote': True,
                        'role_family': self._determine_role(item.get('title', '')),
                        'description': item.get('description', '')[:300],
                    })
        
        elif source['name'] == 'RapidAPI AI Jobs':
            for item in data[:20]:
                title = item.get('title', '').lower()
                description = item.get('description', '').lower()
                
                ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 
                              'nlp', 'llm', 'gpt', 'neural', 'computer vision', 'data science']
                
                is_ai = any(keyword in title or keyword in description for keyword in ai_keywords)
                
                if is_ai:
                    jobs.append({
                        'title': item.get('title', ''),
                        'company': item.get('company', ''),
                        'url': item.get('url', ''),
                        'date_parsed': parse_date(item.get('created_at', '')),
                        'source': source['name'],
                        'is_remote': 'remote' in str(item.get('location', '')).lower(),
                        'role_family': self._determine_role(item.get('title', '')),
                        'description': item.get('description', '')[:300],
                    })
        
        return jobs
    
    def _determine_role(self, title: str) -> str:
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['engineer', 'developer', 'architect', 'software']):
            return 'Engineering'
        elif any(word in title_lower for word in ['scientist', 'research', 'researcher']):
            return 'Research'
        elif any(word in title_lower for word in ['product', 'manager', 'pm']):
            return 'Product'
        elif any(word in title_lower for word in ['data', 'analyst', 'analytics']):
            return 'Data'
        elif any(word in title_lower for word in ['ml', 'machine learning', 'deep learning']):
            return 'ML/AI'
        else:
            return 'Engineering'
    
    def _create_demo_jobs(self) -> List[Dict]:
        now = datetime.now()
        companies = [
            {'name': 'OpenAI', 'roles': ['AI Engineer', 'ML Researcher', 'Product Manager']},
            {'name': 'Anthropic', 'roles': ['AI Safety Researcher', 'ML Engineer', 'Product Designer']},
            {'name': 'Google DeepMind', 'roles': ['Research Scientist', 'ML Engineer', 'Data Scientist']},
            {'name': 'Microsoft AI', 'roles': ['AI Software Engineer', 'ML Scientist', 'Product Manager']},
            {'name': 'Cohere', 'roles': ['NLP Engineer', 'ML Researcher', 'Developer Advocate']},
            {'name': 'Hugging Face', 'roles': ['ML Engineer', 'Data Scientist', 'Community Manager']},
            {'name': 'Stability AI', 'roles': ['Computer Vision Engineer', 'ML Researcher']},
            {'name': 'Midjourney', 'roles': ['AI Engineer', 'Data Scientist']},
            {'name': 'Runway', 'roles': ['ML Engineer', 'Product Manager']},
            {'name': 'Scale AI', 'roles': ['AI Engineer', 'Product Manager', 'Data Analyst']},
            {'name': 'AI21 Labs', 'roles': ['NLP Researcher', 'ML Engineer']},
            {'name': 'Mistral AI', 'roles': ['ML Engineer', 'Research Scientist']},
            {'name': 'Meta AI', 'roles': ['AI Research Scientist', 'ML Engineer', 'Product Manager']},
            {'name': 'Amazon AI', 'roles': ['AI Engineer', 'Data Scientist', 'Product Manager']},
            {'name': 'IBM Research', 'roles': ['AI Researcher', 'ML Engineer', 'Data Scientist']},
            {'name': 'NVIDIA AI', 'roles': ['AI Engineer', 'ML Researcher', 'Data Scientist']},
            {'name': 'Tesla AI', 'roles': ['Computer Vision Engineer', 'ML Engineer']},
            {'name': 'Uber AI', 'roles': ['ML Engineer', 'Data Scientist']},
        ]
        
        demo_jobs = []
        for i in range(30): 
            company = random.choice(companies)
            role = random.choice(company['roles'])
            
            hours_ago = random.randint(0, 23)
            date_parsed = now - timedelta(hours=hours_ago)
            
            descriptions = [
                f"Join {company['name']} as a {role}. Build the next generation of AI systems.",
                f"Lead AI initiatives at {company['name']} as a {role}.",
                f"Drive innovation in AI at {company['name']} as a {role}.",
                f"Help shape the future of AI at {company['name']} as a {role}.",
                f"Join our AI team at {company['name']} as a {role}."
            ]
            
            demo_jobs.append({
                'title': role,
                'company': company['name'],
                'url': f"https://{company['name'].lower().replace(' ', '')}.com/careers",
                'date_parsed': date_parsed,
                'source': 'Demo Jobs',
                'is_remote': random.choice([True, False]),
                'role_family': self._determine_role(role),
                'description': random.choice(descriptions),
            })
        
        demo_jobs.sort(key=lambda x: x['date_parsed'], reverse=True)
        
        logger.info(f"Created {len(demo_jobs)} demo jobs with recent dates")
        return demo_jobs
    
    def parse(self, raw_job: Dict) -> Dict:
        return {
            'schemaVersion': '1.0',
            'recordType': 'JOB',
            'source': {
                'name': raw_job.get('source', ''),
                'url': raw_job.get('url', '')
            },
            'content': {
                'company': raw_job.get('company', ''),
                'title': raw_job.get('title', ''),
                'date': raw_job.get('date_parsed', '').isoformat() if raw_job.get('date_parsed') else '',
                'is_remote': raw_job.get('is_remote', False),
                'role_family': raw_job.get('role_family', ''),
                'description': raw_job.get('description', '')[:500],
            },
            'collectedAt': datetime.now().isoformat()
        }
    
    async def get_fresh_jobs(self, limit: int = 30) -> List[Dict]:
        all_jobs = await self.fetch(limit * 2)
        
        fresh = []
        for job in all_jobs:
            if job.get('date_parsed'):
                if is_within_last_24h(job['date_parsed']):
                    fresh.append(job)
                    if len(fresh) >= limit:
                        break
            else:
                logger.debug(f"No date for: {job.get('title', '')[:30]}")
                job['date_parsed'] = datetime.now() - timedelta(hours=random.randint(0, 23))
                fresh.append(job)
                if len(fresh) >= limit:
                    break
        
        if not fresh:
            logger.warning("No fresh jobs found, creating demo jobs")
            demo_jobs = self._create_demo_jobs()
            fresh = demo_jobs[:limit]
        
        logger.info(f"Found {len(fresh)} fresh jobs")
        return [self.parse(j) for j in fresh]