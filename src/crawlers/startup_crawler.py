import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger

from src.crawlers.base_crawler import BaseCrawler
from src.utils.date_parser import parse_date

class StartupCrawler(BaseCrawler):
    
    
    def __init__(self):
        super().__init__(source_name="Y Combinator")
        self.base_url = "https://www.ycombinator.com/companies"
        self.companies_per_page = 20  
    
    async def fetch(self, limit: int = 1000) -> List[Dict]:
        
        logger.info(f"Fetching {limit} startups from Y Combinator")
        
        all_startups = []
        pages_needed = (limit + self.companies_per_page - 1) // self.companies_per_page
        
        for page in range(1, pages_needed + 1):
            url = f"{self.base_url}?page={page}"
            
            logger.debug(f"Fetching page {page}/{pages_needed}")
            html = await self.fetch_url(url, use_playwright=True)
            
            if html:
                startups = self._parse_page(html, page)
                all_startups.extend(startups)
                logger.info(f"Page {page}: found {len(startups)} startups (total: {len(all_startups)})")
            else:
                logger.warning(f"Failed to fetch page {page}")
                break
            
            await asyncio.sleep(2)
        
        return all_startups[:limit]
    
    def _parse_page(self, html: str, page: int) -> List[Dict]:
        
        soup = BeautifulSoup(html, 'html.parser')
        companies = []
        
        selectors = [
            '._company_86jzd_338',  
            '.company-card',
            'a[href*="/companies/"]',
            '[class*="company"]'
        ]
        
        company_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                company_elements = elements
                break

        if not company_elements:
            links = soup.find_all('a', href=lambda x: x and '/companies/' in x and not 'page=' in x)
            
            company_elements = [link for link in links if not link.find_parent('nav')]
        
        for element in company_elements[:self.companies_per_page]:
            try:
                name = element.text.strip() if hasattr(element, 'text') else ''
                
                if element.name == 'a':
                    link = element.get('href', '')
                else:
                    link_tag = element.find('a')
                    link = link_tag.get('href', '') if link_tag else ''
                
                if link and not link.startswith('http'):
                    link = f"https://www.ycombinator.com{link}"
                
                desc_element = element.find_next('p')
                description = desc_element.text.strip() if desc_element else ''
                
                company = {
                    'name': name,
                    'url': link,
                    'description': description,
                    'source_page': page,
                }
                companies.append(company)
                
            except Exception as e:
                logger.error(f"Error parsing company element: {e}")
                continue
        
        return companies
    
    def parse(self, raw_startup: Dict) -> Dict:
        return {
            'schemaVersion': '1.0',
            'recordType': 'STARTUP',
            'source': {
                'name': 'Y Combinator',
                'url': raw_startup.get('url', '')
            },
            'content': {
                'entityName': raw_startup.get('name', ''),
                'description': raw_startup.get('description', ''),
                'employeeCount': None, 
            },
            'collectedAt': datetime.now().isoformat()
        }