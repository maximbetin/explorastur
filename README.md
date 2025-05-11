# ExplorAstur

ExplorAstur is a minimal web scraper that finds events happening in Asturias, Spain from multiple sources and outputs them to a markdown file.

## Setup

### Requirements
- Python 3.13+
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

## How It Works

The tool is extremely simple:
1. Fetches content from multiple event sources
2. Handles pagination to collect all available events
3. Parses events from HTML content
4. Organizes them into a chronological list in a markdown file
5. Each source is presented under its own header

## Current Event Sources

- **[Telecable Blog](https://blog.telecable.es/agenda-planes-asturias/)**: A monthly article with event listings
- **[Turismo Asturias](https://www.turismoasturias.es/agenda-de-asturias)**: The official tourism website for Asturias with pagination support
- **[Centros Sociales Oviedo](https://www.oviedo.es/centrossociales/avisos)**: Events from Oviedo's network of social centers

## Features

### Pagination Support

The Turismo Asturias scraper now supports pagination, allowing it to:
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

## Output Format

Events are grouped by source and presented chronologically, with the following format:

```
# Eventos en Asturias

_Actualizado: 11/05/2025_

## [Telecable](https://blog.telecable.es/agenda-planes-asturias/)

**Durante todo el mes de mayo**: Estaciones interiores
   - Lugar: Museo de Bellas Artes de Asturias (Oviedo)
   - Link: https://www.museobbaa.com/exposicion/covadonda-valdes-more-estaciones-interiores/

## [Turismo Asturias](https://www.turismoasturias.es/agenda-de-asturias)

**9 mayo - 18 mayo**: Jornadas Gastronómicas de la Llámpara. Villaviciosa
   - Lugar: Quintes y Quintueles
   - Link: https://www.turismoasturias.es/agenda-de-asturias/-/calendarsuite/event/...
```

## Project Structure

```
explorastur/
├── main.py              # Main entry point and script execution
├── processor.py         # Event processing logic
├── scrapers.py          # Web scraping implementations
├── utils.py             # Utility classes for text and date processing
├── requirements.txt     # Python dependencies
├── README.md            # Documentation
├── logs/                # Log files (created automatically)
└── output/              # Generated output (created automatically)
    └── events_*.md      # Markdown event listing
```

## Architecture & Module Responsibilities

### main.py
- Program entry point
- Configures logging
- Creates necessary directories
- Orchestrates the overall process flow
- Handles errors and exceptions

### utils.py
- Houses utility classes for common operations:
  - `DateProcessor`: Handles date parsing, formatting, and comparison
  - `TextProcessor`: Manages text cleaning, extraction, and formatting

### scrapers.py
- Contains scraper implementations
- Base class `EventScraper`: Defines interface for all scrapers
- `TelecableScraper`: Implementation for Telecable blog
- `TurismoAsturiaScraper`: Implementation for Turismo Asturias website with pagination support
- `OviedoCentrosSocialesScraper`: Implementation for Oviedo's social centers events
- Each scraper is responsible for obtaining raw event data

### processor.py
- `EventProcessor`: Processes raw events
  - Filters out past events
  - Cleans and enhances data (extracting locations, fixing formatting)
  - Groups events by source
  - Formats events to markdown output in chronological order

## Data Flow

1. `main.py` sets up logging and calls scrapers
2. `scrapers.py` fetches and extracts raw events
3. `processor.py` processes and formats events
4. `main.py` outputs formatted events to markdown files

## Code Organization

The codebase follows these design principles:

1. **Clear Separation of Concerns**:
   - `main.py`: Application orchestration
   - `utils.py`: Reusable utilities
   - `scrapers.py`: Data acquisition
   - `processor.py`: Data processing

2. **Consistent Code Structure**:
   - Standardized imports
   - Consistent class structure
   - Clear module purposes

## Troubleshooting

- **Missing data**: Check if the website structures have changed (Telecable blog, Turismo Asturias, or Oviedo Centros Sociales)
- **Connection errors**: Ensure you have a stable internet connection

## Important Notes

- Web scraping may be subject to legal restrictions. Always check the terms of service.
- Website structures change over time. You may need to adjust the scraper occasionally.

## Planned Sources

- [Viescu](https://viescu.info/)
- [Biodevas](https://biodevas.org/)
- [Aviles](https://aviles.es/proximos-eventos)
- [Visit Oviedo Tourism](https://www.visitoviedo.info/agenda) (broader than Centros Sociales)
- [Cines Embajadores](https://cinesembajadores.es/oviedo/)
- [Ficx](https://ficx.tv/actividades/programa-actividades-toma-3/)
- [Yelmo Cines](https://yelmocines.es/cartelera/asturias/los-prados)

## License

[MIT License]
