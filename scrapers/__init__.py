"""
ExplorAstur - Web scrapers for events in Asturias.
"""

from scrapers.base import EventScraper
from scrapers.telecable import TelecableScraper
from scrapers.turismo_asturias import TurismoAsturiaScraper
from scrapers.visit_oviedo import VisitOviedoScraper
from scrapers.biodevas import BiodevasScraper
from scrapers.aviles import AvilesEventsScraper

# Export all scrapers
__all__ = [
    'EventScraper',
    'TelecableScraper',
    'TurismoAsturiaScraper',
    'VisitOviedoScraper',
    'BiodevasScraper',
    'AvilesEventsScraper',
]