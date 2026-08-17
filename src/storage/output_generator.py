import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger

class OutputGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
    
    def generate_startups(self, startups: list):
        """Generate startups CSV"""
        if not startups:
            logger.warning("No startups to generate")
            return
        
        try:
            rows = []
            for startup in startups:
                row = {
                    'schemaVersion': startup.get('schemaVersion', '1.0'),
                    'recordType': startup.get('recordType', 'STARTUP'),
                    'source_name': startup.get('source', {}).get('name', ''),
                    'source_url': startup.get('source', {}).get('url', ''),
                    'entityName': startup.get('content', {}).get('entityName', ''),
                    'employeeCount': startup.get('content', {}).get('employeeCount', ''),
                    'collectedAt': startup.get('collectedAt', ''),
                    'resolution_method': startup.get('content', {}).get('entityResolution', {}).get('method', ''),
                    'resolution_confidence': startup.get('content', {}).get('entityResolution', {}).get('confidence', 0)
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            file_path = self.output_dir / 'startups.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated startups.csv with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error generating startups: {e}")
    
    def generate_products(self, products: list):
        if not products:
            logger.warning("No products to generate")
            return
        
        try:
            rows = []
            for product in products:
                row = {
                    'schemaVersion': product.get('schemaVersion', '1.0'),
                    'recordType': product.get('recordType', 'PRODUCT'),
                    'source_name': product.get('source', {}).get('name', ''),
                    'source_url': product.get('source', {}).get('url', ''),
                    'startupName': product.get('content', {}).get('startupName', ''),
                    'pricingModel': product.get('content', {}).get('pricingModel', 'UNKNOWN'),
                    'collectedAt': product.get('collectedAt', ''),
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            file_path = self.output_dir / 'products.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated products.csv with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error generating products: {e}")
    
    def generate_papers(self, papers: list):
        if not papers:
            logger.warning("No papers to generate")
            return
        
        try:
            rows = []
            for paper in papers:
                row = {
                    'schemaVersion': paper.get('schemaVersion', '1.0'),
                    'recordType': paper.get('recordType', 'RESEARCH_PAPER'),
                    'title': paper.get('content', {}).get('title', ''),
                    'authors': ', '.join(paper.get('content', {}).get('authors', [])),
                    'paper_url': paper.get('content', {}).get('paper_url', ''),
                    'github_url': paper.get('content', {}).get('github_url', ''),
                    'github_stars': paper.get('content', {}).get('github_stars', 0),
                    'published_date': paper.get('content', {}).get('published_date', ''),
                    'collectedAt': paper.get('collectedAt', ''),
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            file_path = self.output_dir / 'papers.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated papers.csv with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error generating papers: {e}")
    
    def generate_news(self, news: list):
        """Generate news CSV"""
        if not news:
            logger.warning("No news to generate")
            return
        
        try:
            rows = []
            for article in news:
                row = {
                    'schemaVersion': article.get('schemaVersion', '1.0'),
                    'recordType': article.get('recordType', 'NEWS'),
                    'source_name': article.get('source', {}).get('name', ''),
                    'source_url': article.get('source', {}).get('url', ''),
                    'title': article.get('content', {}).get('title', ''),
                    'date': article.get('content', {}).get('date', ''),
                    'collectedAt': article.get('collectedAt', ''),
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            file_path = self.output_dir / 'news.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated news.csv with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error generating news: {e}")
    
    def generate_jobs(self, jobs: list):
        if not jobs:
            logger.warning("No jobs to generate - creating empty file")
            df = pd.DataFrame(columns=[
                'schemaVersion', 'recordType', 'company', 'date', 
                'is_remote', 'role_family', 'collectedAt'
            ])
            file_path = self.output_dir / 'jobs.csv'
            df.to_csv(file_path, index=False)
            logger.info("Generated empty jobs.csv")
            return
        
        try:
            rows = []
            for job in jobs:
                row = {
                    'schemaVersion': job.get('schemaVersion', '1.0'),
                    'recordType': job.get('recordType', 'JOB'),
                    'company': job.get('content', {}).get('company', ''),
                    'date': job.get('content', {}).get('date', ''),
                    'is_remote': job.get('content', {}).get('is_remote', False),
                    'role_family': job.get('content', {}).get('role_family', ''),
                    'collectedAt': job.get('collectedAt', ''),
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            file_path = self.output_dir / 'jobs.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated jobs.csv with {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error generating jobs: {e}")
    
    def generate_summary(self, stats: dict):
        """Generate summary statistics"""
        summary = {
            'Metric': ['Startups', 'Products', 'Research Papers', 'News Articles', 'Jobs', 'Errors'],
            'Count': [
                stats.get('startups', 0),
                stats.get('products', 0),
                stats.get('papers', 0),
                stats.get('news', 0),
                stats.get('jobs', 0),
                stats.get('errors', 0)
            ],
            'Timestamp': [datetime.now().isoformat()] * 6
        }
        
        try:
            df = pd.DataFrame(summary)
            file_path = self.output_dir / 'summary.csv'
            df.to_csv(file_path, index=False)
            logger.info(f"Generated summary.csv")
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
