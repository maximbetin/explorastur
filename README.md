# ExplorAstur

ExplorAstur is a simple web scraper that finds events happening in Asturias, Spain and outputs them to a markdown file.

## Setup

### Requirements
- Python 3.13+
- Required packages: requests, beautifulsoup4, pyyaml

### Quick Start

1. **Install dependencies**:
   ```bash
   pip install requests beautifulsoup4 pyyaml
   ```

2. **Run the scraper**:
   ```bash
   python scraper.py
   ```

3. **View the results** in the `output` directory

## How It Works

The tool is simple:
1. Loads source configurations from `config.yaml`
2. Fetches content from each website
3. Parses events from HTML content
4. Organizes them into a markdown file by category

## Configuration

Just add sources to `config.yaml`:

```yaml
# Sources
sources:
  - name: Blog Telecable Asturias
    url: https://blog.telecable.es/agenda-planes-asturias/
    category: Oficial
```

## Project Structure

The project is minimal:

```
explorastur/
├── config.yaml          # Configuration file
├── scraper.py           # The scraper code (everything in one file)
├── README.md            # Documentation
├── logs/                # Log files (created automatically)
└── output/              # Generated output (created automatically)
    └── events_*.md      # Markdown event listing
```

## Troubleshooting

- **Missing data**: Check the website structure hasn't changed
- **Connection errors**: Ensure you have a stable internet connection

## Important Notes

- Web scraping may be subject to legal restrictions. Always check the terms of service.
- Website structures change over time. You may need to adjust the scraper occasionally.

## License

[MIT License]
