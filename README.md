# ExplorAstur

ExplorAstur is a minimal web scraper that finds events happening in Asturias, Spain from the Telecable blog and outputs them to a markdown file.

## Setup

### Requirements
- Python 3.13+
- Required packages: requests, beautifulsoup4

### Quick Start

1. **Install dependencies**:
   ```bash
   pip install requests beautifulsoup4
   ```

2. **Run the scraper**:
   ```bash
   python scraper.py
   ```

3. **View the results** in the `output` directory

## How It Works

The tool is extremely simple:
1. Fetches content from the Telecable blog
2. Parses events from HTML content
3. Organizes them into a markdown file

## Project Structure

The project couldn't be more minimal:

```
explorastur/
├── scraper.py           # The scraper code (everything in one file)
├── README.md            # Documentation
├── logs/                # Log files (created automatically)
└── output/              # Generated output (created automatically)
    └── events_*.md      # Markdown event listing
```

## Troubleshooting

- **Missing data**: Check if the Telecable blog structure has changed
- **Connection errors**: Ensure you have a stable internet connection

## Important Notes

- Web scraping may be subject to legal restrictions. Always check the terms of service.
- Website structures change over time. You may need to adjust the scraper occasionally.

## Planned Source

[Viescu](https://viescu.info/)
[Biodevas](https://biodevas.org/)
[Aviles](https://aviles.es/proximos-eventos)
[Visit Oviedo](https://www.visitoviedo.info/agenda)
[Cines Embajadores](https://cinesembajadores.es/oviedo/)
[Centros Sociales](https://www.oviedo.es/centrossociales/avisos)
[Ficx](https://ficx.tv/actividades/programa-actividades-toma-3/)
[Yelmo Cines](https://yelmocines.es/cartelera/asturias/los-prados)
[Blog Telecable](https://blog.telecable.es/agenda-planes-asturias/)
[Turismo Asturias](https://www.turismoasturias.es/agenda-de-asturias)

## License

[MIT License]
