"""
Database models for PartSelect case study
Clean simple data structures for appliance parts and repair data
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Part:
    """Part model for appliance parts data"""
    id: Optional[int] = None
    partselect_number: Optional[str] = None
    manufacturer_number: Optional[str] = None
    name: str = ""
    description: str = ""
    price: str = ""
    brand: str = ""
    category: str = ""  # dishwasher or refrigerator
    stock_status: str = ""
    rating: str = ""
    reviews_count: int = 0
    url: str = ""
    image_url: str = ""
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class BlogPost:
    """Blog documentation model for repair guides"""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    category: str = ""
    tags: Optional[List[str]] = None
    appliance_type: str = ""  # dishwasher or refrigerator
    url: str = ""
    created_at: Optional[datetime] = None

@dataclass
class RepairGuide:
    """Repair instructions model"""
    id: Optional[int] = None
    part_id: Optional[int] = None
    title: str = ""
    difficulty_level: str = ""  # easy medium hard
    estimated_time: str = ""
    tools_required: Optional[List[str]] = None
    steps: str = ""
    tips: str = ""
    warnings: str = ""
    appliance_models: Optional[List[str]] = None
    created_at: Optional[datetime] = None

@dataclass
class SearchQuery:
    """Search query parameters"""
    text: str
    brand: Optional[str] = None
    category: Optional[str] = None
    part_number: Optional[str] = None
    limit: int = 10

@dataclass
class SearchResult:
    """Search result with relevance scoring"""
    parts: List[Part]
    blog_posts: List[BlogPost]
    repair_guides: List[RepairGuide]
    total_results: int
    search_time_ms: float
