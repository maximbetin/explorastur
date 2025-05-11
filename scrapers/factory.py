"""
Scraper factory module.

This module provides a factory for creating scraper instances
based on configuration.
"""

import logging
import importlib
from typing import Dict, Any, List, Type, Optional, Tuple

from scrapers.base import EventScraper
from scrapers.config import get_scraper_configs, get_config_for_scraper

logger = logging.getLogger('explorastur')

# Map of scraper IDs to class names
SCRAPER_CLASS_MAP = {
    "telecable": "TelecableScraper",
    "turismo_asturias": "TurismoAsturiaScraper",
    "oviedo_centros_sociales": "OviedoCentrosSocialesScraper",
    "visit_oviedo": "VisitOviedoScraper",
    "biodevas": "BiodevasScraper",
    "aviles": "AvilesEventsScraper",
}

def get_scraper_class(scraper_id: str) -> Optional[Type[EventScraper]]:
    """
    Get the scraper class for a given scraper ID.

    Args:
        scraper_id: The ID of the scraper (e.g., "telecable")

    Returns:
        Scraper class or None if not found
    """
    if scraper_id not in SCRAPER_CLASS_MAP:
        logger.error(f"No scraper class mapping found for ID: {scraper_id}")
        return None

    class_name = SCRAPER_CLASS_MAP[scraper_id]
    module_name = f"scrapers.{scraper_id}"

    try:
        module = importlib.import_module(module_name)
        scraper_class = getattr(module, class_name)
        return scraper_class
    except (ImportError, AttributeError) as e:
        logger.error(f"Error loading scraper class {class_name} from {module_name}: {e}")
        return None

def create_scraper(scraper_id: str) -> Optional[EventScraper]:
    """
    Create a scraper instance based on its ID.

    Args:
        scraper_id: The ID of the scraper (e.g., "telecable")

    Returns:
        Scraper instance or None if not found
    """
    scraper_class = get_scraper_class(scraper_id)
    if not scraper_class:
        return None

    try:
        # Get configuration for this scraper
        config = get_config_for_scraper(scraper_id)
        # Create scraper instance
        return scraper_class(config)
    except Exception as e:
        logger.error(f"Error creating scraper for {scraper_id}: {e}")
        return None

def create_all_scrapers() -> List[Tuple[str, EventScraper]]:
    """
    Create instances of all enabled scrapers.

    Returns:
        List of tuples containing (name, scraper_instance)
    """
    scrapers = []
    configs = get_scraper_configs()

    for config in configs:
        scraper_id = config["id"]
        logger.info(f"Creating scraper: {config['name']} ({scraper_id})")

        scraper = create_scraper(scraper_id)
        if scraper:
            scrapers.append((config["name"], scraper))

    return scrapers