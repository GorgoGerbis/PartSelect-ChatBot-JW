import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import logging

from ..interfaces import DataProvider

logger = logging.getLogger(__name__)

class CSVDataProvider(DataProvider):
    # loads CSV files and keeps them in memory for fast searching
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # default to backend/data directory
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.parts_data = []
        self.repairs_data = []
        self.blogs_data = []
        self._initialized = False
    
    async def initialize(self) -> bool:
        # load all the CSV files into memory for fast access
        try:
            logger.info(f"Loading CSV data from {self.data_dir}")
            
            # Load parts data
            parts_file = self.data_dir / "parts_dataset.csv"
            if parts_file.exists():
                df = pd.read_csv(parts_file)
                self.parts_data = df.fillna("").to_dict('records')
                logger.info(f"Loaded {len(self.parts_data)} parts from {parts_file.name}")
            else:
                logger.warning(f"Parts file not found: {parts_file}")
            
            # Load repair data
            repair_files = [
                self.data_dir / "dishwasher_repairs.csv",
                self.data_dir / "refrigerator_repairs.csv"
            ]
            
            for repair_file in repair_files:
                if repair_file.exists():
                    df = pd.read_csv(repair_file)
                    repairs = df.fillna("").to_dict('records')
                    self.repairs_data.extend(repairs)
                    logger.info(f"Loaded {len(repairs)} repairs from {repair_file.name}")
                else:
                    logger.warning(f"Repair file not found: {repair_file}")
            
            # Load blogs data (optional)
            blogs_file = self.data_dir / "partselect_blogs.csv"
            if blogs_file.exists():
                df = pd.read_csv(blogs_file)
                self.blogs_data = df.fillna("").to_dict('records')
                logger.info(f"Loaded {len(self.blogs_data)} blogs from {blogs_file.name}")
            else:
                logger.info("No blogs file found (optional)")
            
            self._initialized = True
            logger.info(f"CSV data provider initialized successfully")
            logger.info(f"  Parts: {len(self.parts_data)}")
            logger.info(f"  Repairs: {len(self.repairs_data)}")
            logger.info(f"  Blogs: {len(self.blogs_data)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CSV data provider: {e}")
            return False
    
    async def get_parts_data(self) -> List[Dict[str, Any]]:
        """Return loaded parts data"""
        if not self._initialized:
            await self.initialize()
        return self.parts_data
    
    async def get_repairs_data(self) -> List[Dict[str, Any]]:
        """Return loaded repairs data"""
        if not self._initialized:
            await self.initialize()
        return self.repairs_data
    
    async def get_blogs_data(self) -> List[Dict[str, Any]]:
        """Return loaded blogs data"""
        if not self._initialized:
            await self.initialize()
        return self.blogs_data
    
    def get_stats(self) -> Dict[str, int]:
        """Get data statistics for debugging"""
        return {
            "parts": len(self.parts_data),
            "repairs": len(self.repairs_data), 
            "blogs": len(self.blogs_data),
            "initialized": self._initialized
        }
