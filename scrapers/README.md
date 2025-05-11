# ExplorAstur Scrapers

This directory contains the web scrapers for the ExplorAstur project, which collect event information from various websites in Asturias.

## Directory Structure

- `base.py`: The base scraper class with common functionality
- `config.py`: Centralized configuration for all scrapers
- `factory.py`: Factory for creating and managing scraper instances
- `template.py`: A minimal skeleton template for creating new scrapers
- `__init__.py`: Package initialization, exports, and helper functions
- Individual scraper files (e.g., `telecable.py`, `aviles.py`, etc.)

## Creating a New Scraper

To create a new scraper:

1. Copy `template.py` to a new file with an appropriate name (e.g., `new_source.py`)
2. Rename the class to match your scraper (e.g., `NewSourceScraper`)
3. Implement the required methods by following the template structure
4. Add your scraper configuration to `config.py` using the `register_config()` function
5. Register your scraper in `factory.py` using the `register_scraper()` function
6. Import and add your scraper to `__init__.py` to make it available in the package

Example of adding a new scraper:

```python
# Register config
from scrapers.config import register_config

register_config("new_source", {
    "name": "New Source",
    "url": "https://example.com/events",
    "base_url": "https://example.com"
})

# Register scraper
from scrapers.factory import register_scraper

register_scraper("new_source", "NewSourceScraper", "scrapers.new_source")
```

## Base Scraper Class

The `EventScraper` base class in `base.py` provides common functionality:

- Configuration handling
- HTML fetching with retry logic
- Event standardization
- Pagination processing
- Date formatting and cleaning
- Location extraction
- Error handling with safe execution
- Spanish month name conversion

### Common Helper Methods

The base class includes several helper methods to maintain consistency:

- `fetch_page_with_retry(url)`: Fetches a page with retry logic
- `fetch_and_parse(url)`: Fetches a page and parses it into a BeautifulSoup object
- `create_event(...)`: Creates a standardized event dictionary
- `_standardize_date_format(date_str)`: Standardizes date formats
- `clean_date_text(date_text)`: Cleans and formats date text in various formats
- `extract_location_from_text(text, default_location)`: Extracts location from text
- `get_spanish_month(month_num)`: Converts month number to Spanish name
- `process_pagination(...)`: Handles paginated sites consistently
- `handle_error(error, context, return_value)`: Standard error handling
- `safe_execute(func, context, default_return, *args, **kwargs)`: Executes a function with error handling

## Best Practices for Scrapers

1. **Follow the template structure**: Use the provided template as a starting point and follow its structure to ensure consistency.
2. **Use proper error handling**: Always wrap scraper logic in try/except blocks and use the `handle_error()` method.
3. **Implement pagination correctly**: Use the `process_pagination()` method for sites with multiple pages.
4. **Extract methods for clarity**: Create helper methods for extracting specific pieces of information.
5. **Use type hints**: Add proper type annotations to all methods for better IDE support and code quality.
6. **Use common base class methods**: Prefer using the base class helper methods instead of reimplementing functionality.
7. **Handle attribute access safely**: Always check if elements exist and handle potential None values.
8. **Convert attribute values to proper types**: Handle potential list values from BeautifulSoup attributes.
9. **Use logging appropriately**: Add informative log messages at appropriate levels.
10. **Validate extracted data**: Check that required fields are present before creating events.

## Standard Scraper Method Structure

A well-structured scraper should follow this pattern:

```python
def scrape(self) -> List[Dict[str, str]]:
    """
    Main scrape method - entry point.
    """
    logger.info(f"Fetching URL: {self.url}")

    try:
        # For simple sites
        soup = self.fetch_and_parse(self.url)
        if not soup:
            logger.error(f"Failed to fetch or parse URL: {self.url}")
            return []

        return self._extract_events_from_page(soup)

        # For paginated sites
        # return self.process_pagination(
        #     base_url=self.base_url,
        #     start_url=self.url,
        #     extract_page_events=self._extract_events_from_page,
        #     next_page_selector='.pagination .next-page'
        # )
    except Exception as e:
        return self.handle_error(e, "scraping events", [])

def _extract_events_from_page(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract events from a single page.
    """
    events = []

    # Find all event containers
    event_containers = soup.select('.event-container')
    logger.info(f"Found {len(event_containers)} event containers")

    # Process each container
    for container in event_containers:
        try:
            event = self._extract_event_from_container(container)
            if event:
                events.append(event)
        except Exception as e:
            logger.error(f"Error extracting event: {e}")
            # Continue with the next event

    logger.info(f"Found {len(events)} events")
    return events

def _extract_event_from_container(self, container: Tag) -> Optional[Dict[str, str]]:
    """
    Extract data from a single event container.
    """
    try:
        # Extract title
        title_element = container.select_one('.event-title')
        if not title_element:
            return None
        title = title_element.get_text().strip()
        title = self.text_processor.clean_title(title)

        # Extract event URL (with safe type handling)
        link_element = container.select_one('a.event-link')
        event_url = ""
        if link_element:
            href = link_element.get('href')
            if href:
                # Handle href potentially being a list
                event_url = href[0] if isinstance(href, list) else href
                event_url = str(event_url)

        # Make URL absolute if needed
        if event_url and not event_url.startswith(('http://', 'https://')):
            event_url = make_absolute_url(self.base_url, event_url)

        # Extract and clean date
        date_element = container.select_one('.event-date')
        date = date_element.get_text().strip() if date_element else ''
        date = self.clean_date_text(date)

        # Extract location with fallback
        location_element = container.select_one('.event-location')
        location = location_element.get_text().strip() if location_element else ''

        # If no location found, try to extract from text
        if not location:
            container_text = container.get_text()
            location = self.extract_location_from_text(
                container_text,
                default_location=self.source_name
            )

        # Create standardized event
        return self.create_event(
            title=title,
            date=date,
            location=location,
            url=event_url
        )
    except Exception as e:
        logger.error(f"Error extracting event details: {e}")
        return None
```

## Using the Factory and Helpers

The package provides helper functions to easily create and run scrapers:

```python
from scrapers import create_scraper, run_scraper, run_all_scrapers, get_available_scrapers

# Get all available scrapers
scraper_ids = get_available_scrapers()
print(f"Available scrapers: {scraper_ids}")

# Run a specific scraper
events = run_scraper("telecable")
print(f"Found {len(events)} events from Telecable")

# Run all scrapers
all_events = run_all_scrapers()
for source, events in all_events.items():
    print(f"Found {len(events)} events from {source}")
```

## Debug and Testing

When debugging a scraper, you can run it directly:

```python
from scrapers.telecable import TelecableScraper
from scrapers.config import get_config_for_scraper

# Create a single scraper instance
config = get_config_for_scraper("telecable")
scraper = TelecableScraper(config)

# Run the scraper
events = scraper.scrape()
print(f"Found {len(events)} events")

# Examine the first event
if events:
    print(events[0])
```

## Event Structure

All scraped events should follow this standardized format:

```python
{
    'title': 'Event Title',
    'date': '15 de mayo a las 20:00',
    'location': 'Teatro Campoamor, Oviedo',
    'description': 'Optional description text',
    'url': 'https://example.com/event/123',
    'source': 'Source Name'
}
```

## Type Consistency

All scrapers should use consistent type annotations:

```python
from typing import Dict, List, Optional, Any, cast
from bs4 import BeautifulSoup, Tag

def scrape(self) -> List[Dict[str, str]]:
    ...

def _extract_events_from_page(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
    ...

def _extract_event_from_container(self, container: Tag) -> Optional[Dict[str, str]]:
    ...
```