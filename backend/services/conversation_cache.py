"""
Conversation cache for fast responses
Keeps common queries cached so we dont hit the LLM every time
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CachedResponse:
    # what we store in the cache
    response: str
    parts: List[Dict[str, Any]]
    repairs: List[Dict[str, Any]]
    blogs: List[Dict[str, Any]]
    confidence: float
    timestamp: datetime
    hit_count: int = 0

class HighPerformanceConversationCache:
    # cache for conversation responses saves time on repeated queries
    
    def __init__(self, max_cache_size: int = 5000):  # bigger cache = more hits
        self.max_cache_size = max_cache_size
        self.response_cache: Dict[str, CachedResponse] = {}
        
        # track performance stats
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_queries = 0
        
        # prepopulate with common customer service patterns
        self._warm_cache()
        
        logger.info(f"Cache initialized with {len(self.response_cache)} entries")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better cache hits"""
        normalized = query.lower().strip()
        
        # replace common variations
        replacements = {
            'refrigerator': 'fridge',
            'dish washer': 'dishwasher',
            'ice maker': 'icemaker',
            'not working': 'broken',
            'wont start': 'not starting',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _generate_cache_key(self, query: str, conversation_id: Optional[str] = None) -> str:
        """Generate cache key"""
        normalized_query = self._normalize_query(query)
        combined_key = f"{normalized_query}_{conversation_id or 'default'}"
        return hashlib.md5(combined_key.encode()).hexdigest()
    
    def _warm_cache(self):
        """Prepopulate cache with common customer service responses"""
        common_patterns = {
            "fridge not cooling": {
                "response": "I can help diagnose your cooling issue This is usually caused by a few common problems Let me ask you some questions 1 Is the compressor running do you hear humming 2 Are the vents inside blocked by food 3 When did you last clean the condenser coils Based on your answers well likely need to look at the evaporator fan condenser coils or thermostat",
                "confidence": 0.9
            },
            "ice maker broken": {
                "response": "Ice maker problems are very common Let me help you troubleshoot 1 Is the ice maker getting power any lights or sounds 2 Is there water going to the refrigerator 3 Are you seeing any error codes 4 When did it last make ice Most ice maker issues are either water supply problems a faulty water inlet valve or the ice maker assembly itself needs replacement",
                "confidence": 0.9
            },
            "dishwasher not cleaning": {
                "response": "Poor cleaning is frustrating Lets diagnose this step by step 1 Are the spray arms spinning freely check for clogs 2 Hows your water temperature should be 120F 3 Are you using rinse aid 4 When did you last clean the filter at the bottom Most cleaning issues come from clogged spray arms dirty filters or a worn wash pump motor",
                "confidence": 0.9
            },
            "water leaking": {
                "response": "Water leaks need immediate attention Let me help you find the source 1 Where exactly is the water coming from 2 Is it constant or only during cycles 3 Check door seals and connections Most leaks are from worn door gaskets loose hose connections or damaged water inlet valves",
                "confidence": 0.9
            },
            "loud noise": {
                "response": "Unusual noises can indicate several issues Let me help 1 When does the noise occur startup during cycle draining 2 What type of sound grinding squealing banging 3 Your model number Common causes are worn bearings loose parts or objects stuck in the drain pump",
                "confidence": 0.9
            },
        }
        
        for query, response_data in common_patterns.items():
            cache_key = self._generate_cache_key(query)
            self.response_cache[cache_key] = CachedResponse(
                response=response_data["response"],
                parts=[],
                repairs=[],
                blogs=[],
                confidence=response_data["confidence"],
                timestamp=datetime.now()
            )
    
    def get_cached_response(self, query: str, conversation_id: Optional[str] = None) -> Optional[CachedResponse]:
        """Get cached response if available"""
        self.total_queries += 1
        cache_key = self._generate_cache_key(query, conversation_id)
        
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            cached.hit_count += 1
            self.cache_hits += 1
            
            logger.info(f"Cache HIT for query '{query[:50]}' hit #{cached.hit_count}")
            return cached
        
        self.cache_misses += 1
        return None
    
    def cache_response(self, query: str, response: str, parts: List[Dict], repairs: List[Dict], 
                      blogs: List[Dict], confidence: float, conversation_id: Optional[str] = None):
        """Cache a new response"""
        cache_key = self._generate_cache_key(query, conversation_id)
        
        cached_response = CachedResponse(
            response=response,
            parts=parts or [],
            repairs=repairs or [],
            blogs=blogs or [],
            confidence=confidence,
            timestamp=datetime.now()
        )
        
        self.response_cache[cache_key] = cached_response
    
    def clear_cache(self):
        """Clear all cached responses useful for testing new prompts"""
        self.response_cache.clear()
        logger.info("Cache cleared all cached responses removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        hit_rate = (self.cache_hits / self.total_queries * 100) if self.total_queries > 0 else 0
        
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_responses": len(self.response_cache),
        }

# global cache instance
conversation_cache = HighPerformanceConversationCache()
