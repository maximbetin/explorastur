"""
Scraper for Biodevas events.
"""

import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from datetime import datetime

from scrapers.base import EventScraper
from scraper_utils import make_absolute_url

logger = logging.getLogger('explorastur')

class BiodevasScraper(EventScraper):
    """Scraper for Biodevas events."""

    def __init__(self, config=None):
        super().__init__(config)

    def scrape(self):
        """Scrape events from Biodevas website."""
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            soup = self.fetch_and_parse(self.url)
            if not soup:
                return []

            events = self._extract_events_from_page(soup)
            logger.info(f"Found {len(events)} events on Biodevas page")

            # Check if there are more pages
            pagination = soup.select_one('.navigation.pagination .next.page-numbers')
            if pagination and len(events) > 0:
                # Only fetch one more page to avoid too many requests
                next_page_url = pagination.get('href')
                if next_page_url:
                    logger.info(f"Fetching next page: {next_page_url}")
                    # Ensure next_page_url is a string
                    next_page_url = str(next_page_url)
                    next_soup = self.fetch_and_parse(next_page_url)
                    if next_soup:
                        next_events = self._extract_events_from_page(next_soup)
                        events.extend(next_events)
                        logger.info(f"Added {len(next_events)} more events from next page")

            return events

        except Exception as e:
            logger.error(f"Error scraping Biodevas: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _extract_events_from_page(self, soup):
        """Extract events from the page content."""
        events = []

        # Find all event articles - now using the new selector
        # The content-masonry div contains all articles
        content_masonry = soup.select_one('#content-masonry')
        if not content_masonry:
            logger.warning("No content-masonry div found on Biodevas page")
            return []

        articles = content_masonry.select('article.hentry')
        if not articles:
            logger.warning("No event articles found on Biodevas page")
            return []

        # Process each article
        for article in articles:
            event = self._extract_event_from_article(article)
            if event:
                events.append(event)

        return events

    def _extract_event_from_article(self, article):
        """Extract event details from an article element."""
        try:
            # Extract event link and title
            title_element = article.select_one('.entry-title a')
            if not title_element:
                return None

            title = title_element.get_text().strip()
            event_url = title_element.get('href', '')
            if not event_url.startswith('http'):
                event_url = make_absolute_url(self.base_url, event_url)

            # Skip if no title found
            if not title:
                return None

            # Clean up the title - remove any "Destacado" text that might be included
            title = re.sub(r'^\s*Destacado\s*[-:]\s*', '', title)
            title = self.text_processor.clean_title(title)

            # Extract date from URL or article content
            # URLs often have format like /2025/05/event-name/
            url_date = None
            if event_url:
                url_date_match = re.search(r'/(\d{4})/(\d{2})/', event_url)
                if url_date_match:
                    year = url_date_match.group(1)
                    month_num = int(url_date_match.group(2))
                    month_name = self._get_spanish_month(month_num)
                    url_date = f"{month_name} {year}"

            # Extract summary text for additional info
            summary_element = article.select_one('.entry-summary')
            summary_text = ""
            if summary_element:
                summary_text = summary_element.get_text().strip()

            # Filter out non-event articles by checking the content
            if ('asóciate' in summary_text.lower() and
                not re.search(r'(?:fecha|día|mes)(?:\s|:)', summary_text, re.IGNORECASE)):
                # This is more likely an information article, not an event
                if not re.search(r'(?:actividad|taller|paseo|ruta|visita)', title.lower()):
                    return None

            # Extract location from title, summary, or tags
            location = self._extract_location(article, title, summary_text)

            # Process date information
            event_date = self._extract_date(article, title, summary_text, url_date)

            # Create the event
            return self.create_event(
                title=title,
                date=event_date,
                location=location,
                url=event_url
            )

        except Exception as e:
            logger.error(f"Error extracting event from article: {e}")
            return None

    def _extract_location(self, article, title, summary_text):
        """Extract location from article elements."""
        # Try to extract location from title first
        title_location = self.text_processor.extract_location_from_title(title)
        if title_location:
            return title_location

        # Check for categories that might indicate location
        categories = article.select_one('.category-metas')
        if categories:
            categories_text = categories.get_text().strip()
            if 'Centro Social los Lugg' in categories_text:
                return 'Centro Social los Lugg, Lugones'

        # Try to find location in the summary text
        location_patterns = [
            # "Lugar: Centro Social los Lugg"
            (r'lugar:?\s*([^.,\n]+)', 1),
            # Venue keywords
            (r'(?:en|En)\s+(?:el|la|los|las)?\s+((?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría|Museo|Recinto|Bosque)\s+[^.,\n]+)', 1),
            # Location after "en" preposition with capital letter
            (r'(?:en|En)\s+([A-Z][a-zA-Záéíóúñ]+(?:\s+[a-zA-Záéíóúñ]+)*)', 1),
            # Common locations
            (r'(?:Centro Social los Lugg|Fundación Un bosque pa María|El Sueve|Rodiles)', 0),
            # Activity in location
            (r'actividad\s+(?:en|En)\s+([^.,\n]+)', 1),
        ]

        for pattern, group in location_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                location = match.group(group).strip()
                # Remove unwanted parts like question marks
                location = re.sub(r'\?.*$', '', location).strip()
                return location

        # Check for location in tags
        tags_element = article.select_one('.tags')
        if tags_element:
            tags_text = tags_element.get_text().strip()
            # Look for location names in tags
            location_tags = [
                'Lugones', 'Siero', 'Oviedo', 'Gijón', 'Avilés', 'Villaviciosa',
                'Rodiles', 'El Sueve', 'El Fitu'
            ]

            for location in location_tags:
                if location.lower() in tags_text.lower():
                    return location

        # Default to Asturias if no specific location found
        return "Asturias"

    def _extract_date(self, article, title, summary_text, url_date):
        """Extract date information from article elements."""
        # First check for explicit date patterns in the summary
        date_patterns = [
            # "Fecha: 15 de mayo"
            r'fecha:?\s*(\d{1,2}\s+de\s+[a-zA-Záéíóúñ]+)',
            # "15 de mayo"
            r'(\d{1,2}\s+de\s+[a-zA-Záéíóúñ]+)',
            # "Del 15 al 20 de mayo"
            r'[Dd]el\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Záéíóúñ]+)',
            # "15-20 de mayo"
            r'(\d{1,2})\s*[-\/]\s*(\d{1,2})\s+de\s+([a-zA-Záéíóúñ]+)',
        ]

        # Look for dates with full pattern matching
        for pattern in date_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                # Return the entire matched date phrase
                return match.group(0)

        # Look for date components and build a date string
        day_match = re.search(r'día\s+(\d{1,2})', summary_text, re.IGNORECASE)
        month_match = re.search(r'mes\s+de\s+([a-zA-Záéíóúñ]+)', summary_text, re.IGNORECASE)

        if day_match and month_match:
            day = day_match.group(1)
            month = month_match.group(1)
            return f"{day} de {month}"

        # Check for date in title
        for pattern in date_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(0)

        # If we found a date in the URL, use it
        if url_date:
            return f"Todo el mes de {url_date}"

        # If no date found, use current month
        return f"Todo el mes de {self.date_processor.get_current_month_name()}"

    def _get_spanish_month(self, month_num):
        """Convert month number to Spanish month name."""
        months = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        return months.get(month_num, "")