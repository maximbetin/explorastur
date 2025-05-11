#!/usr/bin/env python3
"""
ExplorAstur - Simple Telecable event scraper for Asturias
---------------------------------------------------------
Main script that runs the scraper and outputs events to a markdown file.
"""

import os
import datetime
import logging
import sys
from scrapers import TelecableScraper
from processor import EventProcessor

# Create directories
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Configure logging
logger = logging.getLogger('explorastur')
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # Add file handler
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/explorastur_{today}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")

def main():
    """Main execution function."""
    logger.info("Starting ExplorAstur - Telecable events scraper")

    try:
        # Create scraper
        scraper = TelecableScraper()

        # Scrape events
        events = scraper.scrape()

        if not events:
            logger.warning("No events found")
            return

        logger.info(f"Found {len(events)} events")

        # Process events
        processor = EventProcessor()
        filtered_events = processor.process_events(events)

        # Format to markdown
        markdown = processor.format_to_markdown(filtered_events)

        # Write to file
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        output_file = f'output/events_{date_str}.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Exported {len(filtered_events)} events to {output_file}")
        logger.info("ExplorAstur completed successfully")

    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()