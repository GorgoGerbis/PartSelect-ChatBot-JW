"""
MCP server for PartSelect tools
Handles parts searching, compatibility checking, model lookup, etc.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import asyncpg
from asyncpg import Pool
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import numpy as np
from datetime import datetime

# vector search stuff - might not be installed
try:
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    logging.warning("vector search not available, install with: pip install langchain-community langchain-openai faiss-cpu")

# basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("partselect_mcp_server")

# MCP server setup
mcp = FastMCP("partselect")

# database config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://partselect:password@localhost:5432/partselect_db")

# global state
db_pool: Optional[Pool] = None
parts_vectorstore = None
repairs_vectorstore = None
embeddings_client = None

# safety limits
ALLOWED_QUERY_TYPES = ["SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "WITH"]
MAX_RESULTS = 20
QUERY_TIMEOUT = 15

class PartSearchResult(BaseModel):
    # what we return when searching for parts
    id: Optional[str] = None
    partselect_number: Optional[str] = None
    manufacturer_number: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    stock_status: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    similarity_score: Optional[float] = None

class ModelSearchResult(BaseModel):
    """Model for appliance model search results"""
    id: Optional[str] = None
    model_number: str
    brand: str
    appliance_type: str
    description: Optional[str] = None

class CompatibilityResult(BaseModel):
    """Model for compatibility check results"""
    is_compatible: bool
    confidence: float
    notes: Optional[str] = None
    alternative_parts: Optional[List[str]] = None

def is_safe_query(query: str) -> bool:
    """Check if the query is safe (read-only)."""
    query_upper = query.strip().upper()
    
    # Check if it starts with allowed commands
    starts_with_allowed = any(
        query_upper.startswith(allowed) for allowed in ALLOWED_QUERY_TYPES
    )
    
    if not starts_with_allowed:
        return False
    
    # Check for dangerous keywords
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
        "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
    ]
    
    return not any(keyword in query_upper for keyword in dangerous_keywords)

async def get_db_pool() -> Pool:
    """Get or create database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=QUERY_TIMEOUT
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    return db_pool

