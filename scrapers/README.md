# ExplorAstur Scrapers

This directory contains the web scrapers for the ExplorAstur project, which collect event information from various websites in Asturias.

## Directory Structure

- `base.py`: The base scraper class with common functionality
- `config.py`: Centralized configuration for all scrapers
- `template.py`: A minimal skeleton template for creating new scrapers
- `__init__.py`: Package initialization and exports
- Individual scraper files (e.g., `telecable.py`, `aviles.py`, etc.)

## Creating a New Scraper

To create a new scraper:

1. Copy `template.py` to a new file with an appropriate name (e.g., `new_source.py`)
2. Rename the class to match your scraper (e.g., `NewSourceScraper`)
3. Add your scraper configuration to `config.py` in the `SITE_CONFIGS` dictionary
4. Implement the required methods in your scraper class
5. Register your scraper in `__init__.py` by importing it and adding it to `__all__`

## Base Scraper Class

The `EventScraper` base class in `base.py` provides common functionality:

- Configuration handling
- HTML fetching with retry logic
- Event standardization
- Pagination processing
- Date formatting

## Utility Functions

The `scraper_utils.py` module provides reusable utility functions:

### HTML Parsing

- `parse_html(html)`: Parse HTML content into a BeautifulSoup object
- `extract_text(element, selector)`: Extract text from an element using a CSS selector
- `extract_attribute(element, selector, attribute)`: Extract an attribute from an element

### URL Handling

- `make_absolute_url(base_url, relative_url)`: Convert a relative URL to an absolute URL
- `extract_url_from_element(element, base_url)`: Extract a URL from an element
- `extract_url_from_onclick(element, base_url, pattern)`: Extract URL from an onclick attribute

### Date Extraction

- `extract_date_from_text(text)`: Extract date information from text
- `extract_time_from_text(text)`: Extract time information from text
- `format_date_range(start_day, end_day, month)`: Format a date range
- `get_spanish_month_name(month_num)`: Get Spanish month name from month number

### Location Extraction

- `extract_location_from_text(text)`: Extract location information from text

### Event Extraction

- `extract_common_event_data(container, selectors, base_url)`: Extract common event data from a container
- `process_pagination(soup, selector, extract_func, base_url, max_pages)`: Process pagination
- `clean_event_title(title)`: Clean up an event title

## Example Usage

Here's a minimal example of how to implement a scraper:

```python
from scrapers.base import EventScraper
from scraper_utils import extract_common_event_data

class ExampleScraper(EventScraper):
    def __init__(self, config=None):
        super().__init__(config)

    def scrape(self):
        events = []

        # Fetch and parse the HTML
        soup = self.fetch_and_parse(self.url)
        if not soup:
            return []

        # Find event containers
        event_containers = soup.select('.event-item')

        # Define selectors for common data
        selectors = {
            'title': '.event-title',
            'date': '.event-date',
            'location': '.event-location',
            'url': 'a.event-link'
        }

        # Process each container
        for container in event_containers:
            # Extract data
            data = extract_common_event_data(container, selectors, self.base_url)

            # Create standardized event
            event = self.create_event(
                title=data['title'],
                date=data['date'],
                location=data['location'],
                url=data['url']
            )

            events.append(event)

        return events
```

## Best Practices

1. Use the utility functions in `scraper_utils.py` whenever possible
2. Handle errors gracefully and log appropriate messages
3. Follow the established patterns for date and location extraction
4. Use the base class's `create_event()` method to standardize event data
5. Keep scraper-specific logic to a minimum by leveraging common utilities