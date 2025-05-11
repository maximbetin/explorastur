"""
Base class for event scrapers.
"""

import logging
import requests
import time
from bs4 import BeautifulSoup
import re
import datetime
from typing import Dict, List, Optional, Any, Union, Callable

from utils import DateProcessor, TextProcessor
from scraper_utils import fetch_page, parse_html, make_absolute_url

logger = logging.getLogger('explorastur')

class EventScraper:
    """Base class for event scrapers.

    Provides common functionality for all event scrapers and defines
    the interface that subclasses must implement.
    """

    def __init__(self, config=None):
        """Initialize the event scraper with common utilities.

        Args:
            config: Configuration dictionary for the scraper
        """
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()
        self.source_name = "Generic"

        # Apply configuration if provided
        self.config = config or {}
        if config:
            self.source_name = config.get("name", self.source_name)
            self.url = config.get("url", "")
            self.timeout = config.get("timeout", 30)
            self.max_retries = config.get("max_retries", 3)
            self.retry_delay = config.get("retry_delay", 2)
            self.headers = config.get("headers", {})
            self.max_pages = config.get("max_pages", 3)
        else:
            self.url = ""
            self.timeout = 30
            self.max_retries = 3
            self.retry_delay = 2
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            self.max_pages = 3

    def scrape(self) -> List[Dict[str, str]]:
        """Scrape events from the source.

        This method should be implemented by subclasses to scrape events
        from a specific source.

        Returns:
            List of event dictionaries
        """
        raise NotImplementedError("Subclasses must implement scrape method")

    def fetch_page_with_retry(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic.

        Args:
            url: URL to fetch

        Returns:
            HTML content string or None if all retries failed
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Fetching URL (attempt {attempt}/{self.max_retries}): {url}")
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.text

                logger.warning(f"Failed to fetch URL: {url}, status code: {response.status_code}")

                # If not a 5XX error, don't retry
                if response.status_code < 500 or response.status_code >= 600:
                    break

            except Exception as e:
                logger.warning(f"Error fetching URL (attempt {attempt}/{self.max_retries}): {url}, error: {e}")

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return None

    def fetch_and_parse(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL and parse its HTML content.

        Args:
            url: The URL to fetch

        Returns:
            BeautifulSoup object or None if request or parsing failed
        """
        html = self.fetch_page_with_retry(url)
        if html:
            return parse_html(html)
        return None

    def create_event(self, title: str, date: str, location: str, url: str,
                    description: str = "", source: Optional[str] = None) -> Dict[str, str]:
        """Create a standardized event dictionary.

        Args:
            title: Event title
            date: Event date
            location: Event location
            url: Event URL
            description: Event description (optional)
            source: Source name (optional)

        Returns:
            Event dictionary with standardized format
        """
        # Use source name from the class if not provided
        if not source:
            source = self.source_name

        # Ensure title isn't empty
        if not title or title == ":":
            title = ""  # Let the processor handle empty titles

        # Standardize the date format for all events
        date = self._standardize_date_format(date)

        return {
            'title': title,
            'date': date,
            'location': location,
            'description': description,
            'url': url,
            'source': source
        }

    def _standardize_date_format(self, date_str: str) -> str:
        """Standardize date format across all scrapers.

        Args:
            date_str: Date string to standardize

        Returns:
            Standardized date string
        """
        if not date_str:
            return date_str

        # Remove day of week prefix if present (e.g., "lunes 12 de mayo" → "12 de mayo")
        date_str = re.sub(r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+', '', date_str.strip())

        # Remove leading zeros in day numbers (e.g., "01 mayo" → "1 mayo")
        date_str = re.sub(r'\b0(\d)(\s+de|\s*[-\/])', r'\1\2', date_str)

        # Remove year suffixes for current year (e.g., "12 mayo 2025" → "12 mayo")
        current_year = datetime.datetime.now().year
        date_str = re.sub(f'\\s+{current_year}\\b', '', date_str)

        return date_str.strip()

    def process_pagination(self, base_url: str, start_url: str,
                          max_pages: Optional[int] = None,
                          extract_page_events: Optional[Callable[[BeautifulSoup], List[Dict[str, str]]]] = None,
                          next_page_selector: Optional[str] = None) -> List[Dict[str, str]]:
        """Process pagination for a website.

        Args:
            base_url: Base URL of the website
            start_url: Starting URL for pagination
            max_pages: Maximum number of pages to process (defaults to self.max_pages)
            extract_page_events: Function to extract events from a page
            next_page_selector: CSS selector for next page link

        Returns:
            List of event dictionaries from all pages
        """
        if not extract_page_events:
            raise ValueError("extract_page_events function must be provided")

        # Use instance max_pages if not provided
        if max_pages is None:
            max_pages = self.max_pages

        all_events = []
        current_page = 1
        current_url = start_url

        while current_page <= max_pages:
            logger.info(f"Fetching page {current_page}: {current_url}")

            try:
                soup = self.fetch_and_parse(current_url)
                if not soup:
                    break

                # Extract events from the current page
                page_events = extract_page_events(soup)
                all_events.extend(page_events)

                logger.info(f"Extracted {len(page_events)} events from page {current_page}")

                # If no next page selector provided, stop after first page
                if not next_page_selector:
                    break

                # Find the next page link
                next_link = soup.select_one(next_page_selector)
                if not next_link:
                    logger.info("No next page link found")
                    break

                # Check if next link is disabled
                classes = next_link.get('class', [])
                if classes and 'disabled' in classes:
                    logger.info("Next page link is disabled")
                    break

                # Get the URL for the next page
                next_url = next_link.get('href', '')
                if not next_url:
                    logger.info("No next page URL found")
                    break

                # Make the URL absolute if it's relative
                if isinstance(next_url, list):
                    next_url = next_url[0] if next_url else ""
                current_url = make_absolute_url(base_url, next_url)
                current_page += 1

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                break

        return all_events