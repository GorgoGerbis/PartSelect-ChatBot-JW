#!/usr/bin/env python3
"""
Script to merge JSON data with real PartSelect URLs into the CSV parts database
Updates part URLs with real PartSelect URLs from scraped data
"""

import json
import pandas as pd
import os
from pathlib import Path

def load_all_json_data():
    """Load all JSON files and create part_number -> real_url mapping"""
    json_dir = Path("data/json_data")
    part_url_mapping = {}
    
    print(f"Loading JSON files from {json_dir}")
    
    for json_file in json_dir.glob("*-Parts.json"):
        print(f"Processing {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                parts_data = json.load(f)
                
            for part in parts_data:
                part_number = part.get('partselect_number', '')
                real_url = part.get('url', '')
                
                if part_number and real_url and 'partselect.com' in real_url:
                    part_url_mapping[part_number] = real_url
                    
        except Exception as e:
            print(f"Error processing {json_file} {e}")
            continue
    
    print(f"Found {len(part_url_mapping)} parts with real PartSelect URLs")
    return part_url_mapping

def update_csv_with_real_urls():
    """Update CSV file with real PartSelect URLs"""
    
    # load the mapping
    url_mapping = load_all_json_data()
    
    # load current CSV
    csv_path = "data/parts_dataset.csv"
    print(f"Loading CSV {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"CSV has {len(df)} parts")
    
    # update URLs
    updated_count = 0
    for index, row in df.iterrows():
        part_id = row['part_id']
        
        if part_id in url_mapping:
            # update with real PartSelect URL
            df.at[index, 'product_url'] = url_mapping[part_id]
            updated_count += 1
    
    print(f"Updated {updated_count} part URLs")
    
    # save updated CSV
    backup_path = "data/parts_dataset_backup.csv"
    df.to_csv(backup_path, index=False)
    print(f"Backup saved to {backup_path}")
    
    df.to_csv(csv_path, index=False)
    print(f"Updated CSV saved to {csv_path}")
    
    # show some examples
    print("\nSample updated URLs")
    updated_parts = df[df['product_url'].str.contains('partselect.com', na=False)].head(5)
    for _, part in updated_parts.iterrows():
        print(f"  {part['part_id']} {part['product_url']}")

if __name__ == "__main__":
    # change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir.parent)  # go to backend directory
    
    print("Merging JSON data with CSV database")
    print("This will update part URLs with real PartSelect URLs from scraped data")
    
    try:
        update_csv_with_real_urls()
        print("Successfully updated parts database with real PartSelect URLs")
        
    except Exception as e:
        print(f"Error {e}")
        print("Make sure youre running from the backend directory")
