#!/usr/bin/env python3
"""
ExplorAstur - Simple event scraper for Asturias tourism websites
---------------------------------------------------------
Main script that runs the scrapers and outputs events to a markdown file.
"""

import os
import datetime
import logging
import sys
import argparse
from scrapers.factory import create_all_scrapers, create_scraper
from processor import EventProcessor

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Configure logging
logger = logging.getLogger('explorastur')
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Custom log format
    log_format = '[%(asctime)s] [%(levelname)s]: %(message)s'
    date_format = '%H:%M:%S'

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    # Add file handler
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/explorastur_{today}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ExplorAstur - Event scraper for Asturias tourism websites"
    )

    parser.add_argument(
        "--scraper", "-s",
        dest="scraper_ids",
        help="Comma-separated list of scraper IDs to run (e.g., 'telecable,aviles')",
        default=""
    )

    parser.add_argument(
        "--output", "-o",
        dest="output_file",
        help="Output file path (default: output/events_YYYY-MM-DD.md)",
        default=""
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug logging",
        default=False
    )

    return parser.parse_args()

def main():
    """
    Main execution function.

    Runs all scrapers, processes the collected events, and outputs them to a markdown file.
    The function handles errors gracefully and logs the process along the way.
    """
    # Parse command line arguments
    args = parse_args()

    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    logger.info("Starting ExplorAstur - Event scrapers")
    all_events = []

    try:
        # If specific scrapers are requested, only run those
        if args.scraper_ids:
            scraper_ids = [s.strip() for s in args.scraper_ids.split(",")]
            logger.info(f"Running specific scrapers: {', '.join(scraper_ids)}")

            scrapers = []
            for scraper_id in scraper_ids:
                scraper = create_scraper(scraper_id)
                if scraper:
                    scrapers.append((scraper.source_name, scraper))
                else:
                    logger.warning(f"Scraper '{scraper_id}' not found or could not be created")
        else:
            # Otherwise, run all enabled scrapers from the configuration
            logger.info("Running all enabled scrapers")
            scrapers = create_all_scrapers()

        # Log the scrapers we're going to run
        logger.info(f"Scrapers to run: {[name for name, _ in scrapers]}")

        # Run each scraper and collect events
        for name, scraper in scrapers:
            logger.info(f"Running {name} scraper")
            events = scraper.scrape()

            if not events:
                logger.warning(f"No events found from {name}")
                continue

            logger.info(f"Found {len(events)} events from {name}")
            all_events.extend(events)

        # Check if we found any events
        if not all_events:
            logger.warning("No events found from any source")
            return

        logger.info(f"Total events collected: {len(all_events)}")

        # Process events (filter, clean, etc.)
        processor = EventProcessor()
        filtered_events = processor.process_events(all_events)

        # Format to markdown
        markdown = processor.format_to_markdown(filtered_events)

        # Determine output file
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        output_file = args.output_file if args.output_file else f'output/events_{date_str}.md'

        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Exported {len(filtered_events)} events to {output_file}")
        logger.info("ExplorAstur completed successfully")

    except Exception as e:
        logger.error(f"Error running scrapers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()