async def initialize_vector_stores():
    """Initialize FAISS vector stores for semantic search."""
    global parts_vectorstore, repairs_vectorstore, embeddings_client
    
    if not VECTOR_SEARCH_AVAILABLE:
        logger.warning("Vector search not available - skipping initialization")
        return
    
    try:
        # Initialize OpenAI embeddings
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found - vector search disabled")
            return
            
        embeddings_client = OpenAIEmbeddings(api_key=openai_api_key)
        
        # Load existing vector stores or create empty ones
        vector_stores_dir = Path(__file__).parent.parent / "vector_stores"
        vector_stores_dir.mkdir(exist_ok=True)
        
        parts_index_path = vector_stores_dir / "parts_index"
        repairs_index_path = vector_stores_dir / "repairs_index"
        
        # Load or create parts vector store
        if parts_index_path.exists():
            try:
                parts_vectorstore = FAISS.load_local(
                    str(parts_index_path), 
                    embeddings_client,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing parts vector store")
            except Exception as e:
                logger.warning(f"Failed to load parts vector store: {e}")
        
        # Load or create repairs vector store
        if repairs_index_path.exists():
            try:
                repairs_vectorstore = FAISS.load_local(
                    str(repairs_index_path), 
                    embeddings_client,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing repairs vector store")
            except Exception as e:
                logger.warning(f"Failed to load repairs vector store: {e}")
        
        if parts_vectorstore is None or repairs_vectorstore is None:
            logger.info("Vector stores not found - they will be created when data is first indexed")
            
    except Exception as e:
        logger.error(f"Error initializing vector stores: {e}")

# Database Tools
@mcp.tool()
async def search_parts(
    query: str,
    brand: Optional[str] = None,
    appliance_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for appliance parts by name, description, or part number.
    
    Args:
        query: Search term (part name, description, symptoms, etc.)
        brand: Optional brand filter (e.g., 'Whirlpool', 'GE', 'Samsung')
        appliance_type: Optional appliance type filter ('refrigerator' or 'dishwasher')
        limit: Maximum number of results (default 10, max 20)
    
    Returns:
        List of matching parts with details
    """
    limit = min(limit, MAX_RESULTS)
    
    try:
        pool = await get_db_pool()
        
        # Build the SQL query
        where_conditions = []
        params = []
        param_count = 0
        
        # Search in name, description, and part numbers
        param_count += 1
        where_conditions.append(f"""(
            name ILIKE ${param_count} OR 
            description ILIKE ${param_count} OR 
            partselect_number ILIKE ${param_count} OR 
            manufacturer_number ILIKE ${param_count}
        )""")
        params.append(f"%{query}%")
        
        # Add brand filter
        if brand:
            param_count += 1
            where_conditions.append(f"brand ILIKE ${param_count}")
            params.append(f"%{brand}%")
        
        # Add appliance type filter (assuming we have this in metadata or category)
        if appliance_type:
            param_count += 1
            where_conditions.append(f"(category ILIKE ${param_count} OR metadata->>'appliance_type' ILIKE ${param_count})")
            params.append(f"%{appliance_type}%")
        
        sql_query = f"""
        SELECT 
            id, partselect_number, manufacturer_number, name, description,
            price, brand, category, stock_status, url, image_url, metadata
        FROM parts 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY 
            CASE 
                WHEN name ILIKE ${params.index(f'%{query}%') + 1} THEN 1
                WHEN partselect_number ILIKE ${params.index(f'%{query}%') + 1} THEN 2
                ELSE 3
            END,
            name
        LIMIT {limit}
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_query, *params)
            
            results = []
            for row in rows:
                result = {
                    "id": str(row["id"]) if row["id"] else None,
                    "partselect_number": row["partselect_number"],
                    "manufacturer_number": row["manufacturer_number"],
                    "name": row["name"],
                    "description": row["description"],
                    "price": row["price"],
                    "brand": row["brand"],
                    "category": row["category"],
                    "stock_status": row["stock_status"],
                    "url": row["url"],
                    "image_url": row["image_url"],
                    "metadata": row["metadata"]
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} parts for query: {query}")
            return results
            
    except Exception as e:
        logger.error(f"Error searching parts: {e}")
        return [{"error": f"Failed to search parts: {str(e)}"}]

@mcp.tool()
async def get_part_details(part_number: str) -> Dict[str, Any]:
    """
    Get complete details for a specific part by part number.
    
    Args:
        part_number: PartSelect part number or manufacturer part number
        
    Returns:
        Complete part information including specifications and compatibility
    """
    try:
        pool = await get_db_pool()
        
        sql_query = """
        SELECT 
            id, partselect_number, manufacturer_number, name, description,
            price, brand, category, stock_status, rating, reviews_count,
            url, image_url, metadata, created_at, updated_at
        FROM parts 
        WHERE partselect_number = $1 OR manufacturer_number = $1
        LIMIT 1
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql_query, part_number)
            
            if not row:
                return {"error": f"Part not found: {part_number}"}
            
            result = {
                "id": str(row["id"]) if row["id"] else None,
                "partselect_number": row["partselect_number"],
                "manufacturer_number": row["manufacturer_number"],
                "name": row["name"],
                "description": row["description"],
                "price": row["price"],
                "brand": row["brand"],
                "category": row["category"],
                "stock_status": row["stock_status"],
                "rating": row["rating"],
                "reviews_count": row["reviews_count"],
                "url": row["url"],
                "image_url": row["image_url"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }
            
            logger.info(f"Retrieved details for part: {part_number}")
            return result
            
    except Exception as e:
        logger.error(f"Error getting part details: {e}")
        return {"error": f"Failed to get part details: {str(e)}"}

@mcp.tool()
async def check_compatibility(part_number: str, model_number: str) -> Dict[str, Any]:
    """
    Enhanced compatibility checking with cross-brand support and appliance type validation.
    
    Args:
        part_number: PartSelect part number or manufacturer part number
        model_number: Appliance model number
        
    Returns:
        Detailed compatibility information with confidence scoring and explanations
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Step 1: Get part details with appliance type detection
            part_query = """
            SELECT id, name, brand, category, metadata,
                   CASE 
                       WHEN LOWER(name) LIKE '%refrigerator%' OR LOWER(category) LIKE '%fridge%' 
                            OR metadata::text LIKE '%refrigerator%' THEN 'refrigerator'
                       WHEN LOWER(name) LIKE '%dishwasher%' OR LOWER(category) LIKE '%dish%'
                            OR metadata::text LIKE '%dishwasher%' THEN 'dishwasher'
                       ELSE 'unknown'
                   END as part_appliance_type
            FROM parts 
            WHERE partselect_number = $1 OR manufacturer_number = $1
            LIMIT 1
            """
            
            part_row = await conn.fetchrow(part_query, part_number)
            if not part_row:
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "error": f"Part {part_number} not found in database",
                    "recommendation": "Please verify the part number and try again"
                }
            
            # Step 2: Get model details
            model_query = """
            SELECT id, brand, appliance_type, series, compatible_brands, metadata
            FROM models
            WHERE model_number = $1
            LIMIT 1
            """
            
            model_row = await conn.fetchrow(model_query, model_number)
            if not model_row:
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "part_name": part_row["name"],
                    "part_brand": part_row["brand"],
                    "notes": f"Model {model_number} not found in database",
                    "recommendation": "Please verify the model number. You can usually find it on a sticker inside your appliance or in the manual."
                }
            
            # Step 3: Critical appliance type check (catches fridge part + dishwasher model)
            part_appliance_type = part_row["part_appliance_type"]
            model_appliance_type = model_row["appliance_type"]
            
            if (part_appliance_type != 'unknown' and 
                model_appliance_type and 
                part_appliance_type != model_appliance_type):
                return {
                    "is_compatible": False,
                    "confidence": 1.0,
                    "part_name": part_row["name"],
                    "part_brand": part_row["brand"],
                    "part_appliance_type": part_appliance_type,
                    "model_brand": model_row["brand"],
                    "model_appliance_type": model_appliance_type,
                    "notes": f"❌ INCOMPATIBLE: This is a {part_appliance_type} part, but {model_number} is a {model_appliance_type}",
                    "recommendation": f"You need a {model_appliance_type} part instead. Try searching for '{model_appliance_type} {part_row['name'].split()[-1]}'"
                }
            
            # Step 4: Check explicit compatibility table
            explicit_compat_query = """
            SELECT compatibility_type, confidence_score, notes, source
            FROM part_compatibility pc
            JOIN parts p ON pc.part_id = p.id
            JOIN models m ON pc.model_id = m.id
            WHERE (p.partselect_number = $1 OR p.manufacturer_number = $1)
            AND m.model_number = $2
            LIMIT 1
            """
            
            explicit_result = await conn.fetchrow(explicit_compat_query, part_number, model_number)
            if explicit_result:
                is_compatible = explicit_result["compatibility_type"] in ['exact', 'compatible']
                confidence = float(explicit_result["confidence_score"])
                
                return {
                    "is_compatible": is_compatible,
                    "confidence": confidence,
                    "part_name": part_row["name"],
                    "part_brand": part_row["brand"],
                    "model_brand": model_row["brand"],
                    "compatibility_type": explicit_result["compatibility_type"],
                    "notes": f"✅ Database confirmed: {explicit_result['notes']}" if is_compatible else f"❌ Database confirmed: {explicit_result['notes']}",
                    "source": explicit_result["source"],
                    "recommendation": "This compatibility has been verified in our database."
                }
            
            # Step 5: Cross-brand compatibility check using brand relationships
            part_brand = part_row["brand"]
            model_brand = model_row["brand"]
            
            # Check if brands are directly compatible
            if part_brand and model_brand:
                brand_compat_query = """
                SELECT compatibility_strength, notes
                FROM brand_relationships
                WHERE (parent_brand = $1 AND subsidiary_brand = $2)
                   OR (parent_brand = $2 AND subsidiary_brand = $1)
                AND (appliance_type = $3 OR appliance_type = 'both')
                LIMIT 1
                """
                
                brand_result = await conn.fetchrow(brand_compat_query, part_brand, model_brand, model_appliance_type)
                
                if brand_result:
                    compatibility_strength = float(brand_result["compatibility_strength"])
                    is_compatible = compatibility_strength >= 0.6  # Threshold for compatibility
                    
                    return {
                        "is_compatible": is_compatible,
                        "confidence": compatibility_strength,
                        "part_name": part_row["name"],
                        "part_brand": part_brand,
                        "model_brand": model_brand,
                        "notes": f"✅ Cross-brand compatibility: {brand_result['notes']}" if is_compatible else f"⚠️ Limited compatibility: {brand_result['notes']}",
                        "recommendation": "Cross-brand compatibility detected. Please verify the specific part fit before ordering." if is_compatible else "Limited cross-brand compatibility. Consider finding a part specifically for your brand."
                    }
                
                # Step 6: Same brand check
                if part_brand.lower() == model_brand.lower():
                    return {
                        "is_compatible": True,
                        "confidence": 0.9,
                        "part_name": part_row["name"],
                        "part_brand": part_brand,
                        "model_brand": model_brand,
                        "notes": f"✅ Same brand match: {part_brand} part for {model_brand} model",
                        "recommendation": "Same brand compatibility. Please verify the part number matches your specific model's requirements."
                    }
                
                # Step 7: No brand relationship found
                return {
                    "is_compatible": False,
                    "confidence": 0.3,
                    "part_name": part_row["name"],
                    "part_brand": part_brand,
                    "model_brand": model_brand,
                    "notes": f"❌ No known compatibility: {part_brand} part with {model_brand} model",
                    "recommendation": f"Consider finding a {model_brand}-specific part instead. Cross-brand compatibility is not established for these brands."
                }
            
            # Step 8: Missing brand information
            return {
                "is_compatible": False,
                "confidence": 0.1,
                "part_name": part_row["name"],
                "part_brand": part_brand or "Unknown",
                "model_brand": model_brand or "Unknown",
                "notes": "⚠️ Insufficient brand information to determine compatibility",
                "recommendation": "Please verify compatibility on the PartSelect website or contact customer service for assistance."
            }
            
    except Exception as e:
        logger.error(f"Error in enhanced compatibility check: {e}")
        return {
            "is_compatible": False,
            "confidence": 0.0,
            "error": f"Compatibility check failed: {str(e)}",
            "recommendation": "Please try again or contact customer service for assistance."
        }

