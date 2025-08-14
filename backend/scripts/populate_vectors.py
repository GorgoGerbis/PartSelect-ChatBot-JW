#!/usr/bin/env python3
"""
Build FAISS indexes from CSV data for semantic search
Intended to run offline during setup
"""

import asyncio
import os
import sys
import pandas as pd
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

# add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorPopulator:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.vector_dir = Path(__file__).parent.parent / "vector_stores"
        self.vector_dir.mkdir(exist_ok=True)
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            sys.exit(1)
        
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Vector store directory: {self.vector_dir}")
    
    async def generate_embeddings(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """Generate OpenAI embeddings for texts"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_api_key)
        except ImportError:
            logger.error("OpenAI library not installed Run pip install openai")
            sys.exit(1)
        
        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        # print(f"DEBUG: batch_size={batch_size}, total_batches={total_batches}")  # debug
        logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                logger.info(f"Processing batch {batch_num}/{total_batches}")
                
                response = await client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=batch
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                await asyncio.sleep(0.1)  # rate limit
                
            except Exception as e:
                logger.error(f"Error in batch {batch_num}: {e}")
                zero_embedding = [0.0] * 1536  # fallback
                embeddings.extend([zero_embedding] * len(batch))
        
        return embeddings
    
    def create_faiss_index(self, embeddings: List[List[float]]) -> Any:
        """Create FAISS index from embeddings"""
        try:
            import faiss
        except ImportError:
            logger.error("FAISS library not installed Run pip install faiss-cpu")
            sys.exit(1)
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # normalize for cosine similarity
        faiss.normalize_L2(embeddings_array)
        index.add(embeddings_array)
        
        logger.info(f"Created FAISS index {index.ntotal} vectors dim {dimension}")
        return index
    
    def prepare_parts_data(self) -> tuple[List[str], List[Dict[str, Any]]]:
        """Load and prepare parts data for vectorization"""
        parts_file = self.data_dir / "parts_dataset.csv"
        
        if not parts_file.exists():
            logger.error(f"Parts file not found {parts_file}")
            return [], []
        
        logger.info(f"Loading parts from {parts_file}")
        df = pd.read_csv(parts_file)
        parts_data = df.fillna("").to_dict('records')
        # TODO maybe add some data cleaning here later
        
        # create text for embedding
        texts = []
        for part in parts_data:
            text_parts = [
                part.get('part_name', ''),
                part.get('symptoms', ''),
                part.get('brand', ''),
                part.get('appliance_types', ''),
                f"Part ID {part.get('part_id', '')}",
                f"Price ${part.get('part_price', '')}"
            ]
            text = " | ".join([p for p in text_parts if p.strip()])
            texts.append(text)
        
        logger.info(f"Prepared {len(texts)} parts for vectorization")
        return texts, parts_data
    
    def prepare_repairs_data(self) -> tuple[List[str], List[Dict[str, Any]]]:
        """Load and prepare repair data"""
        repair_files = [
            self.data_dir / "dishwasher_repairs.csv",
            self.data_dir / "refrigerator_repairs.csv"
        ]
        
        all_repairs = []
        for repair_file in repair_files:
            if repair_file.exists():
                df = pd.read_csv(repair_file)
                repairs = df.fillna("").to_dict('records')
                all_repairs.extend(repairs)
                logger.info(f"Loaded {len(repairs)} repairs from {repair_file.name}")
        
        # create text for embedding  
        texts = []
        for repair in all_repairs:
            text_parts = [
                repair.get('symptom', ''),
                repair.get('Product', ''),
                repair.get('parts', ''),
                f"Difficulty {repair.get('difficulty', '')}"
            ]
            text = " | ".join([p for p in text_parts if p.strip()])
            texts.append(text)
        
        logger.info(f"Prepared {len(texts)} repairs for vectorization")
        return texts, all_repairs
    
    def prepare_blogs_data(self) -> tuple[List[str], List[Dict[str, Any]]]:
        """Load and prepare blog data"""
        blogs_file = self.data_dir / "partselect_blogs.csv"
        
        if not blogs_file.exists():
            logger.warning(f"Blog file not found {blogs_file}")
            return [], []
        
        df = pd.read_csv(blogs_file)
        blogs_data = df.fillna("").to_dict('records')
        
        # create text for embedding
        texts = []
        for blog in blogs_data:
            text_parts = [
                blog.get('title', ''),
                blog.get('description', ''),
                blog.get('content', '')[:300]  # first 300 chars
            ]
            text = " | ".join([p for p in text_parts if p.strip()])
            texts.append(text)
        
        logger.info(f"Prepared {len(texts)} blogs for vectorization")
        return texts, blogs_data
    
    async def populate_parts_vectors(self):
        """Generate and save parts vector index"""
        logger.info("Processing parts data")
        
        texts, data = self.prepare_parts_data()
        if not texts:
            return
        
        embeddings = await self.generate_embeddings(texts)
        index = self.create_faiss_index(embeddings)
        
        # save everything
        parts_dir = self.vector_dir / "parts"
        parts_dir.mkdir(exist_ok=True)
        
        import faiss
        faiss.write_index(index, str(parts_dir / "index.faiss"))
        
        with open(parts_dir / "metadata.pkl", 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Parts vectors saved {index.ntotal} items")
    
    async def populate_repairs_vectors(self):
        """Generate and save repairs vector index"""
        logger.info("Processing repairs data")
        
        texts, data = self.prepare_repairs_data()
        if not texts:
            return
        
        embeddings = await self.generate_embeddings(texts)
        index = self.create_faiss_index(embeddings)
        
        # save everything
        repairs_dir = self.vector_dir / "repairs"
        repairs_dir.mkdir(exist_ok=True)
        
        import faiss
        faiss.write_index(index, str(repairs_dir / "index.faiss"))
        
        with open(repairs_dir / "metadata.pkl", 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Repairs vectors saved {index.ntotal} items")
    
    async def populate_blogs_vectors(self):
        """Generate and save blogs vector index"""
        logger.info("Processing blogs data")
        
        texts, data = self.prepare_blogs_data()
        if not texts:
            return
        
        embeddings = await self.generate_embeddings(texts)
        index = self.create_faiss_index(embeddings)
        
        # save everything
        blogs_dir = self.vector_dir / "blogs"
        blogs_dir.mkdir(exist_ok=True)
        
        import faiss
        faiss.write_index(index, str(blogs_dir / "index.faiss"))
        
        with open(blogs_dir / "metadata.pkl", 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Blogs vectors saved {index.ntotal} items")
    
    async def run_all(self):
        """Run complete vector population process"""
        start_time = time.time()
        
        logger.info("Starting vector database population")
        logger.info("=" * 50)
        
        await self.populate_parts_vectors()
        await self.populate_repairs_vectors()
        await self.populate_blogs_vectors()
        
        duration = time.time() - start_time
        
        logger.info("=" * 50)
        logger.info(f"Vector population complete ({duration:.1f}s)")
        logger.info("Next steps")
        logger.info("1 Set APP_MODE=vector in env")
        logger.info("2 Restart server python main_modular.py") 
        logger.info("3 Test semantic search")

async def main():
    populator = VectorPopulator()
    await populator.run_all()
    # TODO add some error handling here maybe

if __name__ == "__main__":
    asyncio.run(main())