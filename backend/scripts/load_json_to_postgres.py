import asyncio, json, os
from pathlib import Path
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://partselect:password@localhost:5432/partselect_db")

INSERT_SQL = """
INSERT INTO parts (
  partselect_number, manufacturer_number, name, description,
  price, brand, category, stock_status, rating, reviews_count,
  url, image_url, metadata
) VALUES (
  NULLIF($1, ''), $2, $3, $4,
  $5, $6, $7, $8, $9, $10,
  $11, $12, $13::jsonb
)
ON CONFLICT (partselect_number) DO UPDATE SET
  manufacturer_number = EXCLUDED.manufacturer_number,
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  price = EXCLUDED.price,
  brand = EXCLUDED.brand,
  category = EXCLUDED.category,
  stock_status = EXCLUDED.stock_status,
  rating = EXCLUDED.rating,
  reviews_count = EXCLUDED.reviews_count,
  url = EXCLUDED.url,
  image_url = EXCLUDED.image_url,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
"""

def s(v, default=""):  # helper function
    return str(v) if v is not None else default

async def load_file(conn, json_file: Path, brand: str, category: str):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    batch = []
    for part in data:
        if not isinstance(part, dict):
            # skip non object items, some files may include strings or other shapes
            continue
        # skip rows with no identifiers at all
        ps_num = part.get("partselect_number")
        mfg_num = part.get("manufacturer_number")
        if not (s(ps_num).strip() or s(mfg_num).strip()):
            continue
        batch.append((
            s(ps_num).strip(),
            part.get("manufacturer_number"),
            s(part.get("name"), "Unknown Part"),
            s(part.get("description"), ""),
            s(part.get("price"), ""),
            brand,
            category,
            s(part.get("stock_status"), "Unknown"),
            s(part.get("rating"), ""),
            int(part.get("reviews_count") or 0),
            s(part.get("url"), ""),
            s(part.get("image_url"), ""),
            json.dumps(part, ensure_ascii=False)
        ))
    if batch:
        await conn.executemany(INSERT_SQL, batch)
        return len(batch)
    return 0

async def main():
    data_dir = Path("data/json_data")
    if not data_dir.exists():
        raise FileNotFoundError(f"Missing {data_dir}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # clean table for a deterministic load
        await conn.execute("TRUNCATE TABLE parts;")

        total = 0
        for jf in sorted(data_dir.glob("*.json")):
            name = jf.stem.split("-")
            brand = name[0] if len(name) > 0 else ""
            category = name[1] if len(name) > 1 else ""
            try:
                total += await load_file(conn, jf, brand, category)
                print(f"Loaded {jf.name}")
            except Exception as e:
                print(f"Error loading {jf} {e}")
        print(f"Loaded {total} parts total")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
