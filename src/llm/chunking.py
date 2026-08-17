import re
from typing import List, Optional
from loguru import logger

class IntelligentChunker:

    def __init__(
        self,
        max_tokens: int = 8000,
        overlap_tokens: int = 200,
        min_chunk_size: int = 100
    ):
        
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_size = min_chunk_size
        
        self.max_chars = max_tokens * 4
        self.overlap_chars = overlap_tokens * 4
        
        logger.debug(f"Chunker initialized: max_tokens={max_tokens}, overlap={overlap_tokens}")
    
    def chunk_content(self, content: str) -> List[str]:
        
        if not content:
            return []
        
        if len(content) <= self.max_chars:
            return [content]
        
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if para_size > self.max_chars:
            
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                sub_chunks = self._split_paragraph(para)
                chunks.extend(sub_chunks)
                continue
            
            if current_size + para_size > self.max_chars:
                
                chunks.append('\n\n'.join(current_chunk))
                
                overlap = self._get_overlap('\n\n'.join(current_chunk))
                current_chunk = [overlap] if overlap else []
                current_size = len(overlap) if overlap else 0
            
            current_chunk.append(para)
            current_size += para_size + 2  
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        chunks = [c for c in chunks if len(c) >= self.min_chunk_size]
        
        logger.debug(f"Split content into {len(chunks)} chunks")
        return chunks
    
    def _split_paragraph(self, paragraph: str) -> List[str]:
        
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chars:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    
                    overlap = self._get_overlap(' '.join(current_chunk))
                    current_chunk = [overlap] if overlap else []
                    current_size = len(overlap) if overlap else 0
            
            current_chunk.append(sentence)
            current_size += sentence_size + 1  
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _get_overlap(self, previous_chunk: str) -> str:
        if not previous_chunk or len(previous_chunk) <= self.overlap_chars:
            return ''
        
        sentences = re.split(r'(?<=[.!?])\s+', previous_chunk)
        overlap = []
        size = 0
        
        for sentence in reversed(sentences):
            if size + len(sentence) > self.overlap_chars:
                break
            overlap.insert(0, sentence)
            size += len(sentence) + 1
        
        return ' '.join(overlap) if overlap else ''