@mcp.tool()
async def search_models(
    brand: Optional[str] = None,
    model_number: Optional[str] = None,
    appliance_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for appliance models by brand, model number, or appliance type.
    
    Args:
        brand: Brand name (e.g., 'Whirlpool', 'GE')
        model_number: Full or partial model number
        appliance_type: Type of appliance ('refrigerator' or 'dishwasher')
        limit: Maximum number of results (default 10, max 20)
        
    Returns:
        List of matching appliance models
    """
    limit = min(limit, MAX_RESULTS)
    
    try:
        pool = await get_db_pool()
        
        where_conditions = []
        params = []
        param_count = 0
        
        if brand:
            param_count += 1
            where_conditions.append(f"brand ILIKE ${param_count}")
            params.append(f"%{brand}%")
        
        if model_number:
            param_count += 1
            where_conditions.append(f"model_number ILIKE ${param_count}")
            params.append(f"%{model_number}%")
        
        if appliance_type:
            param_count += 1
            where_conditions.append(f"appliance_type ILIKE ${param_count}")
            params.append(f"%{appliance_type}%")
        
        if not where_conditions:
            where_conditions.append("1=1")  # Return all if no filters
        
        sql_query = f"""
        SELECT 
            id, model_number, brand, appliance_type, description, metadata
        FROM models 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY brand, model_number
        LIMIT {limit}
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_query, *params)
            
            results = []
            for row in rows:
                result = {
                    "id": str(row["id"]) if row["id"] else None,
                    "model_number": row["model_number"],
                    "brand": row["brand"],
                    "appliance_type": row["appliance_type"],
                    "description": row["description"],
                    "metadata": row["metadata"]
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} models")
            return results
            
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        return [{"error": f"Failed to search models: {str(e)}"}]

