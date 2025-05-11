"""
ExplorAstur - Web scrapers for events in Asturias.
"""

from scrapers.base import EventScraper
from scrapers.biodevas import BiodevasScraper
from scrapers.telecable import TelecableScraper
from scrapers.aviles import AvilesEventsScraper
from scrapers.visit_oviedo import VisitOviedoScraper
from scrapers.turismo_asturias import TurismoAsturiaScraper
from scrapers.oviedo_announcements import OviedoAnnouncementsScraper

# Export all scrapers
__all__ = [
    'EventScraper',
    'BiodevasScraper',
    'TelecableScraper',
    'VisitOviedoScraper',
    'AvilesEventsScraper',
    'TurismoAsturiaScraper',
    'OviedoAnnouncementsScraper',
]