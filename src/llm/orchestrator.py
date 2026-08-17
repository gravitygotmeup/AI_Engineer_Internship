import asyncio
import random
from typing import Dict, Any, Optional, List
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config
from src.llm.models.gemini import GeminiExtractor
from src.llm.models.groq import GroqExtractor
from src.llm.models.deepseek import DeepSeekExtractor
from src.llm.chunking import IntelligentChunker
from src.llm.rate_limiter import RateLimiter

class LLMOrchestrator:
    
    def __init__(self):
        self.chunker = IntelligentChunker(max_tokens=8000)
        self.rate_limiter = RateLimiter()
        
        self.models = [
            GeminiExtractor(),
            GroqExtractor(),
            DeepSeekExtractor()
        ]
        
        self.current_model_index = 0
        self.fallback_count = 0
        self.max_fallbacks = len(self.models) - 1
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallback_used': 0,
            'model_usage': {}
        }
        
        for model in self.models:
            self.stats['model_usage'][model.display_name] = 0
        
        logger.info(f"Initialized LLM Orchestrator with {len(self.models)} models")
    
    async def extract_structured_data(
        self,
        content: str,
        schema: Dict[str, Any],
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        
        self.stats['total_requests'] += 1
        
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.get_wait_time()
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        chunks = self.chunker.chunk_content(content)
        
        if len(chunks) > 1:
            logger.info(f"Content split into {len(chunks)} chunks for LLM processing")
            
            combined_results = {}
            for i, chunk in enumerate(chunks):
                logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                result = await self._extract_with_fallback(chunk, schema)
                
                if result:
                    combined_results.update(result)
                    
                    if self._schema_complete(combined_results, schema):
                        break
            
            self.stats['successful_requests'] += 1
            return combined_results if combined_results else None
        
        result = await self._extract_with_fallback(content, schema)
        
        if result:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
        
        return result
    
    async def _extract_with_fallback(
        self,
        content: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        
        start_index = self.current_model_index
        
        for i in range(start_index, len(self.models)):
            model = self.models[i]
            model_name = model.display_name
            
            try:
                logger.debug(f"Trying {model_name} for extraction")
                
                if not self.rate_limiter.can_make_request(model_name):
                    wait_time = self.rate_limiter.get_wait_time(model_name)
                    logger.debug(f"Rate limit for {model_name}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                result = await self._extract_with_retry(model, content, schema)
                
                if result:
                    logger.info(f"Successfully extracted with {model_name}")
                    self.current_model_index = i
                    self.fallback_count = 0
                    self.stats['model_usage'][model_name] += 1
                    self.rate_limiter.record_request(model_name)
                    return result
                else:
                    logger.warning(f"{model_name} returned empty result")
                    continue
                    
            except Exception as e:
                logger.warning(f"{model_name} failed: {e}")
                self.fallback_count += 1
                self.stats['fallback_used'] += 1
                
                if self.fallback_count >= len(self.models):
                    logger.error("All LLM models failed, resetting fallback chain")
                    self.fallback_count = 0
                    self.current_model_index = 0
                
                continue
        
        logger.error("All LLM models failed to extract data")
        return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True
    )
    async def _extract_with_retry(
        self,
        model: Any,
        content: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        
        result = await model.extract(content, schema)
        
        if result and self._validate_schema(result, schema):
            return result
        
        return None
    
    def _validate_schema(self, data: Dict, schema: Dict) -> bool:
        
        required_fields = schema.get('required', [])
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def _schema_complete(self, data: Dict, schema: Dict) -> bool:

        required_fields = schema.get('required', [])
        if not required_fields:
            return True
        
        found_fields = sum(1 for field in required_fields if field in data)
        
        return found_fields / len(required_fields) >= 0.8
    
    def get_stats(self) -> Dict:
        
        return self.stats
    
    def reset_stats(self):
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallback_used': 0,
            'model_usage': {}
        }
        for model in self.models:
            self.stats['model_usage'][model.display_name] = 0