@mcp.tool()
async def get_brand_relationships(brand: str, appliance_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get cross-brand compatibility relationships for a specific brand.
    Useful for understanding which parts can work across different brands.
    
    Args:
        brand: Brand name to check relationships for
        appliance_type: Optional filter by appliance type
        
    Returns:
        Brand relationship information with compatibility strengths
    """
    try:
        pool = await get_db_pool()
        
        where_conditions = ["(parent_brand = $1 OR subsidiary_brand = $1)"]
        params = [brand]
        
        if appliance_type:
            where_conditions.append("(appliance_type = $2 OR appliance_type = 'both')")
            params.append(appliance_type.lower())
        
        sql_query = f"""
        SELECT 
            parent_brand, subsidiary_brand, appliance_type,
            compatibility_strength, notes
        FROM brand_relationships
        WHERE {' AND '.join(where_conditions)}
        ORDER BY compatibility_strength DESC
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_query, *params)
            
            relationships = []
            for row in rows:
                # Determine the relationship direction
                is_parent = row["parent_brand"].lower() == brand.lower()
                related_brand = row["subsidiary_brand"] if is_parent else row["parent_brand"]
                relationship_type = "owns" if is_parent else "owned_by"
                
                relationships.append({
                    "related_brand": related_brand,
                    "relationship_type": relationship_type,
                    "appliance_type": row["appliance_type"],
                    "compatibility_strength": float(row["compatibility_strength"]),
                    "notes": row["notes"]
                })
            
            return {
                "brand": brand,
                "relationships": relationships,
                "total_relationships": len(relationships)
            }
            
    except Exception as e:
        logger.error(f"Error getting brand relationships: {e}")
        return {"brand": brand, "relationships": [], "error": str(e)}

