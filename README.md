# ExplorAstur

ExplorAstur is a minimal web scraper that finds events happening in Asturias, Spain from multiple sources and outputs them to a markdown file.

## Setup

### Requirements
- Python 3.9+
- Dependencies listed in requirements.txt

### Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the scraper**:
   ```bash
   python main.py
   ```

3. **View the results** in the `output` directory

### Command-line Arguments

The application now supports several command-line arguments:

- `--scraper`, `-s`: Specify which scrapers to run (comma-separated list of IDs)
  ```bash
  python main.py -s telecable,aviles
  ```

- `--output`, `-o`: Specify a custom output file path
  ```bash
  python main.py -o custom_output.md
  ```

- `--debug`: Enable debug logging
  ```bash
  python main.py --debug
  ```

## How It Works

The tool is extremely simple:
1. Fetches content from multiple event sources
2. Handles pagination to collect all available events
3. Parses events from HTML content
4. Organizes them into a chronological list in a markdown file
5. Each source is presented under its own header

## Current Event Sources

- **[Avilés](https://www.avilescomarca.info/agenda)**: Events from Avilés
- **[Biodevas](https://biodevas.es/agenda-biodevas/)**: Biodevas community events
- **[Telecable Blog](https://blog.telecable.es/agenda-planes-asturias/)**: A monthly article with event listings
- **[Visit Oviedo](https://www.visitoviedo.info/Oviedo/Oviedo-hoy-agenda)**: Events from Oviedo's official tourism website
- **[Turismo Asturias](https://www.turismoasturias.es/agenda)**: The official tourism website for Asturias with pagination support
- **[Centros Sociales Oviedo](https://www.oviedo.es/agenda-municipal/buscador-de-actividades-en-centros-sociales)**: Events from Oviedo's network of social centers

## Features

### Modular Architecture

The project now uses a modular architecture for better maintainability:
- Each scraper is defined in its own module file
- A configuration system centralizes all settings
- A factory pattern creates scrapers dynamically
- Error handling and retry logic are built into the base scraper class

### Pagination Support

The Turismo Asturias and Visit Oviedo scrapers support pagination, allowing them to:
- Automatically detect the total number of pages
- Navigate through all result pages (configurable max limit)
- Collect events from every page
- Handle pagination parameters in URLs

### Clean Date Formatting

The system displays dates in a clean, human-friendly format:
- No leading zeros (e.g., "1 mayo" instead of "01 mayo")
- No years (e.g., "1 mayo" instead of "1 mayo 2025")
- Clean range formatting (e.g., "9 mayo - 18 mayo")

### Concise Event Format

Events are displayed in a concise format that includes only essential information:
- Event title
- Event date
- Location (when available)
- Link to the event page
- No descriptions, keeping the output clean and easy to scan

## Date and Month Handling

The system is designed to work with any month or year:

- **Automatic date detection**: The scraper extracts date information from the event titles and descriptions, supporting various formats (single day, ranges, month-long events)
- **Month-independent parsing**: All date processing works with any Spanish month name (enero, febrero, marzo, etc.)
- **Current month awareness**: The system knows the current month and can handle relative date references like "todo el mes" (all month long)
- **Chronological sorting**: Events are sorted by month and then by day, with month-long events appearing first

This means the scraper will continue to work correctly throughout the year without requiring manual updates to the code when the month changes.

## Project Structure

```
explorastur/
├── main.py              # Main entry point and script execution
├── processor.py         # Event processing logic
├── scrapers.py          # Compatibility layer (deprecated)
├── scraper_utils.py     # Scraping utilities
├── utils.py             # Utility classes for text and date processing
├── test_scraper.py      # Debug script for testing individual scrapers
├── requirements.txt     # Python dependencies
├── README.md            # Documentation
├── scrapers/            # Modular scraper implementations
│   ├── __init__.py      # Package initialization and exports
│   ├── base.py          # Base scraper class
│   ├── config.py        # Configuration system
│   ├── factory.py       # Scraper factory
│   ├── telecable.py     # Telecable scraper
│   ├── turismo_asturias.py # Turismo Asturias scraper
│   ├── aviles.py        # Avilés scraper
│   ├── biodevas.py      # Biodevas scraper
│   ├── oviedo_announcements.py # Oviedo social centers announcements scraper
│   └── visit_oviedo.py  # Visit Oviedo scraper
├── logs/                # Log files (created automatically)
└── output/              # Generated output (created automatically)
    └── events_*.md      # Markdown event listing
```

## Architecture & Module Responsibilities

### main.py
- Program entry point
- Configures logging
- Parses command-line arguments
- Orchestrates the overall process flow
- Handles errors and exceptions

### utils.py
- Houses utility classes for common operations:
  - `DateProcessor`: Handles date parsing, formatting, and comparison
  - `TextProcessor`: Manages text cleaning, extraction, and formatting

### scraper_utils.py
- Provides common utility functions for all scrapers:
  - HTML parsing utilities (parse_html, extract_text, extract_attribute)
  - URL handling utilities (make_absolute_url, extract_url_from_element)
  - Date extraction utilities (extract_date_from_text, extract_time_from_text)
  - Location extraction utilities (extract_location_from_text)
  - Event extraction utilities (extract_common_event_data)

### scrapers/ Package
- **base.py**: Base `EventScraper` class with common functionality
  - Standardized pagination handling via `process_pagination` method
  - Consistent error handling via `handle_error` and `safe_execute` methods
  - Common utility methods for all scrapers
- **config.py**: Centralized configuration system
- **factory.py**: Factory to create scraper instances
- **telecable.py**, **turismo_asturias.py**, etc.: Individual scraper implementations

### processor.py
- `EventProcessor`: Processes raw events
  - Filters out past events
  - Cleans and enhances data (extracting locations, fixing formatting)
  - Groups events by source
  - Formats events to markdown output in chronological order

## Data Flow

1. `main.py` sets up logging and command-line arguments
2. The factory creates scrapers based on configuration or user selection
3. Each scraper fetches and extracts raw events
4. `processor.py` processes and formats events
5. `main.py` outputs formatted events to markdown files

## Code Organization

The codebase follows these design principles:

1. **Modular Architecture**:
   - Each scraper is implemented in its own file
   - Configuration is centralized and separated from the implementation
   - Factory pattern creates scraper instances dynamically

2. **Clear Separation of Concerns**:
   - `main.py`: Application orchestration
   - `utils.py`: Reusable utilities
   - `scrapers/`: Data acquisition
   - `processor.py`: Data processing

3. **Consistent Code Structure**:
   - Standardized imports
   - Consistent class structure
   - Clear module purposes
   - Standardized pagination handling
   - Consistent error handling

4. **Standardized Utilities**:
   - All HTML parsing uses the `parse_html` utility
   - All URL handling uses the `make_absolute_url` utility
   - All scrapers use the base class `process_pagination` method for pagination
   - Error handling is consistent through `handle_error` and `safe_execute` methods

## Troubleshooting

- **Website structure changes**: If a site changes its HTML structure, the scraper may stop working properly. Check for the following symptoms and solutions:
  - Missing events from a specific source: The HTML selectors may need updating
  - Incomplete data: Date or location extraction patterns may need adjustment
  - Error messages about "No events found": The website structure has likely changed significantly

- **Connection errors**:
  - Ensure you have a stable internet connection
  - Some websites may implement rate limiting or blocking of scraping activities
  - The system now includes retry logic, but some sites may still block repeated requests

- **Debugging**:
  - Use the `test_scraper.py` script to test individual scrapers:
    ```bash
    python test_scraper.py -s telecable --debug
    ```
  - Enable debug logging with the `--debug` flag for more detailed information

## Adding New Scrapers

To add a new scraper:

1. Create a new file in the `scrapers/` directory (e.g., `new_source.py`)
2. Implement a class that inherits from `EventScraper`
3. Add the scraper to the configuration in `config.py`
4. Add the class to the registry in `factory.py`

Example:

```python
# scrapers/new_source.py
from scrapers.base import EventScraper

class NewSourceScraper(EventScraper):
    def __init__(self, config=None):
        super().__init__(config)
        if not config:
            self.url = "https://example.com/events"
            self.source_name = "New Source"

    def scrape(self):
        # Your scraping logic here
        events = []
        # ... scraping code ...
        return events
```

Then add to the registry:

```python
# In scrapers/factory.py
SCRAPER_REGISTRY = {
    # ... existing registrations ...
    "new_source": {
        "class_name": "NewSourceScraper",
        "module_path": "scrapers.new_source"
    },
}
```

## License

[MIT License]