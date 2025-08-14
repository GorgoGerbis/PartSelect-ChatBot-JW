"""
Configuration settings for the backend
Uses pydantic for validation and env vars
"""
import os
from pathlib import Path
from typing import Tuple, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# load env vars
load_dotenv()

class DatabaseConfig(BaseSettings):
    # database connection settings
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5434, env="DB_PORT")
    name: str = Field(default="partselect_db", env="DB_NAME")
    user: str = Field(default="partselect", env="DB_USER")
    password: str = Field(default="password", env="DB_PASSWORD")
    
    @property
    def url(self) -> str:
        # generate database URL
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class APIConfig(BaseSettings):
    """API keys and external service configuration."""
    
    deepseek_api_key: Optional[str] = Field(env="DEEPSEEK_API_KEY")
    openai_api_key: Optional[str] = Field(env="OPENAI_API_KEY")
    
    @validator('deepseek_api_key')
    def validate_deepseek_key(cls, v):
        if not v:
            raise ValueError("DEEPSEEK_API_KEY is required")
        return v
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v


class ServerConfig(BaseSettings):
    """Server configuration for MCP and FastAPI."""
    
    # MCP Server
    mcp_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    mcp_port: int = Field(default=8001, env="MCP_SERVER_PORT")
    
    # FastAPI Orchestrator
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")


class ScraperConfig(BaseSettings):
    """Web scraper configuration."""
    
    base_url: str = "https://www.partselect.com"
    categories: List[str] = ["Dishwasher", "Refrigerator"]
    wait_time_min: int = 2
    wait_time_max: int = 5
    max_retries: int = 3
    timeout: int = 30
    max_details_per_brand: int = 3
    
    @property
    def wait_time(self) -> Tuple[int, int]:
        """Get wait time tuple."""
        return (self.wait_time_min, self.wait_time_max)


class VectorConfig(BaseSettings):
    """Vector search configuration."""
    
    embedding_model: str = "text-embedding-ada-002"
    vector_dimension: int = 1536  # OpenAI ada-002 embedding dimension
    faiss_index_type: str = "IndexFlatL2"


class ChatConfig(BaseSettings):
    """Chat system configuration."""
    
    max_conversation_history: int = 10
    streaming_chunk_size: int = 1024
    default_temperature: float = 0.7
    max_tokens: int = 2000


class FileConfig(BaseSettings):
    """File paths and naming patterns."""
    
    # Base paths
    backend_dir: Path = Path(__file__).parent
    project_root: Path = backend_dir.parent
    web_scraper_dir: Path = backend_dir / "web_scraper"
    data_dir: Path = backend_dir / "data"  # Changed to backend/data
    backup_dir: Path = backend_dir / "data_backup"
    
    # File patterns
    parts_file_pattern: str = "{brand}-{category}-Parts.json"
    models_file_pattern: str = "models_with_details.json"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class DevelopmentConfig(BaseSettings):
    """Development and testing settings."""
    
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")


class PartSelectConfig(BaseSettings):
    """Main configuration class combining all settings."""
    
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    server: ServerConfig = ServerConfig()
    scraper: ScraperConfig = ScraperConfig()
    vector: VectorConfig = VectorConfig()
    chat: ChatConfig = ChatConfig()
    files: FileConfig = FileConfig()
    logging: LoggingConfig = LoggingConfig()
    dev: DevelopmentConfig = DevelopmentConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = PartSelectConfig()
