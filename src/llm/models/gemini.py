# src/llm/models/gemini.py
"""
Gemini API integration for LLM extraction
"""

import os
import json
from typing import Dict, Any, Optional
from loguru import logger
import google.generativeai as genai

from src.config import Config

class GeminiExtractor:
    """
    Gemini API extractor with retry logic
    """
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment")
        
        # Initialize Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-3.1-flash-lite')
        self.model_name = "gemini-1.5-flash"
        self.display_name = "Gemini Flash"  # ADD THIS
        
        logger.info(f"Initialized {self.display_name}")
    
    async def extract(self, content: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from content using Gemini
        
        Args:
            content: Text content to extract from
            schema: Expected JSON schema
        
        Returns:
            Extracted structured data or None
        """
        try:
            # Build prompt with schema
            prompt = self._build_prompt(content, schema)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.warning(f"{self.display_name} returned empty response")
                return None
            
            # Parse JSON response
            result = self._parse_response(response.text)
            
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
        
        prompt = f"""
You are a data extraction expert. Extract the following information from the text and return ONLY valid JSON.

Extraction Schema:
{schema_json}

Text to extract from:
{content[:8000]}  # Gemini has large context window

Return ONLY valid JSON matching the schema. Do not include any other text or explanations.
"""
        return prompt
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse Gemini response to JSON
        
        Args:
            response: Gemini response text
        
        Returns:
            Parsed JSON or None
        """
        try:
            # Clean response (remove markdown code blocks if present)
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
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return None