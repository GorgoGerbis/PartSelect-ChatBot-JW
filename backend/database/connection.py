"""
PostgreSQL database connection management
Simple connection handling stuff
"""

import os
import asyncpg
from asyncpg import Pool
import logging
from typing import Optional
from dotenv import load_dotenv

# force reload environment variables
load_dotenv(override=True)

class DatabaseConnection:
    """Manages PostgreSQL connection pool single responsibility"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
        
        # load config from environment PostgreSQL format
        # try multiple environment variable naming conventions
        self.database_url = os.getenv('DATABASE_URL')
        
        # parse individual components support both naming conventions
        self.config = {
            'host': os.getenv('PG_DB_HOST') or os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('PG_DB_PORT') or os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('PG_DB_USER') or os.getenv('POSTGRES_USER', 'partselect_user'),
            'password': os.getenv('PG_DB_PASSWORD') or os.getenv('POSTGRES_PASSWORD', 'your_secure_db_password'),
            'database': os.getenv('PG_DB_NAME') or os.getenv('POSTGRES_DATABASE', 'partselect_db')
        }
        
        # build DATABASE_URL if not provided
        if not self.database_url:
            self.database_url = f"postgresql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
    
    async def initialize(self):
        """Create connection pool"""
        try:
            # try to connect using DATABASE_URL first then fall back to individual config
            try:
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=5,
                    max_size=20
                )
            except Exception as e:
                self.logger.warning(f"DATABASE_URL connection failed {e} trying individual config")
                # fallback to individual config
                self.pool = await asyncpg.create_pool(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    min_size=5,
                    max_size=20
                )
            
            self.logger.info("PostgreSQL connection pool initialized")
            
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed {e}")
            self.logger.error(f"Tried DATABASE_URL {self.database_url}")
            self.logger.error(f"Config {self.config}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("PostgreSQL connection pool closed")
    
    def get_pool(self) -> Pool:
        """Get the connection pool"""
        if not self.pool:
            raise RuntimeError("Database not initialized Call initialize() first")
        return self.pool

# global connection instance
db_connection = DatabaseConnection()

async def get_db_pool() -> Pool:
    """Get database connection pool for dependency injection"""
    if not db_connection.pool:
        await db_connection.initialize()
    return db_connection.get_pool()
