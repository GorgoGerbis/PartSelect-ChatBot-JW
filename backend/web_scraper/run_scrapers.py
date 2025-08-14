"""
Script to run the web scrapers
Can run individually or all together
"""
import sys
import os
import argparse
from pathlib import Path

# add parent to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import config

def run_blog_scraper():
    # run the blog scraper
    print("starting blog scraper...")
    from scrape_blog import main as blog_main
    blog_main()

def run_parts_scraper():
    # run the parts scraper
    print("starting parts scraper...")
    from scrape_parts import main as parts_main
    parts_main()

def run_repair_scraper():
    # run the repair scraper
    print("starting repair scraper...")
    from scrape_repair import main as repair_main
    repair_main()

def run_all_scrapers():
    """Run all the scrapers one after another."""
    print("=" * 80)
    print("Running All PartSelect Scrapers")
    print("=" * 80)
    print(f"Data goes to: {config.files.data_dir}")
    print()
    
    # Order: quick ones first, then the slow parts scraper
    scrapers = [
        ("Blog Articles", run_blog_scraper),
        ("Repair Guides", run_repair_scraper),
        ("Parts (this one takes forever)", run_parts_scraper)
    ]
    
    for i, (name, scraper_func) in enumerate(scrapers, 1):
        print(f"\n[{i}/{len(scrapers)}] Starting {name} scraper...")
        print("-" * 60)
        
        try:
            scraper_func()
            print(f"✅ {name} scraper done")
        except KeyboardInterrupt:
            print(f"\n❌ {name} scraper stopped by user")
            break
        except Exception as e:
            print(f"❌ {name} scraper failed: {e}")
            continue  # keep going with other scrapers
    
    print("\n" + "=" * 80)
    print("All done!")
    print("=" * 80)
    
    # Show what files we created
    if config.files.data_dir.exists():
        print(f"\nFiles created in {config.files.data_dir}:")
        for file in config.files.data_dir.glob("*.csv"):
            file_size = file.stat().st_size / 1024  # KB
            print(f"  📄 {file.name} ({file_size:.1f} KB)")

def main():
    """Main runner with command line arguments."""
    parser = argparse.ArgumentParser(
        description="PartSelect Web Scrapers Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scrapers.py --all          # Run all scrapers
  python run_scrapers.py --blog         # Run only blog scraper
  python run_scrapers.py --parts        # Run only parts scraper  
  python run_scrapers.py --repairs      # Run only repair scraper
        """
    )
    
    # Add mutually exclusive group for scraper selection
    scraper_group = parser.add_mutually_exclusive_group(required=True)
    scraper_group.add_argument('--all', action='store_true',
                              help='Run all scrapers in sequence')
    scraper_group.add_argument('--blog', action='store_true',
                              help='Run only the blog scraper')
    scraper_group.add_argument('--parts', action='store_true',
                              help='Run only the parts scraper')
    scraper_group.add_argument('--repairs', action='store_true',
                              help='Run only the repair scraper')
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    config.files.data_dir.mkdir(exist_ok=True)
    
    print("PartSelect Web Scrapers")
    print("=" * 50)
    print(f"Configuration loaded from: backend/config.py")
    print(f"Data directory: {config.files.data_dir}")
    print(f"Target categories: {', '.join(config.scraper.categories)}")
    print()
    
    # Run selected scraper(s)
    if args.all:
        run_all_scrapers()
    elif args.blog:
        run_blog_scraper()
    elif args.parts:
        run_parts_scraper()
    elif args.repairs:
        run_repair_scraper()

if __name__ == "__main__":
    main()
