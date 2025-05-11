"""
Template for creating new scrapers.

Use this file as a starting point when creating a new scraper.
Copy this file to a new file with an appropriate name (e.g., new_source.py)
and implement the scraper class following this template.
"""

import logging
import re
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Any, Union

from scrapers.base import EventScraper

logger = logging.getLogger('explorastur')

class TemplateScraper(EventScraper):
    """Template scraper class.

    This is a template for creating new scraper classes.
    Rename this class to match your scraper (e.g., NewSourceScraper).
    """

    def __init__(self, config=None):
        """Initialize the scraper.

        Args:
            config: Configuration dictionary for the scraper
        """
        super().__init__(config)

        # If no config is provided, set default values
        if not config:
            self.url = "https://example.com/events"
            self.source_name = "Template Source"

        # Add any other initialization needed for this specific scraper

    def scrape(self) -> List[Dict[str, str]]:
        """Scrape events from the source.

        Returns:
            List of event dictionaries
        """
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            # Fetch and parse the HTML
            soup = self.fetch_and_parse(self.url)
            if not soup:
                logger.error(f"Failed to fetch or parse URL: {self.url}")
                return []

            # Find event containers
            # Replace this selector with the appropriate one for your target site
            event_containers = soup.select('.event-container')
            logger.info(f"Found {len(event_containers)} event containers")

            # Process each event container
            for container in event_containers:
                # Extract event data from the container
                # Replace these selectors with appropriate ones for your target site
                title_element = container.select_one('.event-title')
                date_element = container.select_one('.event-date')
                location_element = container.select_one('.event-location')
                link_element = container.select_one('a')

                # Skip if required elements are missing
                if not title_element or not date_element:
                    continue

                # Extract text content
                title = title_element.get_text().strip()
                date = date_element.get_text().strip()
                location = location_element.get_text().strip() if location_element else ""

                # Extract URL
                url = ""
                if link_element and hasattr(link_element, 'get') and callable(link_element.get):
                    href = link_element.get('href', '')
                    # Handle the case where href is a list (some BS4 versions)
                    if isinstance(href, list):
                        href = href[0] if href else ""

                    # Make URL absolute if it's relative
                    if href and isinstance(href, str) and href.startswith(('http://', 'https://')):
                        url = href
                    elif href and isinstance(href, str):
                        url = self._make_absolute_url(self.url, href)

                # If no URL was found, use the main page URL
                if not url:
                    url = self.url

                # Create event dictionary with safe string values
                event = self.create_event(
                    title=title,
                    date=date,
                    location=location,
                    url=str(url),  # Ensure it's a string
                    description="",  # Optional description
                    source=self.source_name
                )

                events.append(event)

            logger.info(f"Found {len(events)} events")
            return events

        except Exception as e:
            logger.error(f"Error scraping {self.source_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """Make a relative URL absolute.

        Args:
            base_url: The base URL of the website
            relative_url: A relative URL

        Returns:
            Absolute URL
        """
        # Remove fragment identifier
        if '#' in base_url:
            base_url = base_url.split('#')[0]

        # If it already starts with http, it's already absolute
        if relative_url.startswith(('http://', 'https://')):
            return relative_url

        # If it starts with a slash, append to the domain
        if relative_url.startswith('/'):
            # Extract domain from base_url
            from urllib.parse import urlparse
            parsed_base = urlparse(base_url)
            domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            return domain + relative_url

        # Otherwise, it's relative to the current path
        # Remove the filename from the base_url if present
        if base_url.endswith('/'):
            return base_url + relative_url
        else:
            # Remove last path component
            base_url = base_url.rsplit('/', 1)[0] + '/'
            return base_url + relative_url