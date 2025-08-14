import re
from typing import List, Dict, Any, Optional
import logging

from ..interfaces import SearchProvider, SearchResult, PartDetails, RepairGuide, BlogPost, DataProvider

logger = logging.getLogger(__name__)

class SimpleSearchProvider(SearchProvider):
    # basic keyword search 
    
    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider
        self.parts_data = []
        self.repairs_data = []
        self._initialized = False
    
    async def initialize(self):
        # load data from the provider
        if not self._initialized:
            self.parts_data = await self.data_provider.get_parts_data()
            self.repairs_data = await self.data_provider.get_repairs_data()
            self._initialized = True
            logger.info(f"simple search ready with {len(self.parts_data)} parts, {len(self.repairs_data)} repairs")
    
    def _normalize_text(self, text: str) -> str:
        # clean up text for better matching
        if not text:
            return ""
        
        # convert to lowercase and clean up whitespace
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        
        # remove special chars but keep letters, numbers, spaces
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        
        # handle common synonyms
        synonyms = {
            'fridge': 'refrigerator',
            'icebox': 'refrigerator',
            'cooler': 'refrigerator',
            'dish washer': 'dishwasher',
            'dishwashing machine': 'dishwasher',
            'freezer': 'refrigerator freezer',
            'ice maker': 'icemaker',
            'water filter': 'filter water',
            'not cooling': 'not cold warm',
            'not working': 'broken defective',
            'wont start': 'not starting broken',
            'leaking': 'leak water drip',
            'noisy': 'loud noise sound',
            'door seal': 'gasket door',
            'handle': 'door handle',
        }
        
        for synonym, replacement in synonyms.items():
            normalized = normalized.replace(synonym, replacement)
        
        return normalized
    
    def _calculate_relevance(self, query: str, text_fields: List[str]) -> float:
        """Calculate simple relevance score based on keyword matches"""
        if not query or not text_fields:
            return 0.0
        
        query_words = set(self._normalize_text(query).split())
        if not query_words:
            return 0.0
        
        # Combine all text fields
        combined_text = " ".join([str(field) for field in text_fields if field])
        normalized_text = self._normalize_text(combined_text)
        text_words = set(normalized_text.split())
        
        if not text_words:
            return 0.0
        
        # Calculate match ratio
        matches = len(query_words.intersection(text_words))
        score = matches / len(query_words)
        
        # Bonus for exact phrase matches
        if query.lower() in combined_text.lower():
            score += 0.3
        
        # Bonus for part number matches
        if any(word.upper().startswith('PS') or word.upper().startswith('W') for word in query_words):
            for field in text_fields:
                if field and query.upper() in str(field).upper():
                    score += 0.5
        
        return min(score, 1.0)
    
    async def search_parts(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> List[SearchResult]:
        """Search parts using keyword matching"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        results = []
        query_normalized = self._normalize_text(query)
        
        logger.info(f"Searching parts for: '{query}' (normalized: '{query_normalized}')")
        
        for part in self.parts_data:
            # Text fields to search in (using correct CSV column names)
            text_fields = [
                part.get('part_name', ''),
                part.get('symptoms', ''),  # CSV has symptoms field
                part.get('brand', ''),
                part.get('appliance_types', ''),  # CSV uses appliance_types
                part.get('part_id', ''),  # CSV uses part_id as part number
                part.get('mpn_id', ''),   # CSV uses mpn_id as manufacturer number
                part.get('replace_parts', '')  # CSV has replace_parts field
            ]
            
            # Calculate relevance
            relevance = self._calculate_relevance(query, text_fields)
            
            if relevance > 0:
                # Apply filters if provided
                if filters:
                    if filters.get('brand') and part.get('brand', '').lower() != filters['brand'].lower():
                        continue
                    if filters.get('category') and part.get('category', '').lower() != filters['category'].lower():
                        continue
                
                # Create search result
                result = SearchResult(
                    id=part.get('part_id', '') or str(len(results)),
                    name=part.get('part_name', 'Unknown Part'),
                    part_number=part.get('part_id', ''),  # CSV uses part_id as the part number
                    manufacturer_number=part.get('mpn_id', ''),  # CSV uses mpn_id for manufacturer part number
                    price=part.get('part_price', ''),
                    brand=part.get('brand', ''),
                    category=part.get('appliance_types', ''),
                    description=part.get('symptoms', ''),  # Use symptoms as description for now
                    url=part.get('product_url', ''),
                    image_url=part.get('image_url', ''),
                    stock_status=part.get('availability', 'Unknown'),
                    relevance_score=relevance,
                    source="simple_search",
                    # Additional PartSelect fields
                    install_difficulty=part.get('install_difficulty', ''),
                    install_time=part.get('install_time', ''),
                    symptoms=part.get('symptoms', ''),
                    appliance_types=part.get('appliance_types', ''),
                    replace_parts=part.get('replace_parts', ''),
                    install_video_url=part.get('install_video_url', '')
                )
                results.append(result)
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Found {len(results)} parts, returning top {min(limit, len(results))}")
        return results[:limit]
    
    async def get_part_details(self, part_id: str) -> Optional[PartDetails]:
        """Get detailed information for a specific part"""
        await self.initialize()
        
        # Find part by ID, part number, or manufacturer number
        for part in self.parts_data:
            if (part.get('part_id') == part_id or 
                part.get('partselect_number') == part_id or
                part.get('manufacturer_number') == part_id):
                
                return PartDetails(
                    id=part.get('part_id', '') or part.get('partselect_number', ''),
                    name=part.get('part_name', 'Unknown Part'),
                    part_number=part.get('partselect_number', ''),
                    manufacturer_number=part.get('manufacturer_number', ''),
                    price=part.get('part_price', '') or part.get('price', ''),
                    brand=part.get('brand', ''),
                    category=part.get('appliance_types', '') or part.get('category', ''),
                    description=part.get('description', ''),
                    url=part.get('product_url', '') or part.get('url', ''),
                    image_url=part.get('image_url', ''),
                    stock_status=part.get('availability', '') or part.get('stock_status', 'Unknown'),
                    rating=part.get('rating', ''),
                    reviews_count=part.get('reviews_count', 0) if part.get('reviews_count') else 0,
                    specifications=part,  # Include all original data
                )
        
        return None
    
    async def search_repairs(self, query: str, appliance_type: str = None, limit: int = 5) -> List[RepairGuide]:
        """Search repair guides using keyword matching"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        results = []
        query_normalized = self._normalize_text(query)
        
        logger.info(f"Searching repairs for: '{query}' (appliance: {appliance_type})")
        
        for repair in self.repairs_data:
            # Text fields to search in
            text_fields = [
                repair.get('symptom', ''),
                repair.get('description', ''),
                repair.get('parts', ''),
                repair.get('Product', ''),
            ]
            
            # Calculate relevance
            relevance = self._calculate_relevance(query, text_fields)
            
            if relevance > 0:
                # Apply appliance type filter
                if appliance_type:
                    product_type = repair.get('Product', '').lower()
                    if appliance_type.lower() not in product_type:
                        continue
                
                # Create repair guide result
                result = RepairGuide(
                    id=f"repair_{len(results)}",
                    title=repair.get('symptom', 'Unknown Issue'),
                    appliance_type=repair.get('Product', 'Unknown'),
                    symptom=repair.get('symptom', ''),
                    difficulty=repair.get('difficulty', 'Unknown'),
                    estimated_time=repair.get('percentage', ''),  # Using percentage as time estimate
                    parts_needed=repair.get('parts', '').split(', ') if repair.get('parts') else [],
                    steps=repair.get('description', ''),
                    url=repair.get('symptom_detail_url', '')
                )
                results.append((result, relevance))
        
        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Found {len(results)} repair guides, returning top {min(limit, len(results))}")
        return [result[0] for result in results[:limit]]
    
    async def check_compatibility(self, part_id: str, model_number: str) -> Dict[str, Any]:
        """Simple compatibility check based on brand matching"""
        await self.initialize()
        
        part_details = await self.get_part_details(part_id)
        if not part_details:
            return {
                "compatible": False,
                "confidence": 0.0,
                "reason": f"Part {part_id} not found"
            }
        
        # Simple heuristic: if the part brand matches common brands for the model prefix
        model_upper = model_number.upper()
        part_brand = part_details.brand.upper() if part_details.brand else ""
        
        # Common model prefixes and their brands
        brand_prefixes = {
            'WDT': 'WHIRLPOOL',
            'GE': 'GE', 
            'LG': 'LG',
            'SAMSUNG': 'SAMSUNG',
            'FRIGIDAIRE': 'FRIGIDAIRE',
            'BOSCH': 'BOSCH'
        }
        
        expected_brand = None
        for prefix, brand in brand_prefixes.items():
            if model_upper.startswith(prefix):
                expected_brand = brand
                break
        
        if expected_brand and part_brand == expected_brand:
            return {
                "compatible": True,
                "confidence": 0.8,
                "reason": f"Brand match: {part_brand} part for {expected_brand} model"
            }
        elif expected_brand:
            return {
                "compatible": False,
                "confidence": 0.6,
                "reason": f"Brand mismatch: {part_brand} part for {expected_brand} model"
            }
        else:
            return {
                "compatible": True,  # Default to compatible if uncertain
                "confidence": 0.3,
                "reason": "Unable to determine compatibility, please verify manually"
            }
    
    async def search_blogs(self, query: str, limit: int = 3) -> List[BlogPost]:
        """Search blog posts using keyword matching"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        results = []
        query_normalized = self._normalize_text(query)
        
        logger.info(f"Searching blogs for: '{query}'")
        
        for blog in self.blogs_data:
            # Text fields to search in
            text_fields = [
                blog.get('title', ''),
                blog.get('description', ''),
                blog.get('content', ''),
                blog.get('tags', ''),
            ]
            
            # Calculate relevance
            relevance = self._calculate_relevance(query, text_fields)
            
            if relevance > 0:
                # Create blog post result
                result = BlogPost(
                    id=f"blog_{len(results)}",
                    title=blog.get('title', 'Untitled Article'),
                    url=blog.get('url', ''),
                    description=blog.get('description', '')[:200] + "..." if len(blog.get('description', '')) > 200 else blog.get('description', ''),
                    relevance_score=relevance
                )
                results.append((result, relevance))
        
        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Found {len(results)} blogs, returning top {min(limit, len(results))}")
        return [result[0] for result in results[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get search provider statistics"""
        return {
            "provider_type": "simple_search",
            "parts_indexed": len(self.parts_data),
            "repairs_indexed": len(self.repairs_data),
            "blogs_indexed": len(self.blogs_data),
            "initialized": self._initialized
        }
