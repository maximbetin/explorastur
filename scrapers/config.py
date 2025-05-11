"""
Configuration for scrapers.

This module contains all scraper configurations and settings centralized in one place.
It provides functions to access configurations with proper defaults and validation.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, cast

logger = logging.getLogger('explorastur.config')

# Type alias for configuration dictionaries
ScraperConfig = Dict[str, Any]

# Global scraper settings - default for all scrapers
GLOBAL_SETTINGS: ScraperConfig = {
    # Request settings
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,  # seconds
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    },

    # Pagination settings
    "max_pages": 3,

    # Output settings
    "output_dir": os.path.join(os.getcwd(), "output"),

    # Default source name if not specified
    "name": "Generic",

    # Default URL if not specified
    "url": "",

    # Default enabled state
    "enabled": True,
}

# Site-specific configurations - only specify values that differ from GLOBAL_SETTINGS
SITE_CONFIGS: Dict[str, ScraperConfig] = {
    "telecable": {
        "name": "Telecable",
        "url": "https://blog.telecable.es/agenda-planes-asturias/",
        "base_url": "https://blog.telecable.es",
    },

    "turismo_asturias": {
        "name": "Turismo Asturias",
        "url": "https://www.turismoasturias.es/agenda-de-asturias",
        "base_url": "https://www.turismoasturias.es",
    },

    "visit_oviedo": {
        "name": "Visit Oviedo",
        "url": "https://www.visitoviedo.info/agenda",
        "base_url": "https://www.visitoviedo.info",
    },

    "biodevas": {
        "name": "Biodevas",
        "url": "https://biodevas.org/",
        "base_url": "https://biodevas.org",
    },

    "aviles": {
        "name": "Avilés",
        "url": "https://aviles.es/es/proximos-eventos",
        "base_url": "https://aviles.es",
    },

    "oviedo_announcements": {
        "name": "Centros Sociales Oviedo",
        "url": "https://www.oviedo.es/centrossociales/avisos",
        "base_url": "https://www.oviedo.es",
    },
}

def validate_config(config: ScraperConfig) -> bool:
    """
    Validate a scraper configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    required_fields = ["name", "url"]

    for field in required_fields:
        if field not in config or not config[field]:
            logger.error(f"Missing required configuration field: {field}")
            return False

    # If base_url is not specified, try to derive it from URL
    if "base_url" not in config or not config["base_url"]:
        url = config.get("url", "")
        if url and "//" in url:
            url_parts = url.split("/")
            if len(url_parts) >= 3:
                base_url = url_parts[0] + "//" + url_parts[2]
                config["base_url"] = base_url
                logger.info(f"Derived base_url: {base_url} from URL: {url}")

    return True

def get_scraper_configs() -> List[ScraperConfig]:
    """
    Get configurations for all enabled scrapers.

    Returns:
        List of configuration dictionaries for enabled scrapers
    """
    configs = []
    for key, config in SITE_CONFIGS.items():
        # Check if the scraper is enabled (default to global setting if not specified)
        is_enabled = config.get("enabled", GLOBAL_SETTINGS["enabled"])

        if is_enabled:
            # Merge global settings with site-specific config
            full_config = {**GLOBAL_SETTINGS, **config, "id": key}

            # Validate the configuration
            if validate_config(full_config):
                configs.append(full_config)
            else:
                logger.warning(f"Invalid configuration for scraper: {key}, skipping")

    return configs

def get_config_for_scraper(scraper_id: str) -> ScraperConfig:
    """
    Get configuration for a specific scraper.

    Args:
        scraper_id: ID of the scraper (e.g., "telecable")

    Returns:
        Complete configuration dictionary for the scraper

    Raises:
        ValueError: If no configuration is found for the given scraper_id
    """
    if scraper_id not in SITE_CONFIGS:
        raise ValueError(f"No configuration found for scraper: {scraper_id}")

    # Merge global settings with site-specific config
    config = {**GLOBAL_SETTINGS, **SITE_CONFIGS[scraper_id], "id": scraper_id}

    # Validate the configuration
    if not validate_config(config):
        logger.warning(f"Invalid configuration for scraper: {scraper_id}, using anyway")

    return config

def get_default_config() -> ScraperConfig:
    """
    Get the default configuration for when no specific config is provided.

    Returns:
        Default configuration dictionary
    """
    return {**GLOBAL_SETTINGS}

def register_config(scraper_id: str, config: ScraperConfig) -> bool:
    """
    Register a new scraper configuration.

    Args:
        scraper_id: Unique identifier for the scraper
        config: Configuration dictionary for the scraper

    Returns:
        True if registration was successful, False otherwise
    """
    if scraper_id in SITE_CONFIGS:
        logger.warning(f"Configuration for '{scraper_id}' already exists. Overwriting.")

    # Validate the configuration before adding
    full_config = {**GLOBAL_SETTINGS, **config, "id": scraper_id}
    if not validate_config(full_config):
        logger.error(f"Invalid configuration for scraper: {scraper_id}, not registering")
        return False

    # Add to site configs
    SITE_CONFIGS[scraper_id] = config
    logger.info(f"Registered configuration for scraper: {scraper_id}")
    return True