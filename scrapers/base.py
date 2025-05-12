"""
Base class for event scrapers.
"""

import logging
import requests
import time
import traceback
from bs4 import BeautifulSoup
import re
import datetime
from typing import Dict, List, Optional, Any, Union, Callable, cast, TypeVar
from abc import ABC, abstractmethod

from utils import DateProcessor, TextProcessor, HtmlUtils, UrlUtils
from scrapers.config import get_default_config

logger = logging.getLogger('explorastur')

# Generic type for function return values
T = TypeVar('T')

class BaseScraper(ABC):
    """
    Base abstract class for all scrapers.
    Each scraper should inherit from this class and implement the scrape method.
    """

    def __init__(self, base_url: str, source_name: str):
        """
        Initialize the scraper with base URL and source name.

        Args:
            base_url: Base URL of the website to scrape
            source_name: Name of the source (for attribution)
        """
        self.base_url = base_url
        self.source_name = source_name

    def fetch_page(self, url: Optional[str] = None) -> Optional[str]:
        """
        Fetch a page from the website.

        Args:
            url: URL to fetch (defaults to base_url if not provided)

        Returns:
            HTML content as string or None if fetch failed
        """
        target_url = url or self.base_url
        logger.info(f"Fetching page: {target_url}")

        try:
            response = requests.get(target_url)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to fetch page: {target_url}, status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching page {target_url}: {e}")
            return None

    def fetch_and_parse(self, url: Optional[str] = None):
        """
        Fetch a page and parse it with BeautifulSoup.

        Args:
            url: URL to fetch (defaults to base_url if not provided)

        Returns:
            BeautifulSoup object or None if fetch or parse failed
        """
        html = self.fetch_page(url)
        if html:
            return HtmlUtils.parse_html(html)
        return None

    def make_absolute_url(self, relative_url: str) -> str:
        """
        Convert a relative URL to an absolute URL.

        Args:
            relative_url: Relative URL to convert

        Returns:
            Absolute URL
        """
        return UrlUtils.make_absolute_url(self.base_url, relative_url)

    def add_source_info(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add source information to events.

        Args:
            events: List of event dictionaries

        Returns:
            Events with source information added
        """
        for event in events:
            event['source'] = self.source_name
        return events

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape events from the website.

        Returns:
            List of event dictionaries
        """
        pass

class EventScraper(BaseScraper):
    """Base class for event scrapers.

    Provides common functionality for all event scrapers and defines
    the interface that subclasses must implement.
    """

    def __init__(self, config=None):
        """Initialize the event scraper with common utilities.

        Args:
            config: Configuration dictionary for the scraper
        """
        # Apply configuration - use defaults if none provided
        default_config = get_default_config()
        self.config = config or default_config

        # Extract common configuration parameters
        self.source_name = str(self.config.get("name", default_config["name"]))
        self.url = str(self.config.get("url", default_config["url"]))

        # Set base_url - default to derived from URL if not provided
        base_url_default = ""
        if self.url and "//" in self.url:
            url_parts = self.url.split("/")
            if len(url_parts) >= 3:
                base_url_default = url_parts[0] + "//" + url_parts[2]

        self.base_url = str(self.config.get("base_url", base_url_default))
        self.timeout = int(self.config.get("timeout", default_config["timeout"]))
        self.max_retries = int(self.config.get("max_retries", default_config["max_retries"]))
        self.retry_delay = int(self.config.get("retry_delay", default_config["retry_delay"]))
        self.headers = self.config.get("headers", default_config["headers"])
        self.max_pages = int(self.config.get("max_pages", default_config["max_pages"]))

        # Initialize with base class
        super().__init__(self.url, self.source_name)

        # Initialize utility classes
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()

    def handle_error(self, error: Exception, context: str, return_value: T) -> T:
        """Standard error handling for scrapers.

        This method provides consistent error handling across all scrapers.
        It logs the error with appropriate context and optionally includes a traceback.

        Args:
            error: The exception that was raised
            context: Description of what was happening when the error occurred
            return_value: The value to return after handling the error

        Returns:
            The provided return_value (typically an empty list for scraper methods)
        """
        # Log the basic error with context
        logger.error(f"Error {context} for {self.source_name}: {error}")

        # Include the full traceback for detailed debugging
        logger.debug(f"Traceback for {context} error in {self.source_name}:\n{traceback.format_exc()}")

        # Return the provided default value
        return return_value

    def safe_execute(self, func: Callable[..., T], context: str, default_return: T, *args, **kwargs) -> T:
        """Execute a function with standardized error handling.

        This is a wrapper that executes a function and handles any exceptions
        using the standardized error handling approach.

        Args:
            func: The function to execute
            context: Description of what the function is doing
            default_return: Value to return if an exception occurs
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The function's return value or default_return if an exception occurs
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return self.handle_error(e, context, default_return)

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
        # Create a simplified URL for logging
        # Extract domain and path for cleaner logs
        simple_url = url
        if len(url) > 60:  # Only simplify long URLs
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path if parsed.path else "/"
                simple_url = f"{parsed.netloc}{path}"
                if len(simple_url) > 60:
                    simple_url = f"{simple_url[:57]}..."
            except:
                # If parsing fails, use a basic truncation
                simple_url = f"{url[:57]}..."

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Fetching URL (attempt {attempt}/{self.max_retries}): {url}")
                if attempt > 1:
                    logger.info(f"Retry attempt {attempt}/{self.max_retries} for {simple_url}")

                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.text

                # Log an appropriate warning based on status code
                if 400 <= response.status_code < 500:
                    logger.warning(f"Client error: Failed to fetch {simple_url}, status code: {response.status_code}")
                    # For 4XX client errors, only retry 429 (Too Many Requests)
                    if response.status_code != 429:
                        logger.debug(f"Not retrying client error {response.status_code} for URL: {url}")
                        break
                elif 500 <= response.status_code < 600:
                    logger.warning(f"Server error: Failed to fetch {simple_url}, status code: {response.status_code}")
                    # 5XX errors are worth retrying as they are often temporary
                    pass
                else:
                    logger.warning(f"Unexpected status code: {response.status_code} for {simple_url}")
                    break

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout error (attempt {attempt}/{self.max_retries}) for {simple_url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt}/{self.max_retries}) for {simple_url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error (attempt {attempt}/{self.max_retries}) for {simple_url}")
                logger.debug(f"Request error details: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error (attempt {attempt}/{self.max_retries}) for {simple_url}")
                logger.debug(f"Error details: {e}")

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                # Use exponential backoff for retries
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.debug(f"Waiting {delay} seconds before retry {attempt+1}/{self.max_retries}")
                time.sleep(delay)

        logger.error(f"Failed to fetch {simple_url} after {self.max_retries} attempts")
        logger.debug(f"Failed URL: {url}")
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
            return HtmlUtils.parse_html(html)
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
        source_name = source if source else self.source_name

        # Ensure title isn't empty
        title_str = "" if not title or title == ":" else title

        # Standardize the date format for all events
        date_str = self._standardize_date_format(date)

        # Ensure all values are strings
        return {
            'title': str(title_str),
            'date': str(date_str),
            'location': str(location),
            'description': str(description),
            'url': str(url),
            'source': str(source_name)
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

        # Use instance max_pages if not provided, ensure it's an int
        pages_to_fetch = self.max_pages if max_pages is None else int(max_pages)

        all_events = []
        current_page = 1
        current_url = start_url

        while current_page <= pages_to_fetch:
            # Use a simplified log message for cleaner output
            # Only include the full URL in debug mode
            logger.debug(f"Fetching page {current_page}: {current_url}")
            logger.info(f"Processing page {current_page}")

            # Fetch and parse the page
            soup = self.fetch_and_parse(current_url)
            if not soup:
                logger.error(f"Failed to fetch or parse page {current_page}")
                break

            # Extract events from this page
            page_events = extract_page_events(soup)
            all_events.extend(page_events)
            logger.info(f"Found {len(page_events)} events on page {current_page}")

            # Check if we should continue to the next page
            if current_page >= pages_to_fetch:
                break

            # Find the next page link
            if not next_page_selector:
                break

            next_link = soup.select_one(next_page_selector)
            if not next_link:
                logger.info(f"No next page link found on page {current_page}")
                break

            # Get the next page URL - handle potential None or list values
            href = next_link.get('href')
            if not href:
                logger.info(f"No href attribute found in next link on page {current_page}")
                break

            # Convert href to string if it's a list (sometimes BeautifulSoup returns attributes as lists)
            next_url = href[0] if isinstance(href, list) else href

            # Ensure next_url is a string
            next_url = str(next_url)

            # Make absolute URL if it's relative
            if not next_url.startswith(('http://', 'https://')):
                next_url = self.make_absolute_url(next_url)

            # Update for the next iteration
            current_url = next_url
            current_page += 1

        logger.info(f"Finished pagination, found {len(all_events)} events in total")
        return all_events

    def clean_date_text(self, date_text: str) -> str:
        """Clean and format date text.

        Common method to handle various date formats consistently.

        Args:
            date_text: The raw date text to clean

        Returns:
            Cleaned date string
        """
        if not date_text:
            return ""

        # Remove any HTML tags that might be present
        date_text = re.sub(r'<[^>]+>', '', date_text)

        # Remove common prefixes
        prefixes = ['fecha:', 'fecha', 'desde el', 'desde', 'a partir del']
        for prefix in prefixes:
            if date_text.lower().startswith(prefix):
                date_text = date_text[len(prefix):].strip()

        # Handle different date formats

        # Format: "Del 23 al 27 de mayo"
        del_al_match = re.search(r'del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)', date_text, re.IGNORECASE)
        if del_al_match:
            start_day = del_al_match.group(1)
            end_day = del_al_match.group(2)
            month = del_al_match.group(3)
            return f"{start_day} - {end_day} de {month.lower()}"

        # Format: "23 - 27 mayo" or "23-27 mayo"
        range_match = re.search(r'(\d{1,2})\s*[-\/]\s*(\d{1,2})\s+(?:de\s+)?([a-zA-Z]+)', date_text, re.IGNORECASE)
        if range_match:
            start_day = range_match.group(1)
            end_day = range_match.group(2)
            month = range_match.group(3)
            return f"{start_day} - {end_day} de {month.lower()}"

        # Format: "23 de mayo"
        single_day_match = re.search(r'(\d{1,2})\s+(?:de\s+)?([a-zA-Z]+)', date_text, re.IGNORECASE)
        if single_day_match:
            day = single_day_match.group(1)
            month = single_day_match.group(2)
            return f"{day} de {month.lower()}"

        # Format: "Mayo 2023" (whole month)
        month_year_match = re.search(r'([a-zA-Z]+)\s+\d{4}', date_text, re.IGNORECASE)
        if month_year_match:
            month = month_year_match.group(1)
            return f"Todo el mes de {month.lower()}"

        # If no patterns match, just clean up the text
        clean_text = date_text.strip()
        if clean_text:
            return clean_text

        # If nothing works, return empty string
        return ""

    def extract_location_from_text(self, text: str, default_location: str = "") -> str:
        """Extract location from text content.

        Searches for common location patterns in text.

        Args:
            text: Text to search for location
            default_location: Default location to return if none found

        Returns:
            Extracted location or default location
        """
        if not text:
            return default_location

        # Look for location patterns
        location_patterns = [
            # "Lugar: Teatro Palacio Valdés"
            re.search(r'lugar:?\s+([^\.]+)', text, re.IGNORECASE),
            # "en el Teatro Palacio Valdés"
            re.search(r'en\s+(?:el|la|los|las)\s+([^\.]+)', text, re.IGNORECASE),
            # "Localización: Centro Niemeyer"
            re.search(r'localizaci[óo]n:?\s+([^\.]+)', text, re.IGNORECASE),
            # "ubicado en Centro Niemeyer"
            re.search(r'ubicado\s+en\s+([^\.]+)', text, re.IGNORECASE),
        ]

        for pattern in location_patterns:
            if pattern:
                location = pattern.group(1).strip()
                if location:
                    return location

        # Check if we can extract from title as fallback
        title_location = self.text_processor.extract_location_from_title(text)
        if title_location:
            return title_location

        return default_location

    def get_spanish_month(self, month_num: int) -> str:
        """Get Spanish month name from number.

        Args:
            month_num: Month number (1-12)

        Returns:
            Spanish name of the month
        """
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]

        if 1 <= month_num <= 12:
            return months[month_num - 1]
        return ""