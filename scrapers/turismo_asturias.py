"""
Scraper for Turismo Asturias events.
"""

import logging
import re
import datetime
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Any, Union

from scrapers.base import EventScraper
from scraper_utils import make_absolute_url

logger = logging.getLogger('explorastur')

class TurismoAsturiasScraper(EventScraper):
    """Scraper for Turismo Asturias website."""

    def __init__(self, config=None):
        super().__init__(config)

    def scrape(self):
        """Scrape events from Turismo Asturias website with pagination support."""
        logger.info(f"Fetching URL: {self.url}")

        try:
            # Use the base class pagination method with a custom next page selector
            return self.process_pagination(
                base_url=self.base_url,
                start_url=self.url,
                extract_page_events=self._extract_events_from_page,
                next_page_selector='ul.lfr-pagination-buttons li:not(.disabled) a:-soup-contains("Siguiente")'
            )
        except Exception as e:
            return self.handle_error(e, "scraping Turismo Asturias events", [])

    def _extract_events_from_page(self, soup):
        """Extract events from a page of results."""
        events = []

        # Find all event cards in the template-cards section
        event_cards = soup.select('div.template-cards .col-xl-4 .card')

        if not event_cards:
            logger.warning("No event cards found on page")
            return events

        for card in event_cards:
            event = self._extract_event_from_card(card)
            if event:
                events.append(event)

        return events

    def _extract_event_from_card(self, card):
        """Extract event details from a card element."""
        try:
            # Extract event link and title
            link_element = card.select_one('a[href]')
            if not link_element:
                return None

            relative_url = link_element.get('href', '')
            event_url = make_absolute_url(self.base_url, relative_url)

            # Extract title from card-title element
            title_element = card.select_one('.card-title')
            title = title_element.get_text().strip() if title_element else ""

            # Skip if no title found
            if not title:
                return None

            # Extract location from address element
            location_element = card.select_one('.address')
            location = ""
            if location_element:
                # Find the location text after the map marker icon
                location_text = ""
                for item in location_element.contents:
                    if isinstance(item, Tag):
                        item_class = item.get("class", [])
                        if isinstance(item_class, list) and "fa-map-marker-alt" in item_class:
                            continue
                    if isinstance(item, str) and item.strip():
                        location_text += item.strip()

                if not location_text:
                    # Try to find the address in a span
                    location_span = location_element.select_one('span[itemprop="address"]')
                    if location_span:
                        location_text = location_span.get_text().strip()

                location = location_text.strip()

            # Extract date information
            date_element = card.select_one('.date')
            start_date = ""
            end_date = ""

            if date_element:
                # Look for the hidden date elements that contain the full dates
                start_date_elem = date_element.select_one('span[itemprop="startDate"]')
                end_date_elem = date_element.select_one('span[itemprop="endDate"]')

                # Get visible date text which is formatted
                date_spans = date_element.select('span:not(.hide):not(.far):not(.hide-accessible)')
                date_visible_texts = [span.get_text().strip() for span in date_spans if span.get_text().strip()]

                if start_date_elem and start_date_elem.has_attr('date'):
                    start_date = start_date_elem['date'].split()[0]  # Get date part only

                if end_date_elem and end_date_elem.has_attr('date'):
                    end_date = end_date_elem['date'].split()[0]  # Get date part only

            # Extract hour information
            hour_element = card.select_one('.hour')
            time_info = ""

            if hour_element:
                hour_text = hour_element.get_text().strip()
                # Remove the clock icon text
                hour_text = re.sub(r'^\s*\S+\s*', '', hour_text).strip()
                if hour_text and hour_text != "Todo el dia":
                    time_info = hour_text

            # Format the date string
            event_date = self._format_date(start_date, end_date, time_info)

            # Create and return the event
            return self.create_event(
                title=title,
                date=event_date,
                location=location,
                url=event_url
            )

        except Exception as e:
            logger.error(f"Error extracting event from card: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _format_date(self, start_date, end_date, time_info):
        """Format the date string based on start date, end date, and time information."""
        if not start_date:
            return ""

        try:
            # Parse dates from ISO format (YYYY-MM-DD)
            start_parts = start_date.split('-')
            start_year = start_parts[0]
            start_month_num = int(start_parts[1])
            start_day = start_parts[2].lstrip('0')  # Remove leading zeros

            start_month = self._get_spanish_month(start_month_num)

            formatted_date = f"{start_day} {start_month} {start_year}"

            # Add end date if different from start date
            if end_date and end_date != start_date:
                end_parts = end_date.split('-')
                end_year = end_parts[0]
                end_month_num = int(end_parts[1])
                end_day = end_parts[2].lstrip('0')  # Remove leading zeros

                end_month = self._get_spanish_month(end_month_num)

                # Format based on whether month/year are different
                if end_year != start_year:
                    formatted_date += f" - {end_day} {end_month} {end_year}"
                elif end_month_num != start_month_num:
                    formatted_date += f" - {end_day} {end_month} {end_year}"
                else:
                    formatted_date += f" - {end_day} {start_month} {start_year}"

            # Add time information if available
            if time_info:
                formatted_date += f", {time_info}"

            return formatted_date

        except Exception as e:
            logger.error(f"Error formatting date '{start_date}' to '{end_date}': {e}")
            # Return the start date as fallback
            return start_date

    def _get_spanish_month(self, month_num):
        """Convert month number to Spanish month name."""
        months = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        return months.get(month_num, "")