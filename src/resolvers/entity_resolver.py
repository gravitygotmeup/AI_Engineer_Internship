import re
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
from loguru import logger
import pandas as pd

from src.config import Config

class EntityResolver:
    
    def __init__(self, seed_file: Optional[str] = None):
      
        self.seed_entities = []
        self.canonical_map = {}
        self.mapping_log = []
        self.fuzzy_threshold = 85
        
        
        if seed_file:
            self._load_seed_entities(seed_file)
        else:
            
            self._load_default_seeds()
        
        for entity in self.seed_entities:
            normalized = self.normalize(entity)
            self.canonical_map[normalized] = entity
        
        logger.info(f"Loaded {len(self.seed_entities)} seed entities for resolution")
    
    def _load_default_seeds(self):
        
        self.seed_entities = [
            # AI Research
            "OpenAI", "Anthropic", "DeepMind", "Google AI", "Meta AI",
            "Microsoft Research", "Amazon AI", "IBM Research",
            
            # LLM Companies
            "Cohere", "Mistral AI", "AI21 Labs", "Writer", "Adept AI",
            "Imbue", "Hugging Face", "Stability AI", "Runway",
            
            # AI Infrastructure
            "NVIDIA", "AMD", "Intel", "Graphcore", "Cerebras",
            "SambaNova", "Groq", "Tenstorrent", "SiFive",
            
            # AI Applications
            "Jasper", "Copy.ai", "Midjourney", "DALL-E", "Stable Diffusion",
            "ElevenLabs", "Synthesia", "Descript", "Otter.ai",
            
            # AI Data & Labeling
            "Scale AI", "Labelbox", "Snorkel AI", "Hive", "Appen",
            
            # AI Safety
            "Alignment Research Center", "Conjecture", "EleutherAI",
            
            # Enterprise AI
            "C3.ai", "DataRobot", "H2O.ai", "Kore.ai", "Observe.ai",
            "Moveworks", "Avaamo", "Gupshup", "Yellow.ai",
            
            # Computer Vision
            "Clarifai", "Sighthound", "AnyVision", "Megvii", "SenseTime",
            
            # NLP
            "NLP Cloud", "Aylien", "Lexalytics", "MonkeyLearn",
            
            # AI in Healthcare
            "Insilico Medicine", "Recursion", "Tempus", "Exscientia",
            
            # AI in Finance
            "Kavout", "Kensho", "Sentieo", "AlphaSense",
            
            # Others
            "Bard", "Claude", "ChatGPT", "Copilot", "Perplexity AI",
            "Notion AI", "Glean", "Sana", "Zapier AI", "Automate.io"
        ]
    
    def _load_seed_entities(self, file_path: str):
        
        try:
            df = pd.read_csv(file_path)
            if 'canonical_name' in df.columns:
                self.seed_entities = df['canonical_name'].tolist()
            else:
                logger.warning(f"No 'canonical_name' column in {file_path}")
                self._load_default_seeds()
        except Exception as e:
            logger.error(f"Error loading seed file: {e}")
            self._load_default_seeds()
    
    def normalize(self, name: str) -> str:
       
        if not name:
            return ''
        
        name = str(name).strip()
        
        suffixes = [
            r',?\s+(Inc|Corp|Corporation|LLC|Ltd|Limited|Co|Company|Group|Holdings|Labs|Technologies?)\.?$',
            r',?\s+[A-Z]\.?[A-Z]\.?$' 
        ]
        
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        
        name = re.sub(r'[^\w\s\.]', '', name)
        
        name = re.sub(r'\s+', ' ', name).strip()
        
        name = name.lower()
        
        return name
    
    def resolve(self, raw_name: str) -> Dict[str, any]:
        
        if not raw_name:
            return {
                'raw': '',
                'canonical': '',
                'confidence': 0.0,
                'method': 'empty'
            }
        
        normalized = self.normalize(raw_name)
        
        if normalized in self.canonical_map:
            canonical = self.canonical_map[normalized]
            result = {
                'raw': raw_name,
                'canonical': canonical,
                'confidence': 1.0,
                'method': 'exact'
            }
            self._log_mapping(result)
            return result
        
        best_match = None
        best_score = 0
        best_normalized = None
        
        for normalized_seed, canonical in self.canonical_map.items():

            score1 = fuzz.ratio(normalized, normalized_seed)
            score2 = fuzz.partial_ratio(normalized, normalized_seed)
            score3 = fuzz.token_sort_ratio(normalized, normalized_seed)
            
            score = max(score1, score2, score3)
            
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = canonical
                best_normalized = normalized_seed
        
        if best_match:
            result = {
                'raw': raw_name,
                'canonical': best_match,
                'confidence': best_score / 100.0,
                'method': 'fuzzy'
            }
            self._log_mapping(result)
            
            self.canonical_map[normalized] = best_match
            return result
        
        result = {
            'raw': raw_name,
            'canonical': raw_name, 
            'confidence': 0.5,
            'method': 'new_entity'
        }
        self._log_mapping(result)
        
        self.canonical_map[normalized] = raw_name
        self.seed_entities.append(raw_name)
        
        return result
    
    def resolve_batch(self, names: List[str]) -> List[Dict]:
        return [self.resolve(name) for name in names]
    
    def _log_mapping(self, result: Dict):
        
        self.mapping_log.append(result)
        
        if result.get('method') != 'empty':
            logger.debug(
                f"Mapped: '{result['raw']}' -> '{result['canonical']}' "
                f"(confidence: {result['confidence']:.2f}, method: {result['method']})"
            )
    
    def get_mapping_log(self) -> List[Dict]:
        
        return self.mapping_log
    
    def export_mapping_log(self, file_path: str):
        
        if not self.mapping_log:
            logger.warning("No mapping logs to export")
            return
        
        try:
            df = pd.DataFrame(self.mapping_log)
            df.to_csv(file_path, index=False)
            logger.info(f"Exported {len(self.mapping_log)} mappings to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting mapping log: {e}")