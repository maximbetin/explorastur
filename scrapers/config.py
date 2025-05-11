"""
Configuration for scrapers.

This module contains all scraper configurations and settings centralized in one place.
"""

import os
from typing import Dict, Any, List

# Global scraper settings
GLOBAL_SETTINGS = {
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
}

# Site-specific configurations
SITE_CONFIGS = {
    "telecable": {
        "name": "Telecable",
        "url": "https://blog.telecable.es/agenda-planes-asturias/",
        "enabled": True,
    },

    "turismo_asturias": {
        "name": "Turismo Asturias",
        "url": "https://www.turismoasturias.es/agenda-de-asturias",
        "enabled": True,
    },

    "visit_oviedo": {
        "name": "Visit Oviedo",
        "url": "https://www.visitoviedo.info/agenda",
        "enabled": True,
    },

    "biodevas": {
        "name": "Biodevas",
        "url": "https://biodevas.org/",
        "enabled": True,
    },

    "aviles": {
        "name": "Avilés",
        "url": "https://aviles.es/es/proximos-eventos",
        "enabled": True,
    },

    "oviedo_announcements": {
        "name": "Centros Sociales Oviedo",
        "url": "https://www.oviedo.es/centrossociales/avisos",
        "enabled": True,
    },
}

def get_scraper_configs() -> List[Dict[str, Any]]:
    """
    Get configurations for all enabled scrapers.

    Returns:
        List of configuration dictionaries for enabled scrapers
    """
    configs = []
    for key, config in SITE_CONFIGS.items():
        if config.get("enabled", True):
            # Merge global settings with site-specific config
            full_config = {**GLOBAL_SETTINGS, **config, "id": key}
            configs.append(full_config)
    return configs

def get_config_for_scraper(scraper_id: str) -> Dict[str, Any]:
    """
    Get configuration for a specific scraper.

    Args:
        scraper_id: ID of the scraper (e.g., "telecable")

    Returns:
        Complete configuration dictionary for the scraper
    """
    if scraper_id not in SITE_CONFIGS:
        raise ValueError(f"No configuration found for scraper: {scraper_id}")

    config = SITE_CONFIGS[scraper_id]
    return {**GLOBAL_SETTINGS, **config, "id": scraper_id}