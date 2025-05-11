# ExplorAstur

ExplorAstur is a minimal web scraper that finds events happening in Asturias, Spain from the Telecable blog and outputs them to a markdown file.

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
1. Fetches content from the Telecable blog
2. Parses events from HTML content
3. Organizes them into a chronological list in a markdown file
4. Each source is presented under its own header

## Date and Month Handling

The system is designed to work with any month or year:

- **Automatic date detection**: The scraper extracts date information from the event titles and descriptions, supporting various formats (single day, ranges, month-long events)
- **Month-independent parsing**: All date processing works with any Spanish month name (enero, febrero, marzo, etc.)
- **Current month awareness**: The system knows the current month and can handle relative date references like "todo el mes" (all month long)
- **Chronological sorting**: Events are sorted by month and then by day, with month-long events appearing first

This means the scraper will continue to work correctly throughout the year without requiring manual updates to the code when the month changes.

## Output Format

Events are presented in a single chronological list with the following format:

```
# Eventos en Asturias

_Actualizado: 11/05/2025_

## [Blog Telecable](https://blog.telecable.es/agenda-planes-asturias/)

**Durante todo el mes de mayo**: "Estaciones interiores"
   - Lugar: Museo de Bellas Artes de Asturias (Oviedo)
   - Link: https://www.museobbaa.com/exposicion/covadonda-valdes-more-estaciones-interiores/

**11 de mayo**: "Querencia"
   - Lugar: Teatro Palacio Valdés de Avilés
   - Link: https://antonionajarro.com/querencia/
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
- Each scraper is responsible for obtaining raw event data

### processor.py
- `EventProcessor`: Processes raw events
  - Filters out past events
  - Cleans and enhances data (extracting locations, fixing formatting)
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

- **Missing data**: Check if the Telecable blog structure has changed
- **Connection errors**: Ensure you have a stable internet connection

## Important Notes

- Web scraping may be subject to legal restrictions. Always check the terms of service.
- Website structures change over time. You may need to adjust the scraper occasionally.

## Planned Sources

- [Viescu](https://viescu.info/)
- [Biodevas](https://biodevas.org/)
- [Aviles](https://aviles.es/proximos-eventos)
- [Visit Oviedo](https://www.visitoviedo.info/agenda)
- [Cines Embajadores](https://cinesembajadores.es/oviedo/)
- [Centros Sociales](https://www.oviedo.es/centrossociales/avisos)
- [Ficx](https://ficx.tv/actividades/programa-actividades-toma-3/)
- [Yelmo Cines](https://yelmocines.es/cartelera/asturias/los-prados)
- [Turismo Asturias](https://www.turismoasturias.es/agenda-de-asturias)

## License

[MIT License]
