"""
Abstract interfaces for the modular architecture
Lets us swap out different implementations without breaking stuff
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, field_validator

# data models for type safety
class SearchResult(BaseModel):
    # standard search result format with all the partselect fields
    id: str
    name: str  # part_name
    part_number: str  # part_id
    manufacturer_number: Optional[str] = None  # mpn_id
    price: Optional[str] = None  # part_price
    brand: Optional[str] = None
    category: Optional[str] = None  # appliance_types
    description: Optional[str] = None  # symptoms
    url: Optional[str] = None  # product_url
    image_url: Optional[str] = None
    stock_status: Optional[str] = None  # availability
    relevance_score: Optional[float] = None
    source: str = "unknown"
    
    # Additional PartSelect-specific fields
    install_difficulty: Optional[str] = None
    install_time: Optional[str] = None
    symptoms: Optional[str] = None
    appliance_types: Optional[str] = None
    replace_parts: Optional[str] = None
    install_video_url: Optional[str] = None
    
    @field_validator('price', mode='before')
    @classmethod
    def convert_price_to_string(cls, v):
        """Convert price to string if it's a number"""
        if v is None:
            return None
        return str(v)

class PartDetails(BaseModel):
    """Detailed part information"""
    id: str
    name: str
    part_number: str
    manufacturer_number: Optional[str] = None
    price: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    stock_status: Optional[str] = None
    rating: Optional[str] = None
    reviews_count: Optional[int] = None
    specifications: Optional[Dict[str, Any]] = None
    compatibility: Optional[List[str]] = None
    installation_guides: Optional[List[str]] = None
    
    @field_validator('price', mode='before')
    @classmethod
    def convert_price_to_string(cls, v):
        """Convert price to string if it's a number"""
        if v is None:
            return None
        return str(v)

class BlogPost(BaseModel):
    """Blog post information"""
    id: str
    title: str
    url: str
    description: Optional[str] = None
    relevance_score: Optional[float] = None
    source: str = "blog"

class RepairGuide(BaseModel):
    """Repair guide information"""
    id: str
    title: str
    appliance_type: str
    symptom: str
    difficulty: Optional[str] = None
    estimated_time: Optional[str] = None
    parts_needed: Optional[List[str]] = None
    steps: Optional[str] = None
    url: Optional[str] = None

# Abstract Interfaces
class SearchProvider(ABC):
    """Abstract interface for search implementations"""
    
    @abstractmethod
    async def search_parts(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> List[SearchResult]:
        """
        Search for parts using any method (keyword, semantic, hybrid, etc.)
        
        Args:
            query: User search query
            filters: Optional filters (brand, category, price range, etc.)
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    async def get_part_details(self, part_id: str) -> Optional[PartDetails]:
        """
        Get detailed information for a specific part
        
        Args:
            part_id: Unique part identifier
            
        Returns:
            PartDetails object or None if not found
        """
        pass
    
    @abstractmethod
    async def search_repairs(self, query: str, appliance_type: str = None, limit: int = 5) -> List[RepairGuide]:
        """
        Search for repair guides and troubleshooting information
        
        Args:
            query: Problem description or symptom
            appliance_type: Filter by appliance type (refrigerator, dishwasher)
            limit: Maximum number of results
            
        Returns:
            List of RepairGuide objects
        """
        pass
    
    @abstractmethod
    async def check_compatibility(self, part_id: str, model_number: str) -> Dict[str, Any]:
        """
        Check if a part is compatible with a specific appliance model
        
        Args:
            part_id: Part identifier
            model_number: Appliance model number
            
        Returns:
            Dictionary with compatibility information
        """
        pass

class DataProvider(ABC):
    """Abstract interface for data source implementations"""
    
    @abstractmethod
    async def get_parts_data(self) -> List[Dict[str, Any]]:
        """
        Load all parts data from the data source
        
        Returns:
            List of part dictionaries
        """
        pass
    
    @abstractmethod
    async def get_repairs_data(self) -> List[Dict[str, Any]]:
        """
        Load all repair/troubleshooting data
        
        Returns:
            List of repair guide dictionaries
        """
        pass
    
    @abstractmethod
    async def get_blogs_data(self) -> List[Dict[str, Any]]:
        """
        Load blog/documentation data
        
        Returns:
            List of blog/guide dictionaries
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the data provider (connect to DB, load files, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        pass

class LLMProvider(ABC):
    """Abstract interface for LLM implementations"""
    
    @abstractmethod
    async def generate_response(self, query: str, context: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate AI response using the LLM
        
        Args:
            query: User question
            context: Retrieved information (parts, repairs, etc.)
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response string
        """
        pass
    
    @abstractmethod
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine intent and extract entities
        
        Args:
            query: User input
            
        Returns:
            Dictionary with analysis results (intent, entities, confidence, etc.)
        """
        pass

# Factory interface for dependency injection
class PartSelectApp:
    """Main application class that uses pluggable providers"""
    
    def __init__(self, search_provider: SearchProvider, data_provider: DataProvider, llm_provider: LLMProvider):
        self.search_provider = search_provider
        self.data_provider = data_provider  
        self.llm_provider = llm_provider
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all providers"""
        try:
            await self.data_provider.initialize()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize app: {e}")
            return False
    
    @property
    def initialized(self) -> bool:
        return self._initialized
