"""
PostgreSQL data provider for parts, models, and compatibility data
"""

import logging
import asyncpg
from typing import List, Dict, Any, Optional
from providers.interfaces import DataProvider

logger = logging.getLogger(__name__)

class DatabaseDataProvider(DataProvider):
    """PostgreSQL-based data provider"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.pool = await self.db_manager.get_pool()
            logger.info("Database data provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database provider: {e}")
            raise
    
    async def get_parts_data(self) -> List[Dict[str, Any]]:
        """Get all parts from database"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        part_name,
                        part_id,
                        mpn_id,
                        part_price,
                        install_difficulty,
                        install_time,
                        symptoms,
                        appliance_types,
                        replace_parts,
                        brand,
                        availability,
                        install_video_url,
                        product_url
                    FROM parts 
                    ORDER BY part_id
                """)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error fetching parts from database: {e}")
            return []
    
    async def search_parts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search parts in database"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        part_name,
                        part_id,
                        mpn_id,
                        part_price,
                        symptoms,
                        appliance_types,
                        brand,
                        availability,
                        product_url
                    FROM parts 
                    WHERE 
                        part_name ILIKE $1 OR 
                        part_id ILIKE $1 OR
                        symptoms ILIKE $1
                    ORDER BY 
                        CASE 
                            WHEN part_id ILIKE $1 THEN 1
                            WHEN part_name ILIKE $1 THEN 2
                            ELSE 3
                        END
                    LIMIT $2
                """, f"%{query}%", limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error searching parts in database: {e}")
            return []
    
    async def get_part_by_id(self, part_id: str) -> Optional[Dict[str, Any]]:
        """Get specific part by ID from database"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        part_name,
                        part_id,
                        mpn_id,
                        part_price,
                        install_difficulty,
                        install_time,
                        symptoms,
                        appliance_types,
                        replace_parts,
                        brand,
                        availability,
                        install_video_url,
                        product_url
                    FROM parts 
                    WHERE part_id = $1
                """, part_id)
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Error fetching part {part_id} from database: {e}")
            return None
    
    def get_repairs_data(self) -> List[Dict[str, Any]]:
        """Get repairs data - fallback to CSV for now"""
        # TODO: Implement database repairs table
        return []
    
    def get_blogs_data(self) -> List[Dict[str, Any]]:
        """Get blogs data - fallback to CSV for now"""
        # TODO: Implement database blogs table
        return []