@mcp.tool()
async def suggest_compatible_parts(model_number: str, issue_description: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Suggest compatible parts for a specific model based on the issue description.
    Uses the enhanced compatibility system to find appropriate parts.
    
    Args:
        model_number: Appliance model number
        issue_description: Description of the problem (e.g., "not draining", "ice maker broken")
        limit: Maximum number of part suggestions
        
    Returns:
        List of compatible parts with compatibility confidence scores
    """
    limit = min(limit, MAX_RESULTS)
    
    try:
        pool = await get_db_pool()
        
        # First, get the model details
        model_query = """
        SELECT id, brand, appliance_type, compatible_brands
        FROM models
        WHERE model_number = $1
        LIMIT 1
        """
        
        async with pool.acquire() as conn:
            model_row = await conn.fetchrow(model_query, model_number)
            
            if not model_row:
                return [{"error": f"Model {model_number} not found in database"}]
            
            model_brand = model_row["brand"]
            model_appliance_type = model_row["appliance_type"]
            compatible_brands = model_row.get("compatible_brands", [])
            
            # Build brand filter for search - include the model's brand plus compatible brands
            brand_list = [model_brand]
            if compatible_brands:
                brand_list.extend(compatible_brands)
            
            # Remove duplicates and None values
            brand_list = list(set([b for b in brand_list if b]))
            
            if not brand_list:
                return [{"error": "No compatible brands found for this model"}]
            
            # Create placeholders for the IN clause
            brand_placeholders = ','.join(['$' + str(i+3) for i in range(len(brand_list))])
            
            # Search for parts that might fix the issue
            parts_query = f"""
            SELECT 
                p.partselect_number, p.manufacturer_number, p.name, 
                p.brand, p.price, p.stock_status, p.url,
                CASE 
                    WHEN LOWER(p.name) LIKE '%refrigerator%' OR LOWER(p.category) LIKE '%fridge%' THEN 'refrigerator'
                    WHEN LOWER(p.name) LIKE '%dishwasher%' OR LOWER(p.category) LIKE '%dish%' THEN 'dishwasher'
                    ELSE 'unknown'
                END as part_appliance_type
            FROM parts p
            WHERE p.brand IN ({brand_placeholders})
            AND (
                LOWER(p.name) LIKE $1 
                OR LOWER(p.description) LIKE $1
                OR p.metadata::text LIKE $1
            )
            AND (
                CASE 
                    WHEN LOWER(p.name) LIKE '%refrigerator%' OR LOWER(p.category) LIKE '%fridge%' THEN 'refrigerator'
                    WHEN LOWER(p.name) LIKE '%dishwasher%' OR LOWER(p.category) LIKE '%dish%' THEN 'dishwasher'
                    ELSE 'unknown'
                END = $2 OR 
                CASE 
                    WHEN LOWER(p.name) LIKE '%refrigerator%' OR LOWER(p.category) LIKE '%fridge%' THEN 'refrigerator'
                    WHEN LOWER(p.name) LIKE '%dishwasher%' OR LOWER(p.category) LIKE '%dish%' THEN 'dishwasher'
                    ELSE 'unknown'
                END = 'unknown'
            )
            ORDER BY 
                CASE WHEN p.brand = $3 THEN 1 ELSE 2 END,  -- Prefer exact brand match
                p.name
            LIMIT $4
            """
            
            # Simple keyword matching for issue description
            search_term = f"%{issue_description.lower()}%"
            params = [search_term, model_appliance_type, model_brand] + brand_list + [limit]
            
            parts_rows = await conn.fetch(parts_query, *params)
            
            results = []
            for part_row in parts_rows:
                # Calculate compatibility confidence
                part_brand = part_row["brand"]
                confidence = 0.9 if part_brand == model_brand else 0.7  # Lower for cross-brand
                
                if part_row["part_appliance_type"] != model_appliance_type and part_row["part_appliance_type"] != 'unknown':
                    confidence = 0.1  # Very low for wrong appliance type
                
                results.append({
                    "part_number": part_row["partselect_number"] or part_row["manufacturer_number"],
                    "name": part_row["name"],
                    "brand": part_brand,
                    "price": part_row["price"],
                    "stock_status": part_row["stock_status"],
                    "url": part_row["url"],
                    "compatibility_confidence": confidence,
                    "compatibility_note": f"{'Exact' if part_brand == model_brand else 'Cross-brand'} compatibility for {model_number}"
                })
            
            logger.info(f"Found {len(results)} compatible parts for {model_number}")
            return results
            
    except Exception as e:
        logger.error(f"Error suggesting compatible parts: {e}")
        return [{"error": f"Failed to suggest compatible parts: {str(e)}"}]

# Vector Search Tools (only available if dependencies are installed)
if VECTOR_SEARCH_AVAILABLE:
    @mcp.tool()
    async def semantic_search_parts(
        query: str,
        appliance_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find parts using natural language semantic search.
        
        Args:
            query: Natural language description of the part or problem
            appliance_type: Optional filter ('refrigerator' or 'dishwasher')
            top_k: Number of results to return (default 10, max 20)
            
        Returns:
            List of semantically similar parts with similarity scores
        """
        top_k = min(top_k, MAX_RESULTS)
        
        if not parts_vectorstore:
            return [{"error": "Parts vector store not initialized. Please run the populate_vectors.py script first."}]
        
        try:
            # Perform semantic search
            docs = parts_vectorstore.similarity_search_with_score(query, k=top_k)
            
            results = []
            for doc, score in docs:
                # Parse the document content (assuming it's JSON)
                try:
                    part_data = json.loads(doc.page_content)
                    part_data["similarity_score"] = float(score)
                    
                    # Apply appliance type filter if specified
                    if appliance_type:
                        part_category = part_data.get("category", "").lower()
                        part_metadata = part_data.get("metadata", {})
                        part_appliance_type = part_metadata.get("appliance_type", "").lower()
                        
                        if appliance_type.lower() not in part_category and appliance_type.lower() not in part_appliance_type:
                            continue
                    
                    results.append(part_data)
                except json.JSONDecodeError:
                    # Handle plain text documents
                    results.append({
                        "content": doc.page_content,
                        "similarity_score": float(score),
                        "source": "vector_search"
                    })
            
            logger.info(f"Semantic search found {len(results)} parts for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return [{"error": f"Semantic search failed: {str(e)}"}]

    @mcp.tool()
    async def find_similar_parts(
        part_number: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find parts similar to a given part using vector similarity.
        
        Args:
            part_number: Reference part number
            top_k: Number of similar parts to return (default 5, max 10)
            
        Returns:
            List of similar parts with similarity scores
        """
        top_k = min(top_k, 10)
        
        if not parts_vectorstore:
            return [{"error": "Parts vector store not initialized"}]
        
        try:
            # First get the reference part details
            part_details = await get_part_details(part_number)
            if "error" in part_details:
                return [part_details]
            
            # Use part name and description for similarity search
            search_text = f"{part_details.get('name', '')} {part_details.get('description', '')}"
            
            docs = parts_vectorstore.similarity_search_with_score(search_text, k=top_k + 1)
            
            results = []
            for doc, score in docs:
                try:
                    part_data = json.loads(doc.page_content)
                    
                    # Skip the original part
                    if (part_data.get("partselect_number") == part_number or 
                        part_data.get("manufacturer_number") == part_number):
                        continue
                    
                    part_data["similarity_score"] = float(score)
                    results.append(part_data)
                    
                    if len(results) >= top_k:
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            logger.info(f"Found {len(results)} similar parts for: {part_number}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar parts: {e}")
            return [{"error": f"Failed to find similar parts: {str(e)}"}]

# Hybrid Tools
@mcp.tool()
async def smart_part_search(
    query: str,
    appliance_type: Optional[str] = None,
    use_semantic: bool = True,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Intelligent part search combining database and semantic search.
    
    Args:
        query: Search query (part name, symptoms, description)
        appliance_type: Optional appliance type filter
        use_semantic: Whether to include semantic search results
        limit: Maximum results per search method
        
    Returns:
        Combined results from both search methods
    """
    results = {
        "database_results": [],
        "semantic_results": [],
        "combined_count": 0,
        "search_methods_used": []
    }
    
    try:
        # Always do database search
        db_results = await search_parts(query, appliance_type=appliance_type, limit=limit)
        results["database_results"] = db_results
        results["search_methods_used"].append("database")
        
        # Add semantic search if available and requested
        if use_semantic and VECTOR_SEARCH_AVAILABLE and parts_vectorstore:
            semantic_results = await semantic_search_parts(query, appliance_type=appliance_type, top_k=limit)
            if not any("error" in result for result in semantic_results):
                results["semantic_results"] = semantic_results
                results["search_methods_used"].append("semantic")
        
        results["combined_count"] = len(results["database_results"]) + len(results["semantic_results"])
        
        logger.info(f"Smart search completed: {results['combined_count']} total results using {results['search_methods_used']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in smart search: {e}")
        return {"error": f"Smart search failed: {str(e)}"}

# Utility Tools
@mcp.tool()
async def get_server_status() -> Dict[str, Any]:
    """
    Get the current status of the MCP server and its components.
    
    Returns:
        Server status information including database and vector store availability
    """
    status = {
        "server": "PartSelect MCP Server",
        "timestamp": datetime.now().isoformat(),
        "database": {"connected": False, "pool_size": 0},
        "vector_search": {"available": VECTOR_SEARCH_AVAILABLE, "stores_loaded": {}},
        "tools_available": []
    }
    
    # Check database connection
    try:
        pool = await get_db_pool()
        status["database"]["connected"] = True
        status["database"]["pool_size"] = pool.get_size()
    except Exception as e:
        status["database"]["error"] = str(e)
    
    # Check vector stores
    if VECTOR_SEARCH_AVAILABLE:
        status["vector_search"]["stores_loaded"] = {
            "parts": parts_vectorstore is not None,
            "repairs": repairs_vectorstore is not None
        }
    
    # List available tools
    status["tools_available"] = [
        "search_parts", "get_part_details", "check_compatibility", 
        "search_models", "smart_part_search", "get_server_status"
    ]
    
    if VECTOR_SEARCH_AVAILABLE:
        status["tools_available"].extend([
            "semantic_search_parts", "find_similar_parts"
        ])
    
    return status

# Server startup and initialization
async def startup():
    """Initialize the MCP server components."""
    logger.info("Starting PartSelect MCP Server...")
    
    try:
        # Initialize database connection
        await get_db_pool()
        logger.info("Database connection established")
        
        # Initialize vector stores
        await initialize_vector_stores()
        
        logger.info("PartSelect MCP Server startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    # Run startup initialization
    asyncio.run(startup())
    
    # Start the MCP server
    logger.info("Starting MCP server on stdio transport...")
    mcp.run(transport='stdio')
