"""
Scraper for Telecable blog events.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from typing import Dict, List, Optional, Any

from scrapers.base import EventScraper

logger = logging.getLogger('explorastur')

class TelecableScraper(EventScraper):
    """Scraper for Telecable blog."""

    def __init__(self, config=None):
        super().__init__(config)
        # Initialize scraper-specific attributes
        self.current_month_year = self.date_processor.get_current_month_year()

    def scrape(self):
        """Scrape events from Blog Telecable Asturias directly from HTML structure."""
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            # Use our new fetch method with retry logic
            html = self.fetch_page_with_retry(self.url)
            if not html:
                logger.error(f"Failed to fetch URL: {self.url}")
                return []

            soup = BeautifulSoup(html, 'html.parser')

            # Find the article body - this is the main content area
            article_body = soup.select_one('.article-body')
            if not article_body:
                logger.warning("No article body found with .article-body selector")

                # Try to find any article content
                article_body = soup.select_one('article') or soup.select_one('.post-content') or soup.select_one('.entry-content')
                if not article_body:
                    logger.error("Could not find any article content")
                    return []

            logger.info(f"Found article body with {len(list(article_body.children))} child elements")

            # Extract categories and their events
            categories = {}
            current_category = "General"

            # Find all h2 headers (category headers) and p tags (event details)
            for element in article_body.find_all(['h2', 'p']):
                if element.name == 'h2':
                    # Start a new category
                    current_category = element.get_text().strip()
                    logger.info(f"Found category: {current_category}")

                elif element.name == 'p':
                    # Look for paragraphs that start with bold text (typically event titles)
                    bold_elements = element.find_all(['b', 'strong'])
                    if bold_elements:
                        for bold in bold_elements:
                            title_text = bold.get_text().strip()

                            # Skip if it's not a proper event title
                            if not title_text or len(title_text) < 3:
                                continue

                            # Check if this is a date pattern like "2 de mayo: Event Name"
                            date_prefix_match = re.match(r'^(\d{1,2}\s+de\s+[a-zA-Z]+):\s*(.+)$', title_text)

                            if date_prefix_match:
                                date = date_prefix_match.group(1)
                                title = date_prefix_match.group(2).strip()
                            else:
                                # If no date prefix, use the entire bold text as title
                                title = title_text
                                # Try to extract date from paragraph text
                                date = self._extract_date("", element.get_text())

                            # Extract the full paragraph text for details
                            details = element.get_text().strip()

                            # Extract location and URL
                            location = self._extract_location(details)
                            url = self._extract_url(details) or self.url

                            # Create the event
                            event = self.create_event(
                                title=title,
                                date=date,
                                location=location,
                                url=url,
                                source="Telecable"
                            )

                            if event:
                                events.append(event)

            logger.info(f"Found {len(events)} events in {len(categories)} categories")
            return events

        except Exception as e:
            logger.error(f"Error scraping Telecable: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _parse_event(self, title, details, category):
        """Parse an event from its title and details text."""
        # Skip items that aren't events (like section headers)
        if len(title) < 3 or title.lower() in ['música', 'exposiciones', 'teatro', 'cine', 'talleres']:
            return None

        # Check if the title contains a colon, which typically separates the event name from details
        if ':' in title and title.index(':') > 0:
            # Split only on the first colon
            parts = title.split(':', 1)
            title = parts[0].strip()
            details = parts[1].strip() + " " + details.replace(title, "")

        # Check if the title contains a date pattern
        date_match = re.match(r'^(\d{1,2}\s+de\s+[a-zA-Z]+):\s*(.+)$', title)
        if date_match:
            date = date_match.group(1)
            title = date_match.group(2).strip()
        else:
            # Clean up the title - remove date patterns if they're in the title
            title = re.sub(r'^\d{1,2}\s+de\s+[a-zA-Z]+:\s*', '', title)
            title = self.text_processor.clean_title(title)

            # Extract date from the title or details
            date = self._extract_date(title, details)

        # Skip non-events like "Talleres" headers
        if self.text_processor.is_non_event(title):
            return None

        # Extract location from details
        location = self._extract_location(details)

        # Extract URL from details if it contains a link
        url = self._extract_url(details) or self.url

        # Create event with base class helper
        return self.create_event(
            title=title,
            date=date,
            location=location,
            url=url,
            source="Telecable"
        )

    def _extract_date(self, title, details):
        """Extract date information from title and details."""
        # Common date patterns
        date_patterns = [
            # "2 de mayo" or "2 de mayo:"
            r'(\d{1,2}\s+de\s+[a-zA-Z]+)(?:\s*:)?',
            # "2-3 de mayo" (date range)
            r'(\d{1,2}\s*[-y]\s*\d{1,2}\s+de\s+[a-zA-Z]+)',
            # Just day numbers like "2" at the beginning of a title
            r'^(\d{1,2})\s+de\s+[a-zA-Z]+',
            # "Del 2 al 5 de mayo"
            r'[Dd]el\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
            # "Durante todo el mes de mayo"
            r'[Dd]urante\s+todo\s+el\s+mes\s+de\s+([a-zA-Z]+)',
            # "Todo el mes de mayo"
            r'[Tt]odo\s+el\s+mes\s+de\s+([a-zA-Z]+)',
        ]

        # First check the title for a date
        for pattern in date_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(0)

        # Then check the details
        for pattern in date_patterns:
            match = re.search(pattern, details)
            if match:
                return match.group(0)

        # If no date found, use the current month
        return f"Todo el mes de {self.date_processor.get_current_month_name()}"

    def _extract_location(self, details):
        """Extract location information from details."""
        # Common location patterns
        location_patterns = [
            # Venues with specific names
            r'(?:en|En)\s+(?:el|la|los|las)?\s+((?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría|Museo|Recinto)\s+[^\.]+)',
            # "en Oviedo", "en Gijón", etc.
            r'(?:en|En)\s+((?:Oviedo|Gijón|Avilés|Villaviciosa|Llanera|Cabranes|Corvera)[^\.]+)',
            # Any location after "en" or "en el/la"
            r'(?:en|En)\s+(?:el|la|los|las)?\s+([^\.]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, details)
            if match:
                location = match.group(1).strip()
                # Clean up trailing punctuation
                location = re.sub(r'[,\.:;]$', '', location)
                return location

        return ""

    def _extract_url(self, details):
        """Extract URL from details if it contains a link reference."""
        # Look for common URL patterns in the text
        url_patterns = [
            r'https?://[^\s\'"]+',
        ]

        for pattern in url_patterns:
            match = re.search(pattern, details)
            if match:
                return match.group(0)

        return self.url