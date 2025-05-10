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

## License

[MIT License]
