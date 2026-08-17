# src/llm/models/groq.py
"""
Groq API integration for LLM extraction (Llama models)
"""

import os
import json
from typing import Dict, Any, Optional
from loguru import logger
from groq import Groq

from src.config import Config

class GroqExtractor:
    """
    Groq API extractor with Llama models
    """
    
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment")
        
        # Initialize Groq client
        self.client = Groq(api_key=self.api_key)
        self.model_name = "llama-3.1-8b-instant"
        self.display_name = "Groq Llama 3.1"  # ADD THIS
        
        logger.info(f"Initialized {self.display_name}")
    
    async def extract(self, content: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from content using Groq
        
        Args:
            content: Text content to extract from
            schema: Expected JSON schema
        
        Returns:
            Extracted structured data or None
        """
        try:
            # Build prompt with schema
            prompt = self._build_prompt(content, schema)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            if not response or not response.choices:
                logger.warning(f"{self.display_name} returned empty response")
                return None
            
            result_text = response.choices[0].message.content
            
            # Parse JSON response
            result = self._parse_response(result_text)
            
            if result:
                logger.debug(f"{self.display_name} extraction successful")
                return result
            else:
                logger.warning(f"{self.display_name} returned invalid JSON")
                return None
                
        except Exception as e:
            logger.error(f"{self.display_name} error: {e}")
            return None
    
    def _build_prompt(self, content: str, schema: Dict[str, Any]) -> str:
        """
        Build extraction prompt with schema
        
        Args:
            content: Text content
            schema: Expected JSON schema
        
        Returns:
            Prompt string
        """
        # Convert schema to JSON for prompt
        schema_json = json.dumps(schema, indent=2)
        
        # Truncate content if too long (Groq has smaller context window)
        max_content = 6000  # Groq context window limit
        truncated_content = content[:max_content]
        
        prompt = f"""
Extract the following information from the text and return ONLY valid JSON.

Schema:
{schema_json}

Text:
{truncated_content}

Return ONLY valid JSON. No explanations. No markdown.
"""
        return prompt
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse Groq response to JSON
        
        Args:
            response: Groq response text
        
        Returns:
            Parsed JSON or None
        """
        try:
            # Clean response
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse error: {e}")
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return None