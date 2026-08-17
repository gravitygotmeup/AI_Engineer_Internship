import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from loguru import logger

class RateLimiter:
    
    def __init__(self):
        self.model_limits = {
            'Gemini Flash': 60,      
            'Groq Llama 3.1': 30,    
            'DeepSeek': 100,        
        }
        
        self.global_limit = 200
        
        self.buckets = {}
        self.last_request_time = defaultdict(float)
        self.request_counts = defaultdict(int)
        self.global_request_count = 0
        self.global_window_start = time.time()
        
        for model in self.model_limits:
            self.buckets[model] = self.model_limits[model]
        
        logger.info(f"Rate limiter initialized with limits: {self.model_limits}")
    
    def can_make_request(self, model_name: Optional[str] = None) -> bool:
        
        current_time = time.time()
        
        if current_time - self.global_window_start > 60:
            
            self.global_request_count = 0
            self.global_window_start = current_time
        
        if self.global_request_count >= self.global_limit:
            logger.debug(f"Global rate limit reached: {self.global_request_count}/{self.global_limit}")
            return False
        
        if model_name and model_name in self.model_limits:
            
            if current_time - self.last_request_time[model_name] > 60:
                self.request_counts[model_name] = 0
                self.buckets[model_name] = self.model_limits[model_name]
            
            if self.request_counts[model_name] >= self.model_limits[model_name]:
                logger.debug(f"Model {model_name} rate limit reached: {self.request_counts[model_name]}/{self.model_limits[model_name]}")
                return False
        
        return True
    
    def record_request(self, model_name: Optional[str] = None):
        
        current_time = time.time()
        
        self.global_request_count += 1
        
        if model_name and model_name in self.model_limits:
            if current_time - self.last_request_time[model_name] > 60:
                self.request_counts[model_name] = 0
            self.request_counts[model_name] += 1
            self.last_request_time[model_name] = current_time
            self.buckets[model_name] = max(0, self.buckets[model_name] - 1)
    
    def get_wait_time(self, model_name: Optional[str] = None) -> float:
        
        current_time = time.time()
        wait_times = []
        
        if self.global_request_count >= self.global_limit:
            time_since_start = current_time - self.global_window_start
            if time_since_start < 60:
                wait_times.append(60 - time_since_start + 0.5)
        
        if model_name and model_name in self.model_limits:
            if self.request_counts[model_name] >= self.model_limits[model_name]:
                time_since_last = current_time - self.last_request_time[model_name]
                if time_since_last < 60:
                    wait_times.append(60 - time_since_last + 0.5)
        
        if wait_times:
            wait_time = max(wait_times)
            jitter = wait_time * (0.1 + 0.1 * (time.time() % 1))
            return wait_time + jitter
        
        return 0
    
    def get_remaining_capacity(self, model_name: Optional[str] = None) -> int:
        
        if model_name and model_name in self.model_limits:
            return max(0, self.model_limits[model_name] - self.request_counts[model_name])
        return max(0, self.global_limit - self.global_request_count)
    
    def reset(self):
        current_time = time.time()
        self.request_counts = defaultdict(int)
        self.last_request_time = defaultdict(float)
        self.global_request_count = 0
        self.global_window_start = current_time
        
        for model in self.model_limits:
            self.buckets[model] = self.model_limits[model]
        
        logger.info("Rate limiter reset")

