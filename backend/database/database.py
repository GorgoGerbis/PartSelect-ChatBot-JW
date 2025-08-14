import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncpg
from asyncpg import Connection, Pool
import numpy as np
from datetime import datetime
import logging

# database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://partselect:password@localhost:5432/partselect_db")

# SQL schema
CREATE_EXTENSION_SQL = """
-- vector extension disabled for compatibility
-- CREATE EXTENSION IF NOT EXISTS vector;
"""

CREATE_PARTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partselect_number VARCHAR(50),
    manufacturer_number VARCHAR(50),
    name TEXT NOT NULL,
    description TEXT,
    price VARCHAR(20),
    brand VARCHAR(100),
    category VARCHAR(50),
    stock_status VARCHAR(50),
    rating VARCHAR(20),
    reviews_count INTEGER DEFAULT 0,
    url TEXT,
    image_url TEXT,
    embedding TEXT,  -- vector embedding as JSON text pgvector not available
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_INDEXES_SQL = """
-- standard indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_parts_partselect_number ON parts(partselect_number);
CREATE INDEX IF NOT EXISTS idx_parts_manufacturer_number ON parts(manufacturer_number);
CREATE INDEX IF NOT EXISTS idx_parts_brand_category ON parts(brand, category);
CREATE INDEX IF NOT EXISTS idx_parts_name ON parts USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_parts_description ON parts USING gin(to_tsvector('english', description));

-- Vector similarity index disabled (pgvector not available)
-- CREATE INDEX IF NOT EXISTS idx_parts_embedding ON parts USING hnsw (embedding vector_cosine_ops);
"""

