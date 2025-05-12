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
from typing import List, Dict, Any, Optional

from scrapers.factory import create_all_scrapers, create_scraper
from processor import EventProcessor

# Constants
LOG_DIR = 'logs'
OUTPUT_DIR = 'output'
LOG_FORMAT = '[%(asctime)s] [%(levelname)s]: %(message)s'
DATE_FORMAT = '%H:%M:%S'

# Create necessary directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


class LogFilter(logging.Filter):
    """Filter to clean up log output by removing verbose pagination URLs and other noise."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Skip long pagination URLs
        if "?p_p_id=" in getattr(record, 'msg', "") or "/-/calendars/week/" in getattr(record, 'msg', ""):
            return False

        # Skip verbose "Fetching page" messages in INFO mode
        if record.levelno == logging.INFO and "Fetching page" in getattr(record, 'msg', ""):
            return False

        # Always allow ERROR and WARNING messages
        if record.levelno in (logging.ERROR, logging.WARNING):
            return True

        return True


def setup_logging(debug: bool = False, verbose: bool = False) -> logging.Logger:
    """
    Configure and return the logger with appropriate settings.

    Args:
        debug: Whether to enable debug logging
        verbose: Whether to show all log messages including pagination details

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('explorastur')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers.clear()

    # Add console handler with filter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    if not verbose:
        console_handler.addFilter(LogFilter())

    logger.addHandler(console_handler)

    # Add file handler (keep all details in the file)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = f'{LOG_DIR}/explorastur_{today}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    logger.info(f"Logging to file: {log_file}")
    return logger


def parse_args() -> argparse.Namespace:
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

    parser.add_argument(
        "--verbose", "-v",
        dest="verbose",
        action="store_true",
        help="Show all log messages including pagination details",
        default=False
    )

    return parser.parse_args()


def run_scrapers(scraper_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Run the specified scrapers or all enabled scrapers if none specified.

    Args:
        scraper_ids: Optional list of scraper IDs to run

    Returns:
        List of collected events
    """
    logger = logging.getLogger('explorastur')
    all_events = []

    # If specific scrapers are requested, only run those
    if scraper_ids:
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
        try:
            events = scraper.scrape()

            if not events:
                logger.warning(f"No events found from {name}")
                continue

            logger.info(f"Found {len(events)} events from {name}")
            all_events.extend(events)
        except Exception as e:
            logger.error(f"Error running {name} scraper: {e}")
            import traceback
            logger.error(traceback.format_exc())

    return all_events


def process_and_save_events(events: List[Dict[str, Any]], output_file: Optional[str] = None) -> None:
    """
    Process events and save them to the output file.

    Args:
        events: List of events to process
        output_file: Optional output file path
    """
    logger = logging.getLogger('explorastur')

    if not events:
        logger.warning("No events to process")
        return

    logger.info(f"Processing {len(events)} events")

    # Process events (filter, clean, etc.)
    processor = EventProcessor()
    filtered_events = processor.process_events(events)

    if not filtered_events:
        logger.warning("No events remaining after filtering")
        return

    # Format to markdown
    markdown = processor.format_to_markdown(filtered_events)

    # Determine output file
    if not output_file:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        output_file = f'{OUTPUT_DIR}/events_{date_str}.md'

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    logger.info(f"Exported {len(filtered_events)} events to {output_file}")


def main() -> None:
    """
    Main execution function.

    Runs all scrapers, processes the collected events, and outputs them to a markdown file.
    The function handles errors gracefully and logs the process along the way.
    """
    # Parse command line arguments
    args = parse_args()

    # Set up logging
    logger = setup_logging(debug=args.debug, verbose=args.verbose)

    logger.info("Starting ExplorAstur - Event scrapers")

    try:
        # Parse scraper IDs if provided
        scraper_ids = [s.strip() for s in args.scraper_ids.split(",")] if args.scraper_ids else None

        # Run scrapers
        all_events = run_scrapers(scraper_ids)

        # Process and save events
        process_and_save_events(all_events, args.output_file)

        logger.info("ExplorAstur completed successfully")

    except Exception as e:
        logger.error(f"Error running scrapers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()