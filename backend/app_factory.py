"""
App factory for creating different app configurations

Started simple then kept adding modes as needed
TODO: probably should refactor this at some point
"""

import os
import logging
from typing import Optional

from providers.interfaces import PartSelectApp
from providers.data.csv_provider import CSVDataProvider
from providers.search.simple_search import SimpleSearchProvider
from providers.llm.deepseek_provider import DeepSeekProvider

# TODO: move this to a proper config system
logger = logging.getLogger(__name__)

class AppFactory:
    """Factory for creating different app configurations based on available resources"""
    
    @staticmethod
    async def create_app(mode: str = None) -> PartSelectApp:
        """Main entry point, figures out what mode to use"""
        if mode is None:
            mode = os.getenv("APP_MODE", "simple").lower()
        
        logger.info(f"Initializing app in '{mode}' mode")
        
        # NOTE: added these modes incrementally as we built features
        if mode == "simple":
            return await AppFactory.create_simple_app()
        elif mode == "vector":
            return await AppFactory.create_vector_app()
        elif mode == "advanced":
            return await AppFactory.create_advanced_app()
        else:
            # fallback for typos or invalid modes  
            logger.warning(f"Unknown mode '{mode}' using simple instead")
            return await AppFactory.create_simple_app()
    
    @staticmethod
    async def create_simple_app() -> PartSelectApp:
        """Basic setup with CSV files and keyword search"""
        logger.info("Setting up simple app (CSV + keyword search)")
        
        try:
            # basic providers, just get something working
            data_provider = CSVDataProvider()
            search_provider = SimpleSearchProvider(data_provider)
            llm_provider = DeepSeekProvider()
            
            app = PartSelectApp(search_provider, data_provider, llm_provider)
            
            success = await app.initialize()
            if not success:
                raise RuntimeError("App initialization failed")
            
            # quick stats check
            logger.info("Simple app ready")
            logger.debug(f"Data provider stats: {data_provider.get_stats()}")
            # logger.debug(f"Search stats: {search_provider.get_stats()}")  # sometimes this fails
            
            return app
            
        except Exception as e:
            logger.error(f"Simple app creation failed: {e}")
            raise
    
    @staticmethod  
    async def create_vector_app() -> PartSelectApp:
        """Vector search version, needs OpenAI API key"""
        logger.info("Trying to set up vector search app")
        
        # check if we have what we need
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("No OPENAI_API_KEY found cant do vector search")
            return await AppFactory.create_simple_app()
        
        try:
            from providers.search.openai_vector_search import OpenAIVectorSearchProvider
        except ImportError as import_err:
            logger.warning(f"Vector search imports failed: {import_err}")
            logger.info("Probably need to pip install langchain openai faiss cpu")
            return await AppFactory.create_simple_app()
        
        try:
            data_provider = CSVDataProvider()
            search_provider = OpenAIVectorSearchProvider(data_provider)
            llm_provider = DeepSeekProvider()
            
            app = PartSelectApp(search_provider, data_provider, llm_provider)
            
            init_success = await app.initialize()
            if not init_success:
                logger.warning("Vector app init failed falling back")
                return await AppFactory.create_simple_app()
            
            logger.info("Vector app is ready")
            return app
            
        except Exception as e:
            logger.error(f"Vector app setup error: {e}")
            return await AppFactory.create_simple_app()
    
    @staticmethod
    async def create_advanced_app() -> PartSelectApp:
        """Advanced mode with PostgreSQL + vector search if available"""
        logger.info("Attempting advanced app setup")
        
        # check what we have available
        db_url = os.getenv("DATABASE_URL")
        openai_key = os.getenv("OPENAI_API_KEY") 
        
        missing = []
        if not db_url:
            missing.append("DATABASE_URL")
        if not openai_key:
            missing.append("OPENAI_API_KEY")
            
        if missing:
            logger.warning(f"Advanced mode needs {', '.join(missing)}")
            logger.info("Falling back to vector mode")
            return await AppFactory.create_vector_app()
        
        try:
            # try importing the advanced stuff
            from database.database import DatabaseManager
            from providers.search.openai_vector_search import OpenAIVectorSearchProvider
        except ImportError as e:
            logger.warning(f"Cant import advanced components {e}")
            return await AppFactory.create_vector_app()
        
        try:
            # set up the database connection
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Use PostgreSQL data provider for advanced mode
            from providers.data.database_provider import DatabaseDataProvider
            data_provider = DatabaseDataProvider(db_manager)  
            search_provider = OpenAIVectorSearchProvider(data_provider)
            llm_provider = DeepSeekProvider()
            
            # init everything
            await data_provider.initialize()
            await search_provider.initialize()
            
            app = PartSelectApp(
                search_provider=search_provider,
                data_provider=data_provider, 
                llm_provider=llm_provider
            )
            # Ensure app reports initialized state consistently
            await app.initialize()
            
            # attach the db manager for direct queries if needed
            app.db_manager = db_manager
            
            logger.info("Advanced app ready with PostgreSQL and vector search")
            return app
            
        except Exception as e:
            logger.error(f"Advanced setup failed: {e}")
            return await AppFactory.create_vector_app()
    
    @staticmethod
    def get_available_modes() -> list:
        """Check what modes we can actually run"""
        modes = ["simple"]  # this always works
        
        if os.getenv("OPENAI_API_KEY"):
            modes.append("vector")
        
        # advanced needs both  
        if os.getenv("OPENAI_API_KEY") and os.getenv("DATABASE_URL"):
            modes.append("advanced")
        
        return modes
    
    @staticmethod  
    def get_recommended_mode() -> str:
        """Figure out the best mode for current setup"""
        available = AppFactory.get_available_modes()
        
        # vector is usually the sweet spot
        if "vector" in available:
            return "vector"
        else:
            return "simple"