class DatabaseManager:
    """Manages PostgreSQL database with vector search capabilities."""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize database connection pool and create tables."""
        try:
            # create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # initialize database schema
            async with self.pool.acquire() as conn:
                # skip extension creation vector not available
                # await conn.execute(CREATE_EXTENSION_SQL)
                await conn.execute(CREATE_PARTS_TABLE_SQL)
                await conn.execute(CREATE_INDEXES_SQL)
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    def get_pool(self) -> Pool:
        """Expose the connection pool for providers that need raw access."""
        if not self.pool:
            raise RuntimeError("Database not initialized Call initialize() first")
        return self.pool
    
    async def load_parts_from_json(self, data_dir: Path):
        """Load flattened JSON parts data into PostgreSQL."""
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found {data_dir}")
        
        json_files = list(data_dir.glob("*.json"))
        total_parts = 0
        
        self.logger.info(f"Loading {len(json_files)} JSON files into database")
        
        async with self.pool.acquire() as conn:
            # clear existing data
            await conn.execute("TRUNCATE parts")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # extract brand and category from filename
                    filename = json_file.stem  # e.g., "Whirlpool-Dishwasher-Parts"
                    parts = filename.split("-")
                    if len(parts) >= 2:
                        brand = parts[0]
                        category = parts[1]  # Dishwasher or Refrigerator
                        
                        # prepare batch insert
                        insert_data = []
                        for part in data:
                            insert_data.append((
                                part.get('partselect_number'),
                                part.get('manufacturer_number'),
                                part.get('name', 'Unknown Part'),
                                part.get('description', ''),
                                part.get('price', ''),
                                brand,
                                category,
                                part.get('stock_status', 'Unknown'),
                                part.get('rating', ''),
                                part.get('reviews_count', 0),
                                part.get('url', ''),
                                part.get('image_url', ''),
                                json.dumps(part, ensure_ascii=False)  # Store full JSON as text; cast to JSONB in INSERT
                            ))
                        
                        # Batch insert
                        await conn.executemany("""
                            INSERT INTO parts (
                                partselect_number, manufacturer_number, name, description,
                                price, brand, category, stock_status, rating, reviews_count,
                                url, image_url, metadata
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
                        """, insert_data)
                        
                        total_parts += len(data)
                        self.logger.info(f"Loaded {len(data)} parts from {json_file.name}")
                
                except Exception as e:
                    self.logger.error(f"Error loading {json_file} {e}")
                    continue
        
        self.logger.info(f"Successfully loaded {total_parts} parts into database")
        return total_parts
    
    async def search_parts_sql(
        self, 
        query: str, 
        brand: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Traditional SQL-based search for exact matches and filtering."""
        
        sql_conditions = ["1=1"]  # always true base condition
        params = []
        param_count = 0
        
        # add text search conditions
        if query:
            param_count += 1
            sql_conditions.append(f"""(
                partselect_number ILIKE ${param_count} OR
                manufacturer_number ILIKE ${param_count} OR
                name ILIKE ${param_count} OR
                to_tsvector('english', description) @@ plainto_tsquery('english', ${param_count})
            )""")
            params.append(f"%{query}%")
        
        # Add brand filter
        if brand:
            param_count += 1
            sql_conditions.append(f"brand ILIKE ${param_count}")
            params.append(f"%{brand}%")
        
        # Add category filter
        if category:
            param_count += 1
            sql_conditions.append(f"category ILIKE ${param_count}")
            params.append(f"%{category}%")
        
        sql = f"""
        SELECT 
            id, partselect_number, manufacturer_number, name, description,
            price, brand, category, stock_status, rating, reviews_count,
            url, image_url, metadata,
            CASE 
                WHEN partselect_number ILIKE $1 OR manufacturer_number ILIKE $1 THEN 100
                WHEN name ILIKE $1 THEN 50
                ELSE 10
            END as relevance_score
        FROM parts 
        WHERE {' AND '.join(sql_conditions)}
        ORDER BY relevance_score DESC, name
        LIMIT {limit}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
    
    async def search_parts_vector(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Vector similarity search using pgvector."""
        
        # vector similarity search disabled pgvector not available
        return []
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Combine SQL and vector search for best results."""
        
        # get SQL results exact matches keywords
        sql_results = await self.search_parts_sql(query, brand, category, limit)
        
        # vector results disabled pgvector not available
        vector_results = []
        
        # Merge and deduplicate results
        seen_ids = set()
        merged_results = []
        
        # Add SQL results first (higher priority for exact matches)
        for result in sql_results:
            if result['id'] not in seen_ids:
                result['search_type'] = 'sql'
                merged_results.append(result)
                seen_ids.add(result['id'])
        
        # Add vector results
        for result in vector_results:
            if result['id'] not in seen_ids:
                result['search_type'] = 'vector'
                result['relevance_score'] = result.get('similarity_score', 0) * 100
                merged_results.append(result)
                seen_ids.add(result['id'])
        
        # Sort by relevance and return
        merged_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return merged_results[:limit]
    
    # SUPER FAST DIRECT LOOKUPS - For specific queries like "PS11752778"
    async def get_part_by_exact_number(self, part_number: str) -> Optional[Dict[str, Any]]:
        """Lightning-fast exact part number lookup - <100ms response"""
        sql = """
        SELECT 
            id, partselect_number, manufacturer_number, name, description,
            price, brand, category, stock_status, rating, reviews_count,
            url, image_url, metadata
        FROM parts 
        WHERE partselect_number = $1 OR manufacturer_number = $1
        LIMIT 1
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, part_number)
            return dict(row) if row else None
    
    async def get_installation_info(self, part_number: str) -> Dict[str, Any]:
        """Get complete installation info for a specific part - SUPER FAST"""
        # Get the part details first
        part = await self.get_part_by_exact_number(part_number)
        if not part:
            return {"error": f"Part {part_number} not found"}
        
        # TODO add installation video guide lookup from blogs table
        # for now extract from metadata if available
        metadata = part.get('metadata', {})
        
        return {
            "part": part,
            "installation": {
                "difficulty": metadata.get('install_difficulty', 'Unknown'),
                "time": metadata.get('install_time', 'Unknown'),
                "video_url": metadata.get('install_video_url'),
                "tools_needed": metadata.get('tools_required', []),
                "instructions": metadata.get('install_instructions', 'Check the part URL for detailed instructions')
            },
            "compatibility": {
                "models": metadata.get('compatible_models', []),
                "symptoms": part.get('description', '')
            }
        }
    
    async def get_parts_for_model(self, model_number: str, symptom: str = None) -> List[Dict[str, Any]]:
        """Find all parts for a specific model - SUPER FAST MODEL LOOKUP"""
        conditions = ["(metadata->>'compatible_models' ILIKE $1 OR description ILIKE $1)"]
        params = [f"%{model_number}%"]
        param_count = 1
        
        if symptom:
            param_count += 1
            conditions.append(f"(description ILIKE ${param_count} OR metadata->>'symptoms' ILIKE ${param_count})")
            params.append(f"%{symptom}%")
        
        sql = f"""
        SELECT 
            id, partselect_number, manufacturer_number, name, description,
            price, brand, category, stock_status, rating, reviews_count,
            url, image_url, metadata,
            CASE 
                WHEN metadata->>'compatible_models' ILIKE $1 THEN 100
                WHEN description ILIKE $1 THEN 50
                ELSE 10
            END as relevance_score
        FROM parts 
        WHERE {' AND '.join(conditions)}
        ORDER BY relevance_score DESC, price ASC
        LIMIT 20
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
    
    async def get_repair_guides_for_symptom(self, appliance_type: str, symptom: str) -> List[Dict[str, Any]]:
        """Get repair guides for specific symptoms - SUPER FAST REPAIR LOOKUP"""
        # TODO this would query a repairs table if you have one
        # for now search in blogs for repair content
        sql = """
        SELECT title, url, description
        FROM blogs
        WHERE (title ILIKE $1 OR description ILIKE $1) 
          AND (title ILIKE $2 OR description ILIKE $2)
        ORDER BY 
            CASE WHEN title ILIKE $1 THEN 100 ELSE 50 END DESC
        LIMIT 5
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, f"%{symptom}%", f"%{appliance_type}%")
            return [dict(row) for row in rows]

# Global database manager instance
db_manager = DatabaseManager()

async def get_database() -> DatabaseManager:
    """Dependency injection for FastAPI."""
    if not db_manager.pool:
        await db_manager.initialize()
    return db_manager
