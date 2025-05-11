"""
ExplorAstur - Web scrapers for events in Asturias.

This package contains web scrapers that collect event information from
various sources in Asturias, Spain. The scrapers are designed to extract,
normalize, and structure event data in a consistent format.
"""

import logging
from typing import Dict, List, Optional, Type

# Import the base classes
from scrapers.base import EventScraper

# Import scraper implementations
from scrapers.biodevas import BiodevasScraper
from scrapers.telecable import TelecableScraper
from scrapers.aviles import AvilesEventsScraper
from scrapers.visit_oviedo import VisitOviedoScraper
from scrapers.turismo_asturias import TurismoAsturiaScraper
from scrapers.oviedo_announcements import OviedoAnnouncementsScraper

# Import factory for creating scraper instances
from scrapers.factory import create_scraper, create_all_scrapers, register_scraper

# Import consistency checking utilities
from scrapers.consistency_checker import check_all_scrapers, check_scraper_consistency

# Set up module logger
logger = logging.getLogger('explorastur.scrapers')

# Export all public classes and functions
__all__ = [
    # Base classes
    'EventScraper',

    # Scraper implementations
    'BiodevasScraper',
    'TelecableScraper',
    'AvilesEventsScraper',
    'VisitOviedoScraper',
    'TurismoAsturiaScraper',
    'OviedoAnnouncementsScraper',

    # Factory functions
    'create_scraper',
    'create_all_scrapers',
    'register_scraper',

    # Helper functions
    'get_available_scrapers',
    'run_scraper',
    'run_all_scrapers',

    # Consistency checking utilities
    'check_all_scrapers',
    'check_scraper_consistency',
]

def get_available_scrapers() -> List[str]:
    """
    Get a list of all available scraper IDs.

    Returns:
        List of scraper IDs that can be created
    """
    from scrapers.factory import SCRAPER_REGISTRY
    return list(SCRAPER_REGISTRY.keys())

def run_scraper(scraper_id: str) -> List[Dict[str, str]]:
    """
    Run a single scraper by ID and return the events.

    Args:
        scraper_id: ID of the scraper to run

    Returns:
        List of event dictionaries or empty list if scraper fails
    """
    scraper = create_scraper(scraper_id)
    if not scraper:
        logger.error(f"Failed to create scraper: {scraper_id}")
        return []

    try:
        logger.info(f"Running scraper: {scraper_id}")
        events = scraper.scrape()
        logger.info(f"Scraper {scraper_id} found {len(events)} events")
        return events
    except Exception as e:
        logger.error(f"Error running scraper {scraper_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def run_all_scrapers() -> Dict[str, List[Dict[str, str]]]:
    """
    Run all available scrapers and return events by source.

    Returns:
        Dictionary mapping source names to lists of event dictionaries
    """
    all_events = {}
    scrapers = create_all_scrapers()

    for name, scraper in scrapers:
        try:
            logger.info(f"Running scraper: {name}")
            events = scraper.scrape()
            logger.info(f"Scraper {name} found {len(events)} events")
            all_events[name] = events
        except Exception as e:
            logger.error(f"Error running scraper {name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            all_events[name] = []

    return all_events