#!/usr/bin/env python3
"""
Load CSV data into PostgreSQL with correct column mapping
"""

import asyncio
import asyncpg
import pandas as pd
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5434/postgres")

async def create_parts_table():
    """Create parts table matching CSV structure"""
    
    create_table_sql = """
    DROP TABLE IF EXISTS parts CASCADE;
    
    CREATE TABLE parts (
        id SERIAL PRIMARY KEY,
        part_name TEXT,
        part_id VARCHAR(50) UNIQUE,
        mpn_id VARCHAR(50),
        part_price DECIMAL(10,2),
        install_difficulty VARCHAR(50),
        install_time VARCHAR(50),
        symptoms TEXT,
        appliance_types VARCHAR(100),
        replace_parts TEXT,
        brand VARCHAR(100),
        availability VARCHAR(50),
        install_video_url TEXT,
        product_url TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX idx_parts_part_id ON parts(part_id);
    CREATE INDEX idx_parts_brand ON parts(brand);
    CREATE INDEX idx_parts_appliance_types ON parts(appliance_types);
    """
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(create_table_sql)
        print("Parts table created successfully")
    finally:
        await conn.close()

async def load_csv_data():
    """Load CSV data into PostgreSQL"""
    
    # load CSV
    csv_path = "data/parts_dataset.csv"
    df = pd.read_csv(csv_path)
    print(f"Loading {len(df)} parts from CSV")
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # insert data with proper NaN handling
        for _, row in df.iterrows():
            await conn.execute("""
                INSERT INTO parts (
                    part_name, part_id, mpn_id, part_price, install_difficulty,
                    install_time, symptoms, appliance_types, replace_parts,
                    brand, availability, install_video_url, product_url
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (part_id) DO UPDATE SET
                    part_name = EXCLUDED.part_name,
                    product_url = EXCLUDED.product_url
            """, 
                str(row['part_name']) if pd.notna(row['part_name']) else '',
                str(row['part_id']) if pd.notna(row['part_id']) else '',
                str(row['mpn_id']) if pd.notna(row['mpn_id']) else '',
                float(row['part_price']) if pd.notna(row['part_price']) else 0.0,
                str(row['install_difficulty']) if pd.notna(row['install_difficulty']) else '',
                str(row['install_time']) if pd.notna(row['install_time']) else '',
                str(row['symptoms']) if pd.notna(row['symptoms']) else '',
                str(row['appliance_types']) if pd.notna(row['appliance_types']) else '',
                str(row['replace_parts']) if pd.notna(row['replace_parts']) else '',
                str(row['brand']) if pd.notna(row['brand']) else '',
                str(row['availability']) if pd.notna(row['availability']) else '',
                str(row['install_video_url']) if pd.notna(row['install_video_url']) else '',
                str(row['product_url']) if pd.notna(row['product_url']) else ''
            )
        
        print(f"Loaded {len(df)} parts into PostgreSQL")
        
        # verify
        count = await conn.fetchval("SELECT COUNT(*) FROM parts")
        print(f"Database now has {count} parts")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_parts_table())
    asyncio.run(load_csv_data())
