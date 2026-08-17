# scripts/run_pipeline.py
"""
Main pipeline orchestrator - COMPLETE VERSION with LLM Integration
Collects papers, startups, products, news, and jobs with LLM processing
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import Config
from src.crawlers.paper_crawler import PaperCrawler
from src.crawlers.startup_crawler import StartupCrawler
from src.crawlers.product_crawler import ProductCrawler
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.job_crawler import JobCrawler
from src.llm.orchestrator import LLMOrchestrator
from src.resolvers.entity_resolver import EntityResolver
from src.storage.output_generator import OutputGenerator
from src.utils.logger import setup_logger

class Pipeline:
    """
    Main pipeline orchestrator with LLM integration
    
    Phases:
    1. Collect research papers with GitHub stars
    2. Collect startups from Y Combinator
    3. Collect products from directories
    4. Collect fresh news (24-hour freshness)
    5. Collect fresh jobs (24-hour freshness)
    6. LLM Processing - Extract structured data
    7. Entity Resolution - Canonicalize names
    8. Generate output files
    """
    
    def __init__(self):
        setup_logger()
        self.logger = logger
        
        # Initialize crawlers
        self.paper_crawler = PaperCrawler()
        self.startup_crawler = StartupCrawler()
        self.product_crawler = ProductCrawler()
        self.news_crawler = NewsCrawler()
        self.job_crawler = JobCrawler()
        
        # Initialize LLM Orchestrator
        self.llm_orchestrator = LLMOrchestrator()
        
        # Initialize resolver with seed entities
        seed_file = Config.SEED_DATA_DIR / 'seed_startups.csv'
        self.resolver = EntityResolver(str(seed_file) if seed_file.exists() else None)
        
        # Initialize output generator
        self.output_generator = OutputGenerator(Config.OUTPUT_DIR)
        
        # Statistics
        self.stats = {
            'papers': 0,
            'startups': 0,
            'products': 0,
            'news': 0,
            'jobs': 0,
            'llm_processed': 0,
            'llm_failed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    async def run(self):
        """
        Run the complete pipeline with LLM integration
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting AI Engineer Demo Pipeline (with LLM)")
        self.logger.info("=" * 60)
        
        try:
            # Phase 1: Research Papers
            self.logger.info("\n📄 PHASE 1: Collecting Research Papers")
            papers = await self._collect_papers()
            
            # Phase 2: Startups
            self.logger.info("\n🏢 PHASE 2: Collecting Startups")
            startups = await self._collect_startups()
            
            # Phase 3: Products
            self.logger.info("\n📱 PHASE 3: Collecting Products")
            products = await self._collect_products()
            
            # Phase 4: Fresh News
            self.logger.info("\n📰 PHASE 4: Collecting Fresh News")
            news = await self._collect_news()
            
            # Phase 5: Fresh Jobs
            self.logger.info("\n💼 PHASE 5: Collecting Fresh Jobs")
            jobs = await self._collect_jobs()
            
            # Phase 6: LLM Processing
            self.logger.info("\n🤖 PHASE 6: LLM Processing")
            llm_processed = await self._process_with_llm({
                'startups': startups,
                'products': products,
                'papers': papers,
                'news': news,
                'jobs': jobs
            })
            
            # Phase 7: Entity Resolution
            self.logger.info("\n🔍 PHASE 7: Resolving Entities")
            resolved_data = await self._resolve_entities(llm_processed)
            
            # Phase 8: Generate Output
            self.logger.info("\n📊 PHASE 8: Generating Output")
            await self._generate_output(resolved_data, news, jobs)
            
            # Summary
            self._print_summary()
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def _collect_papers(self) -> list:
        """
        Collect research papers with GitHub stars
        
        Returns:
            List of paper records
        """
        try:
            # Collect 1100 papers, will use top 1000
            papers = await self.paper_crawler.run(limit=1100)
            self.stats['papers'] = len(papers)
            
            # Show GitHub stats
            stats = self.paper_crawler.get_github_stats()
            self.logger.info(f"📊 GitHub Cache: {stats['cache_size']} entries, {stats['request_count']} requests")
            
            self.logger.success(f"✅ Collected {len(papers)} research papers")
            return papers[:1000]  # Use top 1000
        except Exception as e:
            self.logger.error(f"Paper collection failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _collect_startups(self) -> list:
        """
        Collect startup data from Y Combinator
        
        Returns:
            List of startup records
        """
        try:
            # Collect 1100 startups, will use top 1000
            startups = await self.startup_crawler.run(limit=1100)
            self.stats['startups'] = len(startups)
            self.logger.success(f"✅ Collected {len(startups)} startups")
            return startups[:1000]
        except Exception as e:
            self.logger.error(f"Startup collection failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _collect_products(self) -> list:
        """
        Collect products from product directories
        
        Returns:
            List of product records
        """
        try:
            # Collect 1100 products, will use top 1000
            products = await self.product_crawler.get_products(limit=1100)
            self.stats['products'] = len(products)
            
            # Count pricing models
            pricing_counts = {}
            for product in products:
                model = product.get('content', {}).get('pricingModel', 'UNKNOWN')
                pricing_counts[model] = pricing_counts.get(model, 0) + 1
            
            self.logger.info(f"📊 Pricing Models: {pricing_counts}")
            self.logger.success(f"✅ Collected {len(products)} products")
            return products[:1000]
        except Exception as e:
            self.logger.error(f"Product collection failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _collect_news(self) -> list:
        """
        Collect fresh news (last 24 hours)
        
        Returns:
            List of news records
        """
        try:
            news = await self.news_crawler.get_fresh_news(limit=50)
            self.stats['news'] = len(news)
            
            if news:
                # Show sample dates
                dates = [n.get('content', {}).get('date', '') for n in news[:5]]
                self.logger.info(f"📊 Sample dates: {dates}")
            else:
                self.logger.warning("No fresh news found")
            
            self.logger.success(f"✅ Collected {len(news)} fresh news articles")
            return news
        except Exception as e:
            self.logger.error(f"News collection failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _collect_jobs(self) -> list:
        """
        Collect fresh jobs (last 24 hours)
        
        Returns:
            List of job records
        """
        try:
            jobs = await self.job_crawler.get_fresh_jobs(limit=50)
            self.stats['jobs'] = len(jobs)
            
            if jobs:
                # Show role families
                roles = {}
                for job in jobs:
                    role = job.get('content', {}).get('role_family', 'Unknown')
                    roles[role] = roles.get(role, 0) + 1
                self.logger.info(f"📊 Role Families: {roles}")
            
            self.logger.success(f"✅ Collected {len(jobs)} fresh job listings")
            return jobs
        except Exception as e:
            self.logger.error(f"Job collection failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def _process_with_llm(self, data: dict) -> dict:
        """
        Process extracted data with LLM to structure it
        
        Args:
            data: Raw data from crawlers
        
        Returns:
            LLM-processed structured data
        """
        self.logger.info("🔄 Processing data with LLM Orchestrator...")
        self.logger.info(f"📊 LLM Models: Gemini → Groq → DeepSeek (fallback chain)")
        
        processed_data = {
            'startups': [],
            'products': [],
            'papers': [],
            'news': [],
            'jobs': []
        }
        
        # Define schema for each entity type
        startup_schema = {
            "type": "object",
            "properties": {
                "entityName": {"type": "string"},
                "description": {"type": "string"},
                "employeeCount": {"type": "integer"},
                "industry": {"type": "string"},
                "foundedYear": {"type": "integer"}
            },
            "required": ["entityName"]
        }
        
        product_schema = {
            "type": "object",
            "properties": {
                "productName": {"type": "string"},
                "description": {"type": "string"},
                "pricingModel": {"type": "string"},
                "category": {"type": "string"}
            },
            "required": ["productName"]
        }
        
        # Process startups with LLM
        if data.get('startups'):
            self.logger.info(f"📤 Processing {len(data['startups'])} startups with LLM...")
            processed_count = 0
            failed_count = 0
            
            for i, startup in enumerate(data['startups']):
                try:
                    # Get raw content
                    raw_name = startup.get('content', {}).get('entityName', '')
                    raw_desc = startup.get('content', {}).get('description', '')
                    
                    # Create content for LLM
                    content = f"Company: {raw_name}\nDescription: {raw_desc}"
                    
                    # Extract structured data
                    if content and len(content) > 10:
                        structured = await self.llm_orchestrator.extract_structured_data(
                            content, 
                            startup_schema
                        )
                        
                        if structured:
                            startup['content']['llm_processed'] = structured
                            # Update fields if LLM extracted better data
                            if structured.get('entityName'):
                                startup['content']['entityName'] = structured['entityName']
                            if structured.get('description'):
                                startup['content']['description'] = structured['description']
                            if structured.get('employeeCount'):
                                startup['content']['employeeCount'] = structured['employeeCount']
                            processed_count += 1
                            self.stats['llm_processed'] += 1
                        else:
                            failed_count += 1
                            self.stats['llm_failed'] += 1
                    else:
                        failed_count += 1
                    
                    # Progress indicator
                    if (i + 1) % 100 == 0:
                        self.logger.info(f"  Processed {i+1}/{len(data['startups'])} startups (✅ {processed_count} successful)")
                    
                    # Rate limiting - small delay between requests
                    if i % 10 == 0:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    self.logger.error(f"LLM processing failed for startup: {e}")
                    failed_count += 1
                    self.stats['llm_failed'] += 1
                    self.stats['errors'] += 1
            
            self.logger.info(f"✅ Startups processed: {processed_count} successful, {failed_count} failed")
            processed_data['startups'] = data['startups']
        
        # Process products with LLM
        if data.get('products'):
            self.logger.info(f"📤 Processing {len(data['products'])} products with LLM...")
            processed_count = 0
            failed_count = 0
            
            for i, product in enumerate(data['products']):
                try:
                    raw_name = product.get('content', {}).get('productName', '')
                    raw_desc = product.get('content', {}).get('description', '')
                    
                    content = f"Product: {raw_name}\nDescription: {raw_desc}"
                    
                    if content and len(content) > 10:
                        structured = await self.llm_orchestrator.extract_structured_data(
                            content,
                            product_schema
                        )
                        
                        if structured:
                            product['content']['llm_processed'] = structured
                            # Update pricing model if extracted
                            if structured.get('pricingModel'):
                                product['content']['pricingModel'] = structured['pricingModel']
                            if structured.get('category'):
                                product['content']['category'] = structured['category']
                            processed_count += 1
                            self.stats['llm_processed'] += 1
                        else:
                            failed_count += 1
                            self.stats['llm_failed'] += 1
                    else:
                        failed_count += 1
                    
                    if (i + 1) % 100 == 0:
                        self.logger.info(f"  Processed {i+1}/{len(data['products'])} products (✅ {processed_count} successful)")
                    
                    if i % 10 == 0:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    self.logger.error(f"LLM processing failed for product: {e}")
                    failed_count += 1
                    self.stats['llm_failed'] += 1
                    self.stats['errors'] += 1
            
            self.logger.info(f"✅ Products processed: {processed_count} successful, {failed_count} failed")
            processed_data['products'] = data['products']
        
        # Pass through other data without LLM processing
        processed_data['papers'] = data.get('papers', [])
        processed_data['news'] = data.get('news', [])
        processed_data['jobs'] = data.get('jobs', [])
        
        # Show LLM stats
        stats = self.llm_orchestrator.get_stats()
        self.logger.info(f"📊 LLM Orchestrator Stats:")
        self.logger.info(f"  Total Requests: {stats['total_requests']}")
        self.logger.info(f"  Successful: {stats['successful_requests']}")
        self.logger.info(f"  Failed: {stats['failed_requests']}")
        self.logger.info(f"  Fallbacks Used: {stats['fallback_used']}")
        self.logger.info(f"  Model Usage: {stats['model_usage']}")
        
        return processed_data
    
    async def _resolve_entities(self, data: dict) -> dict:
        """
        Resolve entity names to canonical forms
        
        Args:
            data: Dictionary with startups, products, papers
        
        Returns:
            Resolved data with canonical names
        """
        resolved = {
            'startups': [],
            'products': [],
            'papers': [],
            'news': [],
            'jobs': []
        }
        
        # Resolve startup names
        if data.get('startups'):
            for startup in data['startups']:
                raw_name = startup.get('content', {}).get('entityName', '')
                if raw_name:
                    resolved_name = self.resolver.resolve(raw_name)
                    startup['content']['entityName'] = resolved_name['canonical']
                    startup['content']['entityResolution'] = resolved_name
                resolved['startups'].append(startup)
        
        # Resolve product startup names
        if data.get('products'):
            for product in data['products']:
                raw_name = product.get('content', {}).get('startupName', '')
                if raw_name:
                    resolved_name = self.resolver.resolve(raw_name)
                    product['content']['startupName'] = resolved_name['canonical']
                    product['content']['entityResolution'] = resolved_name
                resolved['products'].append(product)
        
        # Pass through other data
        resolved['papers'] = data.get('papers', [])
        resolved['news'] = data.get('news', [])
        resolved['jobs'] = data.get('jobs', [])
        
        # Export mapping log
        mapping_file = Config.OUTPUT_DIR / 'entity_mapping.csv'
        self.resolver.export_mapping_log(str(mapping_file))
        
        total_mappings = len(self.resolver.get_mapping_log())
        self.logger.info(f"📊 Total entity mappings: {total_mappings}")
        
        return resolved
    
    async def _generate_output(self, data: dict, news: list, jobs: list):
        """
        Generate all output files
        
        Args:
            data: Resolved data with startups, products, papers
            news: Fresh news articles
            jobs: Fresh job listings
        """
        # Generate each output
        self.output_generator.generate_startups(data.get('startups', []))
        self.output_generator.generate_products(data.get('products', []))
        self.output_generator.generate_papers(data.get('papers', []))
        self.output_generator.generate_news(news)
        self.output_generator.generate_jobs(jobs)
        self.output_generator.generate_summary(self.stats)
        
        self.logger.success("✅ All output files generated")
        
        # Show output directory contents
        output_dir = Config.OUTPUT_DIR
        files = list(output_dir.glob('*.csv'))
        self.logger.info(f"📁 Output files: {', '.join([f.name for f in files])}")
    
    def _print_summary(self):
        """Print execution summary"""
        elapsed = datetime.now() - self.stats['start_time']
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 PIPELINE EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"📄 Research Papers: {self.stats['papers']}")
        self.logger.info(f"🏢 Startups: {self.stats['startups']}")
        self.logger.info(f"📱 Products: {self.stats['products']}")
        self.logger.info(f"📰 News Articles: {self.stats['news']}")
        self.logger.info(f"💼 Jobs: {self.stats['jobs']}")
        self.logger.info(f"🤖 LLM Processed: {self.stats['llm_processed']}")
        self.logger.info(f"❌ LLM Failed: {self.stats['llm_failed']}")
        self.logger.info(f"❌ Errors: {self.stats['errors']}")
        self.logger.info(f"⏱️  Time: {elapsed}")
        self.logger.info("=" * 60)
        
        # Check if all requirements met
        requirements_met = True
        if self.stats['papers'] < 1000:
            self.logger.warning("⚠️ Papers requirement not met (need 1000+)")
            requirements_met = False
        if self.stats['startups'] < 1000:
            self.logger.warning("⚠️ Startups requirement not met (need 1000+)")
            requirements_met = False
        if self.stats['products'] < 1000:
            self.logger.warning("⚠️ Products requirement not met (need 1000+)")
            requirements_met = False
        if self.stats['news'] == 0:
            self.logger.warning("⚠️ No news articles found (need 24-hour fresh)")
            requirements_met = False
        if self.stats['jobs'] == 0:
            self.logger.warning("⚠️ No jobs found (need 24-hour fresh)")
            requirements_met = False
        if self.stats['llm_processed'] == 0:
            self.logger.warning("⚠️ No LLM processing was successful")
            requirements_met = False
        
        if requirements_met:
            self.logger.success("✅ All requirements met! Ready for submission.")
        else:
            self.logger.warning("⚠️ Some requirements not met. Please check the issues above.")
        
        self.logger.info("=" * 60)
        self.logger.info("✅ Pipeline completed!")

async def main():
    """Main entry point"""
    pipeline = Pipeline()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())