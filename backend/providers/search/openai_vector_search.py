import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional
import numpy as np
import pickle
from pathlib import Path

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..interfaces import SearchProvider, SearchResult, PartDetails, RepairGuide, BlogPost, DataProvider

logger = logging.getLogger(__name__)

class OpenAIVectorSearchProvider(SearchProvider):
    """Simple vector search using OpenAI embeddings and cosine similarity"""
    
    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider
        self.openai_client = None
        self.parts_data = []
        self.repairs_data = []
        self.parts_embeddings = []
        self.repairs_embeddings = []
        self.parts_texts = []
        self.repairs_texts = []
        self._initialized = False
        
        # Cache directory for embeddings
        self.cache_dir = Path(__file__).parent.parent.parent / "vector_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for vector search")
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        
        self.openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI vector search provider initialized")
    
    def _create_part_text(self, part: Dict[str, Any]) -> str:
        """Create searchable text from part data"""
        fields = [
            part.get('part_name', ''),
            part.get('description', ''),
            part.get('brand', ''),
            part.get('appliance_types', ''),
            part.get('symptoms', ''),
            'appliance part repair'  # Context
        ]
        
        # Clean and combine
        cleaned_fields = [str(field).strip() for field in fields if field and str(field).strip()]
        return " ".join(cleaned_fields)
    
    def _create_repair_text(self, repair: Dict[str, Any]) -> str:
        """Create searchable text from repair data"""
        fields = [
            repair.get('symptom', ''),
            repair.get('description', ''),
            repair.get('parts', ''),
            repair.get('Product', ''),
            'repair troubleshooting guide'  # Context
        ]
        
        # Clean and combine
        cleaned_fields = [str(field).strip() for field in fields if field and str(field).strip()]
        return " ".join(cleaned_fields)
    
    async def _generate_embeddings(self, texts: List[str], cache_key: str) -> List[List[float]]:
        """Generate embeddings with caching"""
        cache_file = self.cache_dir / f"{cache_key}_embeddings.pkl"
        
        # Try to load from cache
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if len(cached_data) == len(texts):
                        logger.info(f"Loaded {len(cached_data)} embeddings from cache: {cache_key}")
                        return cached_data
            except Exception as e:
                logger.warning(f"Failed to load embeddings cache: {e}")
        
        # Generate new embeddings
        logger.info(f"Generating {len(texts)} embeddings for {cache_key}...")
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            try:
                response = await self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
                # Small delay to be nice to the API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {e}")
                # Create zero embeddings as fallback
                zero_embedding = [0.0] * 1536  # Ada-002 dimension
                embeddings.extend([zero_embedding] * len(batch))
        
        # Cache the results
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embeddings, f)
            logger.info(f"Cached {len(embeddings)} embeddings to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache embeddings: {e}")
        
        return embeddings
    
    async def initialize(self):
        """Initialize vector search with FAISS indexes"""
        if self._initialized:
            return
        
        logger.info("Initializing OpenAI vector search...")
        
        # Try to load FAISS indexes first
        vector_dir = Path(__file__).parent.parent.parent / "vector_stores"
        
        if self._load_faiss_indexes(vector_dir):
            logger.info("✅ Loaded FAISS indexes successfully")
        else:
            logger.info("📋 FAISS indexes not found, falling back to embedding generation")
            await self._initialize_with_embeddings()
        
        self._initialized = True
    
    def _load_faiss_indexes(self, vector_dir: Path) -> bool:
        """Load pre-computed FAISS indexes"""
        try:
            import faiss
            import pickle
            
            # Load parts index
            parts_dir = vector_dir / "parts"
            if (parts_dir / "index.faiss").exists() and (parts_dir / "metadata.pkl").exists():
                self.parts_index = faiss.read_index(str(parts_dir / "index.faiss"))
                with open(parts_dir / "metadata.pkl", 'rb') as f:
                    self.parts_data = pickle.load(f)
                logger.info(f"   Parts FAISS index: {self.parts_index.ntotal} vectors")
            else:
                logger.warning("Parts FAISS index not found")
                return False
            
            # Load repairs index
            repairs_dir = vector_dir / "repairs"
            if (repairs_dir / "index.faiss").exists() and (repairs_dir / "metadata.pkl").exists():
                self.repairs_index = faiss.read_index(str(repairs_dir / "index.faiss"))
                with open(repairs_dir / "metadata.pkl", 'rb') as f:
                    self.repairs_data = pickle.load(f)
                logger.info(f"   Repairs FAISS index: {self.repairs_index.ntotal} vectors")
            else:
                logger.warning("Repairs FAISS index not found")
                self.repairs_index = None
                self.repairs_data = []
            
            # Load blogs index (optional)
            blogs_dir = vector_dir / "blogs"
            if (blogs_dir / "index.faiss").exists() and (blogs_dir / "metadata.pkl").exists():
                self.blogs_index = faiss.read_index(str(blogs_dir / "index.faiss"))
                with open(blogs_dir / "metadata.pkl", 'rb') as f:
                    self.blogs_data = pickle.load(f)
                logger.info(f"   Blogs FAISS index: {self.blogs_index.ntotal} vectors")
            else:
                self.blogs_index = None
                self.blogs_data = []
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS indexes: {e}")
            return False
    
    async def _initialize_with_embeddings(self):
        """Fallback: initialize with embedding generation"""
        # Load data from provider
        self.parts_data = await self.data_provider.get_parts_data()
        self.repairs_data = await self.data_provider.get_repairs_data()
        
        logger.info(f"Loaded {len(self.parts_data)} parts and {len(self.repairs_data)} repairs")
        
        # Create searchable texts
        self.parts_texts = [self._create_part_text(part) for part in self.parts_data]
        self.repairs_texts = [self._create_repair_text(repair) for repair in self.repairs_data]
        
        # Generate embeddings (with caching)
        if self.parts_texts:
            self.parts_embeddings = await self._generate_embeddings(self.parts_texts, "parts")
        
        if self.repairs_texts:
            self.repairs_embeddings = await self._generate_embeddings(self.repairs_texts, "repairs")
        
        logger.info(f"   Parts embeddings: {len(self.parts_embeddings)}")
        logger.info(f"   Repairs embeddings: {len(self.repairs_embeddings)}")
    
    async def _faiss_search_parts(self, query: str, limit: int) -> List[tuple]:
        """Search parts using FAISS index"""
        try:
            # Generate query embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
            
            # Normalize query embedding
            import faiss
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            similarities, indices = self.parts_index.search(query_embedding, limit)
            
            # Convert results to (part_data, similarity) tuples
            results = []
            logger.info(f"Raw FAISS results: similarities={similarities[0][:5]}, indices={indices[0][:5]}")
            
            for similarity, idx in zip(similarities[0], indices[0]):
                if idx >= 0 and similarity > 0.01:  # Lowered threshold from 0.1 to 0.01
                    part_data = self.parts_data[idx]
                    results.append((part_data, float(similarity)))
                    logger.debug(f"  Part match: {part_data.get('part_name', 'Unknown')} (similarity: {similarity:.3f})")
            
            logger.info(f"FAISS search found {len(results)} parts (threshold: 0.01)")
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS parts search: {e}")
            return []
    
    async def _faiss_search_repairs(self, query: str, limit: int) -> List[tuple]:
        """Search repairs using FAISS index"""
        try:
            # Generate query embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
            
            # Normalize query embedding
            import faiss
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            similarities, indices = self.repairs_index.search(query_embedding, limit)
            
            # Convert results to (repair_data, similarity) tuples
            results = []
            logger.info(f"Raw FAISS repairs results: similarities={similarities[0][:5]}, indices={indices[0][:5]}")
            
            for similarity, idx in zip(similarities[0], indices[0]):
                if idx >= 0 and similarity > 0.01:  # Lowered threshold from 0.1 to 0.01
                    repair_data = self.repairs_data[idx]
                    results.append((repair_data, float(similarity)))
                    logger.debug(f"  Repair match: {repair_data.get('title', 'Unknown')} (similarity: {similarity:.3f})")
            
            logger.info(f"FAISS repairs search found {len(results)} repairs (threshold: 0.01)")
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS repairs search: {e}")
            return []
    
    async def _vector_search(self, query: str, embeddings: List[List[float]], texts: List[str], data: List[Dict], limit: int) -> List[tuple]:
        """Perform vector similarity search"""
        if not embeddings or not query.strip():
            return []
        
        try:
            # Generate query embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            query_embedding = response.data[0].embedding
            
            # Calculate similarities (manual cosine similarity without scikit-learn)
            query_vec = np.array(query_embedding)
            embeddings_matrix = np.array(embeddings)
            
            # Manual cosine similarity calculation
            query_norm = np.linalg.norm(query_vec)
            doc_norms = np.linalg.norm(embeddings_matrix, axis=1)
            
            # Calculate dot product
            dot_products = np.dot(embeddings_matrix, query_vec)
            
            # Calculate cosine similarity
            similarities = dot_products / (query_norm * doc_norms + 1e-8)  # Add small epsilon to avoid division by zero
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:limit]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    results.append((data[idx], similarities[idx]))
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def search_parts(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> List[SearchResult]:
        """Search parts using vector similarity"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        logger.info(f"Vector searching parts for: '{query}'")
        
        # Use FAISS index if available, otherwise fallback to embeddings
        if hasattr(self, 'parts_index') and self.parts_index is not None:
            results = await self._faiss_search_parts(query, limit * 2)
        else:
            # Fallback to embedding-based search
            results = await self._vector_search(
                query, 
                getattr(self, 'parts_embeddings', []), 
                getattr(self, 'parts_texts', []), 
                self.parts_data, 
                limit * 2
            )
        
        search_results = []
        for part, similarity in results:
            # Apply filters if provided
            if filters:
                if filters.get('brand') and part.get('brand', '').lower() != filters['brand'].lower():
                    continue
                if filters.get('category') and part.get('category', '').lower() != filters['category'].lower():
                    continue
            
            # Create search result
            result = SearchResult(
                id=part.get('part_id', '') or part.get('partselect_number', '') or str(len(search_results)),
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
                relevance_score=float(similarity),
                source="vector_search"
            )
            search_results.append(result)
            
            if len(search_results) >= limit:
                break
        
        logger.info(f"Vector search found {len(search_results)} parts")
        return search_results
    
    async def get_part_details(self, part_id: str) -> Optional[PartDetails]:
        """Get detailed part information (same as simple search)"""
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
                    specifications=part,
                )
        
        return None
    
    async def search_repairs(self, query: str, appliance_type: str = None, limit: int = 5) -> List[RepairGuide]:
        """Search repair guides using vector similarity"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        logger.info(f"Vector searching repairs for: '{query}' (appliance: {appliance_type})")
        
        # Use FAISS index if available, otherwise fallback to embeddings
        if hasattr(self, 'repairs_index') and self.repairs_index is not None:
            results = await self._faiss_search_repairs(query, limit * 2)
        else:
            # Fallback to embedding-based search
            results = await self._vector_search(
                query, 
                getattr(self, 'repairs_embeddings', []), 
                getattr(self, 'repairs_texts', []), 
                self.repairs_data, 
                limit * 2
            )
        
        repair_results = []
        for repair, similarity in results:
            # Apply appliance type filter
            if appliance_type:
                product_type = repair.get('Product', '').lower()
                if appliance_type.lower() not in product_type:
                    continue
            
            # Create repair guide result
            result = RepairGuide(
                id=f"repair_{len(repair_results)}",
                title=repair.get('symptom', 'Unknown Issue'),
                appliance_type=repair.get('Product', 'Unknown'),
                symptom=repair.get('symptom', ''),
                difficulty=repair.get('difficulty', 'Unknown'),
                estimated_time=repair.get('percentage', ''),
                parts_needed=repair.get('parts', '').split(', ') if repair.get('parts') else [],
                steps=repair.get('description', ''),
                url=repair.get('symptom_detail_url', '')
            )
            repair_results.append(result)
            
            if len(repair_results) >= limit:
                break
        
        logger.info(f"Vector search found {len(repair_results)} repair guides")
        return repair_results
    
    async def check_compatibility(self, part_id: str, model_number: str) -> Dict[str, Any]:
        """Simple compatibility check (same as simple search)"""
        await self.initialize()
        
        part_details = await self.get_part_details(part_id)
        if not part_details:
            return {
                "compatible": False,
                "confidence": 0.0,
                "reason": f"Part {part_id} not found"
            }
        
        # Simple heuristic based on brand matching
        model_upper = model_number.upper()
        part_brand = part_details.brand.upper() if part_details.brand else ""
        
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
                "compatible": True,
                "confidence": 0.3,
                "reason": "Unable to determine compatibility, please verify manually"
            }
    
    async def search_blogs(self, query: str, limit: int = 3) -> List[BlogPost]:
        """Search blog posts using vector similarity"""
        await self.initialize()
        
        if not query.strip():
            return []
        
        # Check if we have blogs index
        if not hasattr(self, 'blogs_index') or self.blogs_index is None:
            logger.info("No blogs index available")
            return []
        
        logger.info(f"Vector searching blogs for: '{query}'")
        
        try:
            # Generate query embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
            
            # Normalize query embedding
            import faiss
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            similarities, indices = self.blogs_index.search(query_embedding, limit * 2)
            
            # Convert results
            blog_results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx >= 0 and similarity > 0.1:  # Valid index and minimum similarity
                    blog_data = self.blogs_data[idx]
                    
                    result = BlogPost(
                        id=f"blog_{idx}",
                        title=blog_data.get('title', 'Untitled Article'),
                        url=blog_data.get('url', ''),
                        description=blog_data.get('description', '')[:200] + "..." if len(blog_data.get('description', '')) > 200 else blog_data.get('description', ''),
                        relevance_score=float(similarity)
                    )
                    blog_results.append(result)
            
            logger.info(f"Found {len(blog_results)} blogs")
            return blog_results[:limit]
            
        except Exception as e:
            logger.error(f"Error in blog vector search: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search provider statistics"""
        return {
            "provider_type": "openai_vector_search",
            "parts_indexed": len(getattr(self, 'parts_data', [])),
            "repairs_indexed": len(getattr(self, 'repairs_data', [])),
            "blogs_indexed": len(getattr(self, 'blogs_data', [])),
            "initialized": self._initialized,
            "faiss_loaded": hasattr(self, 'parts_index')
        }
