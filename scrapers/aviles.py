"""
Scraper for Avilés events.
"""

import logging
import re
import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

from utils import UrlUtils
from .base import EventScraper

logger = logging.getLogger('explorastur')

class AvilesEventsScraper(EventScraper):
    """Scraper for Avilés events."""

    def __init__(self, config=None):
        """Initialize the scraper.

        Args:
            config: Configuration dictionary for the scraper
        """
        super().__init__(config)

    def scrape(self) -> List[Dict[str, str]]:
        """Scrape events from Avilés website.

        Returns:
            List of standardized event dictionaries
        """
        logger.info(f"Fetching URL: {self.url}")

        try:
            # Fetch only the first page for now to avoid pagination-related errors
            # This is a temporary fix until the website's pagination system is more stable
            events = []

            # Fetch the first page
            soup = self.fetch_and_parse(self.url)
            if soup:
                logger.info(f"Fetching page 1: {self.url}")
                page_events = self._extract_events_from_page(soup)
                if page_events:
                    events.extend(page_events)
                    logger.info(f"Found {len(page_events)} events on page 1")
            else:
                logger.error(f"Failed to fetch or parse the first page: {self.url}")
                logger.warning("The Avilés events server may be experiencing issues. This is a known intermittent problem.")
                return []

            # Skip pagination for now due to server errors
            logger.info(f"Finished pagination, found {len(events)} events in total")
            return events

        except Exception as e:
            logger.error(f"Error scraping Avilés events: {e}")
            logger.warning("The Avilés website often experiences server errors (502). This is a known issue with their server.")
            return []

    def _extract_events_from_page(self, soup) -> List[Dict[str, str]]:
        """Extract events from the page content.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of event dictionaries
        """
        events = []

        # Find all event cards - new structure uses .card.border-info
        event_cards = soup.select('.card.border-info')
        if not event_cards:
            logger.warning("No event cards found on Avilés page")
            return []

        # Process each card
        for card in event_cards:
            try:
                event = self._extract_event_from_card(card)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error extracting event from card: {e}")
                # Continue with the next event instead of failing completely

        logger.info(f"Found {len(events)} events from Avilés")
        return events

    def _extract_event_from_card(self, card) -> Optional[Dict[str, str]]:
        """Extract event details from a card element.

        Args:
            card: BeautifulSoup element containing event data

        Returns:
            Event dictionary or None if extraction failed
        """
        try:
            # Extract event title
            title_element = card.select_one('h5')
            if not title_element:
                return None

            title = title_element.get_text().strip()

            # Extract event URL from the "Ver" button
            link_element = card.select_one('.btn.btn-primary')
            event_url = self.url  # Default to the main page
            if link_element and 'onclick' in link_element.attrs:
                onclick = link_element['onclick']
                event_id_match = re.search(r"showPopup\('/-/calendar/calendar/event/(\d+)", onclick)
                if event_id_match:
                    event_id = event_id_match.group(1)
                    event_url = f"{self.base_url}/-/calendar/calendar/event/{event_id}"

            # Skip if no title found
            if not title:
                return None

            # Clean up the title
            title = self.text_processor.clean_title(title)

            # Extract date information from badges
            date_info = self._extract_date_info(card)

            # Extract location from card text
            location = self._extract_location(card, title)

            # Create the event
            return self.create_event(
                title=title,
                date=date_info,
                location=location,
                url=event_url
            )

        except Exception as e:
            logger.error(f"Error extracting event from card: {e}")
            return None

    def _extract_date_info(self, card) -> str:
        """Extract and format date information from the card.

        Args:
            card: BeautifulSoup element containing date information

        Returns:
            Formatted date string
        """
        try:
            # Check for date badges in the card
            date_badges = card.select('.badge.badge-secondary')

            start_date = ""
            end_date = ""
            recurrent_end = ""

            for badge in date_badges:
                badge_text = badge.get_text().strip()

                # Check for start date
                if badge_text.startswith("INICIO:"):
                    start_date = badge_text.replace("INICIO:", "").strip()

                # Check for end date
                elif badge_text.startswith("FIN:"):
                    end_date = badge_text.replace("FIN:", "").strip()

                # Check for recurrent event end date
                elif "Finaliza:" in badge_text:
                    recurrent_end = re.search(r"Finaliza:\s*(\d{2}-\d{2}-\d{4})", badge_text)
                    if recurrent_end:
                        recurrent_end = recurrent_end.group(1)

            # Format the date information
            if start_date:
                # Extract day, month, year from the format "DD-MM-YYYY HH:MM"
                date_match = re.search(r"(\d{2})-(\d{2})-(\d{4})", start_date)
                if date_match:
                    day = date_match.group(1).lstrip('0')
                    month_num = int(date_match.group(2))
                    month_name = self._get_spanish_month(month_num)

                    # Check if it's a recurring event
                    if recurrent_end:
                        end_match = re.search(r"(\d{2})-(\d{2})-(\d{4})", recurrent_end)
                        if end_match:
                            end_day = end_match.group(1).lstrip('0')
                            end_month_num = int(end_match.group(2))
                            end_month_name = self._get_spanish_month(end_month_num)

                            # If same month
                            if month_num == end_month_num:
                                return f"{day} - {end_day} de {month_name}"
                            else:
                                return f"{day} de {month_name} - {end_day} de {end_month_name}"

                    # Extract time if available
                    time_match = re.search(r"(\d{2}:\d{2})", start_date)
                    if time_match:
                        time = time_match.group(1)
                        return f"{day} de {month_name} a las {time}"

                    return f"{day} de {month_name}"

            # If no structured date found, try to extract from description
            card_text_div = card.select_one('.card-text')
            if card_text_div:
                card_text = card_text_div.get_text().strip()

                # Look for date patterns
                date_patterns = [
                    # "Fecha: Del 14 de marzo al 15 de junio 2025"
                    re.search(r'fecha:?\s*del\s+(\d{1,2})\s+de\s+([a-zA-Z]+)\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
                             card_text, re.IGNORECASE),
                    # "Del 5 al 10 de mayo"
                    re.search(r'del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
                             card_text, re.IGNORECASE),
                    # "5-10 de mayo"
                    re.search(r'(\d{1,2})\s*[-\/]\s*(\d{1,2})\s+de\s+([a-zA-Z]+)',
                             card_text, re.IGNORECASE),
                    # "5 de mayo"
                    re.search(r'(\d{1,2})\s+de\s+([a-zA-Z]+)',
                             card_text, re.IGNORECASE)
                ]

                for pattern in date_patterns:
                    if pattern:
                        return pattern.group(0)

            # If no date found, use current month
            return f"Todo el mes de {self.date_processor.get_current_month_name()}"

        except Exception as e:
            logger.error(f"Error extracting date info: {e}")
            return f"Todo el mes de {self.date_processor.get_current_month_name()}"

    def _extract_location(self, card, title) -> str:
        """Extract location information from the card or title.

        Args:
            card: BeautifulSoup element containing location information
            title: Event title string

        Returns:
            Location string
        """
        try:
            # Try to find location in the card text
            card_text_div = card.select_one('.card-text')
            if not card_text_div:
                # If no card text, try to extract from title or return default
                title_location = self.text_processor.extract_location_from_title(title)
                return title_location if title_location else "Avilés"

            card_text = card_text_div.get_text().strip()

            # Look for location patterns
            location_patterns = [
                # "Lugar: Teatro Palacio Valdés"
                re.search(r'lugar:?\s+([^\.]+)', card_text, re.IGNORECASE),
                # "en el Teatro Palacio Valdés"
                re.search(r'en\s+(?:el|la|los|las)\s+([^\.]+)', card_text, re.IGNORECASE),
                # "Teatro Palacio Valdés"
                re.search(r'(?:centro\s+de\s+arte|centro|teatro|museo|casa\s+de\s+cultura|auditorio|palacio|plaza)\s+([^\.]+)',
                         card_text, re.IGNORECASE)
            ]

            for pattern in location_patterns:
                if pattern:
                    location = pattern.group(1).strip()
                    if location.lower().endswith(", avilés"):
                        return location
                    else:
                        return f"{location}, Avilés"

            # Try to extract from title as fallback
            title_location = self.text_processor.extract_location_from_title(title)
            if title_location:
                if title_location.lower().endswith(", avilés"):
                    return title_location
                else:
                    return f"{title_location}, Avilés"

            return "Avilés"

        except Exception as e:
            logger.error(f"Error extracting location: {e}")
            return "Avilés"

    def _get_spanish_month(self, month_num) -> str:
        """Get the Spanish name for a month number.

        Args:
            month_num: Month number (1-12)

        Returns:
            Spanish month name
        """
        month_mapping = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre"
        }
        return month_mapping.get(month_num, "")