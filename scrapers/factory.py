"""
Scraper factory module.

This module provides a factory for creating scraper instances
based on configuration.
"""

import logging
import importlib
import traceback
from typing import Dict, Any, List, Type, Optional, Tuple, cast

from scrapers.base import EventScraper
from scrapers.config import get_scraper_configs, get_config_for_scraper

logger = logging.getLogger('explorastur')

# Map of scraper IDs to class names and module paths
SCRAPER_REGISTRY = {
    "biodevas": {
        "class_name": "BiodevasScraper",
        "module_path": "scrapers.biodevas"
    },
    "telecable": {
        "class_name": "TelecableScraper",
        "module_path": "scrapers.telecable"
    },
    "aviles": {
        "class_name": "AvilesEventsScraper",
        "module_path": "scrapers.aviles"
    },
    "visit_oviedo": {
        "class_name": "VisitOviedoScraper",
        "module_path": "scrapers.visit_oviedo"
    },
    "turismo_asturias": {
        "class_name": "TurismoAsturiasScraper",
        "module_path": "scrapers.turismo_asturias"
    },
    "oviedo_announcements": {
        "class_name": "OviedoAnnouncementsScraper",
        "module_path": "scrapers.oviedo_announcements"
    },
}

def get_scraper_class(scraper_id: str) -> Optional[Type[EventScraper]]:
    """
    Get the scraper class for a given scraper ID.

    Args:
        scraper_id: The ID of the scraper (e.g., "telecable")

    Returns:
        Scraper class or None if not found
    """
    if scraper_id not in SCRAPER_REGISTRY:
        logger.error(f"No scraper registration found for ID: {scraper_id}")
        return None

    scraper_info = SCRAPER_REGISTRY[scraper_id]
    class_name = scraper_info["class_name"]
    module_path = scraper_info["module_path"]

    try:
        module = importlib.import_module(module_path)
        scraper_class = getattr(module, class_name)
        return cast(Type[EventScraper], scraper_class)
    except ImportError as e:
        logger.error(f"Error importing module {module_path}: {e}")
        logger.debug(f"Import traceback: {traceback.format_exc()}")
        return None
    except AttributeError as e:
        logger.error(f"Class {class_name} not found in module {module_path}: {e}")
        return None

def create_scraper(scraper_id: str) -> Optional[EventScraper]:
    """
    Create a scraper instance based on its ID.

    Args:
        scraper_id: The ID of the scraper (e.g., "telecable")

    Returns:
        Scraper instance or None if creation failed
    """
    scraper_class = get_scraper_class(scraper_id)
    if not scraper_class:
        return None

    try:
        # Get configuration for this scraper
        config = get_config_for_scraper(scraper_id)

        # Create scraper instance
        scraper = scraper_class(config)

        # Verify it's a valid EventScraper instance
        if not isinstance(scraper, EventScraper):
            logger.error(f"Created object for {scraper_id} is not an EventScraper instance")
            return None

        return scraper
    except Exception as e:
        logger.error(f"Error creating scraper for {scraper_id}: {e}")
        logger.debug(f"Creation traceback: {traceback.format_exc()}")
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
        else:
            logger.warning(f"Failed to create scraper: {config['name']} ({scraper_id})")

    logger.info(f"Created {len(scrapers)} scrapers out of {len(configs)} configurations")
    return scrapers

def register_scraper(
    scraper_id: str,
    class_name: str,
    module_path: str
) -> bool:
    """
    Register a new scraper type.

    This function can be used to dynamically register new scraper types
    without modifying the SCRAPER_REGISTRY dictionary directly.

    Args:
        scraper_id: Unique identifier for the scraper
        class_name: Name of the scraper class
        module_path: Full module path to the scraper

    Returns:
        True if registration was successful, False otherwise
    """
    if scraper_id in SCRAPER_REGISTRY:
        logger.warning(f"Scraper ID '{scraper_id}' already registered. Skipping.")
        return False

    # Add to registry
    SCRAPER_REGISTRY[scraper_id] = {
        "class_name": class_name,
        "module_path": module_path
    }

    # Verify it can be imported
    try:
        scraper_class = get_scraper_class(scraper_id)
        if not scraper_class:
            logger.error(f"Failed to load newly registered scraper: {scraper_id}")
            # Remove from registry if it can't be loaded
            del SCRAPER_REGISTRY[scraper_id]
            return False
        return True
    except Exception as e:
        logger.error(f"Exception while verifying new scraper {scraper_id}: {e}")
        # Remove from registry on error
        del SCRAPER_REGISTRY[scraper_id]
        return False