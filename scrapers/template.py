"""
Template for creating new scrapers.

This is a minimal skeleton template that should be copied to a new file
when creating a new scraper. It contains only the essential structure
that needs to be implemented for each scraper.

Usage:
1. Copy this file to a new file with an appropriate name (e.g., new_source.py)
2. Rename the class to match your scraper (e.g., NewSourceScraper)
3. Implement the required methods

Do not modify this template directly - it's meant to be copied.
"""

import logging
from typing import Dict, List, Optional, Any, cast
from bs4 import BeautifulSoup, Tag

from scrapers.base import EventScraper
from scraper_utils import make_absolute_url

logger = logging.getLogger('explorastur')

class TemplateScraper(EventScraper):
    """Template scraper class.

    This is a skeleton template for creating new scraper classes.
    Rename this class to match your scraper (e.g., NewSourceScraper).
    """

    def __init__(self, config=None):
        """Initialize the scraper.

        The base class handles all the configuration.
        You can add scraper-specific initialization here if needed.

        Args:
            config: Configuration dictionary for the scraper
        """
        super().__init__(config)
        # Add any scraper-specific initialization here

    def scrape(self) -> List[Dict[str, str]]:
        """Scrape events from the source.

        This is the main method that should be implemented.
        It should handle the following steps:
        1. Fetch and parse the HTML from the source
        2. Find event containers/elements
        3. Extract data from each event
        4. Create standardized event dictionaries
        5. Return the list of events

        Returns:
            List of standardized event dictionaries
        """
        logger.info(f"Fetching URL: {self.url}")

        try:
            # For simple scraping without pagination
            soup = self.fetch_and_parse(self.url)
            if not soup:
                logger.error(f"Failed to fetch or parse URL: {self.url}")
                return []

            return self._extract_events_from_page(soup)

            # For pagination support, use the following pattern instead:
            # return self.process_pagination(
            #     base_url=self.base_url,
            #     start_url=self.url,
            #     extract_page_events=self._extract_events_from_page,
            #     next_page_selector='.pagination .next-page'
            # )
        except Exception as e:
            return self.handle_error(e, "scraping events", [])

    def _extract_events_from_page(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract events from a single page.

        This helper method should process a single page of events,
        finding all event containers and extracting data from each.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of event dictionaries
        """
        events = []

        # Find all event containers
        # TODO: Replace with appropriate selector for your target site
        event_containers = soup.select('.event-container')
        logger.info(f"Found {len(event_containers)} event containers")

        # Process each event container
        for container in event_containers:
            try:
                event = self._extract_event_from_container(container)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error extracting event: {e}")
                # Continue with the next event instead of failing completely

        logger.info(f"Found {len(events)} events")
        return events

    def _extract_event_from_container(self, container: Tag) -> Optional[Dict[str, str]]:
        """Extract event details from a container element.

        Args:
            container: BeautifulSoup element containing event data

        Returns:
            Event dictionary or None if extraction failed
        """
        try:
            # TODO: Implement extraction logic for your specific website
            # Extract title, date, location, URL, etc.
            title_element = container.select_one('.event-title')
            if not title_element:
                return None

            title = title_element.get_text().strip()

            # Clean the title
            title = self.text_processor.clean_title(title)

            # Extract event URL
            link_element = container.select_one('a.event-link')
            event_url = ""
            if link_element:
                href = link_element.get('href')
                if href:
                    # Convert href to string if it's a list
                    event_url = href[0] if isinstance(href, list) else href
                    event_url = str(event_url)

            # Make URL absolute if it's relative
            if event_url and not event_url.startswith(('http://', 'https://')):
                event_url = make_absolute_url(self.base_url, event_url)

            # Extract date
            date_element = container.select_one('.event-date')
            date = date_element.get_text().strip() if date_element else ''

            # Clean and standardize the date format
            date = self.clean_date_text(date)

            # Extract location
            location_element = container.select_one('.event-location')
            location = location_element.get_text().strip() if location_element else ''

            # If no specific location element, try to extract from container text
            if not location:
                container_text = container.get_text()
                location = self.extract_location_from_text(
                    container_text,
                    default_location=self.source_name
                )

            # Extract description (optional)
            desc_element = container.select_one('.event-description')
            description = desc_element.get_text().strip() if desc_element else ''

            # Create a standardized event dictionary
            return self.create_event(
                title=title,
                date=date,
                location=location,
                url=event_url,
                description=description
            )

        except Exception as e:
            logger.error(f"Error extracting event details: {e}")
            return None

    # Add any additional helper methods needed for your specific scraper
    # def _extract_date(self, element):
    #     """Example helper method to extract date information."""
    #     pass

    # def _extract_location(self, element):
    #     """Example helper method to extract location information."""
    #     pass