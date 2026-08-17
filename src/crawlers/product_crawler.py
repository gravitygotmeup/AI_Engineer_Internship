import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger

from src.crawlers.base_crawler import BaseCrawler

class ProductCrawler(BaseCrawler):
   
    def __init__(self):
        super().__init__(source_name="Product Aggregator")
        
        self.sources = [
            {
                'name': 'Product Hunt AI',
                'url': 'https://www.producthunt.com/topics/artificial-intelligence',
                'base_url': 'https://www.producthunt.com',
                'product_selector': '.post-item',
                'title_selector': '.post-item__title',
                'link_selector': 'a',
                'description_selector': '.post-item__tagline',
                'pricing_selector': '.pricing-badge',
                'use_playwright': True
            },
            {
                'name': 'YC Companies',
                'url': 'https://www.ycombinator.com/companies',
                'base_url': 'https://www.ycombinator.com',
                'product_selector': '._company_86jzd_338',
                'title_selector': '._companyName_86jzd_380',
                'link_selector': 'a',
                'description_selector': '._tagline_86jzd_401',
                'pricing_selector': None,
                'use_playwright': True
            },
            {
                'name': 'AI Tools Directory',
                'url': 'https://www.ai-tools.directory/',
                'base_url': 'https://www.ai-tools.directory',
                'product_selector': '.tool-card',
                'title_selector': '.tool-name',
                'link_selector': 'a',
                'description_selector': '.tool-description',
                'pricing_selector': '.pricing-tag',
                'use_playwright': False
            }
        ]
        
        self.pricing_patterns = {
            'FREE': ['free', 'free forever', 'open source'],
            'FREEMIUM': ['freemium', 'free tier', 'free plan', 'free version'],
            'PAID': ['paid', 'premium', 'pro', 'enterprise pricing', 'subscription'],
            'ENTERPRISE': ['enterprise', 'custom pricing', 'contact sales']
        }
    
    async def fetch(self, limit: int = 1000) -> List[Dict]:
        
        logger.info(f"Fetching products from {len(self.sources)} sources")
        
        all_products = []
        
        for source in self.sources:
            logger.debug(f"Fetching from {source['name']}")
            
            try:
                use_playwright = source.get('use_playwright', False)
                html = await self.fetch_url(source['url'], use_playwright=use_playwright)
                
                if html:
                    products = self._parse_source(html, source)
                    all_products.extend(products)
                    logger.info(f"{source['name']}: found {len(products)} products")
                else:
                    logger.warning(f"Failed to fetch {source['name']}")
                    
            except Exception as e:
                logger.error(f"Error fetching {source['name']}: {e}")
            
            await asyncio.sleep(2)
        
        if not all_products:
            logger.warning("No products found, creating demo products")
            all_products = self._create_demo_products()
        
        return all_products[:limit]
    
    def _parse_source(self, html: str, source: Dict) -> List[Dict]:
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        product_elements = soup.select(source['product_selector'])
        
        if not product_elements:
            logger.warning(f"No elements found for {source['name']} with selector: {source['product_selector']}")
            return []
        
        for element in product_elements[:30]:  
            try:
                title_element = element.select_one(source['title_selector'])
                title = title_element.text.strip() if title_element else ''
                
                link_element = element.select_one(source['link_selector'])
                link = link_element.get('href', '') if link_element else ''
                
                if link and not link.startswith('http'):
                    if link.startswith('/'):
                        link = f"{source['base_url']}{link}"
                    else:
                        link = f"{source['base_url']}/{link}"
                
                desc_element = element.select_one(source['description_selector'])
                description = desc_element.text.strip() if desc_element else ''
                
                startup_name = self._extract_startup_name(element, source)
                
                pricing_text = ''
                if source.get('pricing_selector'):
                    pricing_element = element.select_one(source['pricing_selector'])
                    pricing_text = pricing_element.text.strip() if pricing_element else ''
                
                if not pricing_text:
                    pricing_text = self._detect_pricing_from_text(description + ' ' + title)
                
                pricing_model = self._determine_pricing_model(pricing_text)
                
                product = {
                    'title': title,
                    'url': link,
                    'description': description,
                    'startup_name': startup_name,
                    'pricing_text': pricing_text,
                    'pricing_model': pricing_model,
                    'source': source['name'],
                    'category': self._detect_category(title, description)
                }
                
                if title: 
                    products.append(product)
                
            except Exception as e:
                logger.error(f"Error parsing product: {e}")
                continue
        
        return products
    
    def _extract_startup_name(self, element, source: Dict) -> str:
        """Extract startup/company name from product element"""
        company_selectors = [
            '.company-name',
            '.startup-name',
            '.creator-name',
            '.by-company',
            '._companyName_86jzd_380'  
        ]
        
        for selector in company_selectors:
            company_elem = element.select_one(selector)
            if company_elem:
                return company_elem.text.strip()
        
        element_text = element.text
        match = re.search(r'(?:by|from)\s+([A-Z][a-zA-Z0-9\s\.]+)', element_text)
        if match:
            return match.group(1).strip()
        
        return ''
    
    def _detect_pricing_from_text(self, text: str) -> str:
        """Detect pricing information from text"""
        text_lower = text.lower()
        
        patterns = [
            r'\$\d+',
            r'\$\d+\.\d+',
            r'\$\d+/\s*(month|mo|year|yr)',
            r'free\s+(tier|plan|version)',
            r'freemium',
            r'open\s+source',
            r'enterprise\s+pricing',
            r'contact\s+sales',
            r'custom\s+pricing'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return text_lower
        
        return 'Unknown'
    
    def _determine_pricing_model(self, pricing_text: str) -> str:
        """Determining pricing model from text"""
        if not pricing_text:
            return 'UNKNOWN'
        
        pricing_text_lower = pricing_text.lower()
        
        for model, keywords in self.pricing_patterns.items():
            for keyword in keywords:
                if keyword in pricing_text_lower:
                    return model
        
        if re.search(r'\$\d+', pricing_text_lower):
            return 'PAID'
        
        if 'free' in pricing_text_lower and not any(x in pricing_text_lower for x in ['tier', 'plan', 'version']):
            return 'FREE'
        
        return 'UNKNOWN'
    
    def _detect_category(self, title: str, description: str) -> str:
        text = (title + ' ' + description).lower()
        
        categories = {
            'AI/ML': ['ai', 'machine learning', 'ml', 'deep learning', 'neural network', 'llm', 'gpt'],
            'NLP': ['nlp', 'language', 'text', 'translation', 'sentiment', 'chat', 'conversational'],
            'Computer Vision': ['vision', 'image', 'video', 'face', 'detection', 'recognition', 'cv'],
            'Data': ['data', 'analytics', 'insight', 'visualization', 'dashboard', 'bi'],
            'Developer Tools': ['api', 'sdk', 'developer', 'code', 'programming', 'dev', 'git'],
            'Productivity': ['productivity', 'automation', 'workflow', 'management', 'collaboration'],
            'Creativity': ['design', 'art', 'music', 'video', 'creative', 'generate'],
            'Business': ['sales', 'marketing', 'crm', 'finance', 'hr', 'recruiting'],
            'Healthcare': ['health', 'medical', 'diagnosis', 'drug', 'patient', 'clinical'],
            'Education': ['learn', 'teach', 'education', 'tutor', 'study', 'training']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        
        return 'Other'
    
    def _create_demo_products(self) -> List[Dict]:
        """Create demo products for testing"""
        demo_products = [
            {
                'title': 'ChatGPT',
                'url': 'https://chat.openai.com',
                'description': 'Advanced conversational AI assistant',
                'startup_name': 'OpenAI',
                'pricing_text': 'Free tier available, Pro at $20/month',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'AI/ML'
            },
            {
                'title': 'GitHub Copilot',
                'url': 'https://github.com/features/copilot',
                'description': 'AI-powered code completion',
                'startup_name': 'GitHub',
                'pricing_text': '$10/month or $100/year',
                'pricing_model': 'PAID',
                'source': 'Demo',
                'category': 'Developer Tools'
            },
            {
                'title': 'Midjourney',
                'url': 'https://www.midjourney.com',
                'description': 'AI image generation',
                'startup_name': 'Midjourney',
                'pricing_text': '$10-60/month subscription',
                'pricing_model': 'PAID',
                'source': 'Demo',
                'category': 'Creativity'
            },
            {
                'title': 'Hugging Face',
                'url': 'https://huggingface.co',
                'description': 'AI models and datasets platform',
                'startup_name': 'Hugging Face',
                'pricing_text': 'Free tier, Enterprise available',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'AI/ML'
            },
            {
                'title': 'Notion AI',
                'url': 'https://www.notion.so',
                'description': 'AI-powered workspace',
                'startup_name': 'Notion',
                'pricing_text': '$10/month add-on',
                'pricing_model': 'PAID',
                'source': 'Demo',
                'category': 'Productivity'
            },
            {
                'title': 'Canva AI',
                'url': 'https://www.canva.com',
                'description': 'AI-powered design tools',
                'startup_name': 'Canva',
                'pricing_text': 'Free tier, Pro at $12.99/month',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'Creativity'
            },
            {
                'title': 'Clerk',
                'url': 'https://clerk.com',
                'description': 'AI-powered authentication',
                'startup_name': 'Clerk',
                'pricing_text': 'Free tier, Enterprise pricing',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'Developer Tools'
            },
            {
                'title': 'Synthesia',
                'url': 'https://www.synthesia.io',
                'description': 'AI video generation',
                'startup_name': 'Synthesia',
                'pricing_text': '$30/month, Enterprise plans',
                'pricing_model': 'PAID',
                'source': 'Demo',
                'category': 'Creativity'
            },
            {
                'title': 'Runway ML',
                'url': 'https://runwayml.com',
                'description': 'AI video and image editing',
                'startup_name': 'Runway',
                'pricing_text': 'Free tier, Pro at $15/month',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'Creativity'
            },
            {
                'title': 'Tome',
                'url': 'https://tome.app',
                'description': 'AI-powered storytelling',
                'startup_name': 'Tome',
                'pricing_text': 'Free tier, Pro available',
                'pricing_model': 'FREEMIUM',
                'source': 'Demo',
                'category': 'Productivity'
            }
        ]
        logger.info(f"Created {len(demo_products)} demo products")
        return demo_products
    
    def parse(self, raw_product: Dict) -> Dict:
        return {
            'schemaVersion': '1.0',
            'recordType': 'PRODUCT',
            'source': {
                'name': raw_product.get('source', ''),
                'url': raw_product.get('url', '')
            },
            'content': {
                'startupName': raw_product.get('startup_name', ''),
                'productName': raw_product.get('title', ''),
                'description': raw_product.get('description', ''),
                'pricingModel': raw_product.get('pricing_model', 'UNKNOWN'),
                'category': raw_product.get('category', 'Other'),
            },
            'collectedAt': datetime.now().isoformat()
        }
    
    async def get_products(self, limit: int = 1000) -> List[Dict]:
    
        raw_products = await self.fetch(limit)
        parsed_products = [self.parse(p) for p in raw_products]
        logger.info(f"Returning {len(parsed_products)} products")
        return parsed_products