# ExplorAstur

ExplorAstur is a modular Python tool that extracts event information from web pages using a local LLM running in LM Studio. It processes URLs directly through the LLM and outputs structured event data.

## Features

- Process URLs directly through LLM for event extraction
- Support for single URL or batch processing
- Parse and validate extracted event information
- Output events in JSON or console-friendly format
- Modular design for easy extension or reuse
- Clean error handling and validation

## Requirements

- Python 3.8+
- A local LLM running in LM Studio (or compatible service) with an OpenAI-compatible API
- Required packages (see `requirements.txt`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/explorastur.git
   cd explorastur
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Command Line Interface

```bash
# Process a single URL
python -m explorastur.cli --url https://example.com/events

# Process multiple URLs
python -m explorastur.cli --url-list "https://example.com/events" "https://another-site.com/calendar"

# Process URLs from a file (one URL per line)
python -m explorastur.cli --urls urls.txt

# Specify a custom LLM API endpoint
python -m explorastur.cli --url https://example.com/events --llm-api http://localhost:1234/v1

# Output to console in a readable format
python -m explorastur.cli --url https://example.com/events --format console

# Save output to a file
python -m explorastur.cli --url https://example.com/events --output events.json
```

### Python API

```python
from explorastur import URLEventProcessor, ProcessingResult

# Initialize the processor
processor = URLEventProcessor()

# Process a single URL
result = processor.process_url("https://example.com/events")
print(f"Found {len(result.events)} events")

# Process multiple URLs
urls = [
    "https://example.com/events",
    "https://another-site.com/calendar"
]
results = processor.process_urls(urls)

# Access results
for result in results:
    if result.error:
        print(f"Error processing {result.url}: {result.error}")
    else:
        print(f"Found {len(result.events)} events at {result.url}")

# Don't forget to close the processor
processor.close()
```

## Customization

### Custom Prompt Templates

You can modify the `DEFAULT_PROMPT_TEMPLATE` in `config.py` to change how the LLM extracts event information:

```python
from explorastur.config import DEFAULT_PROMPT_TEMPLATE

# Customize the prompt
custom_prompt = """
Analyze the content at this URL and extract all upcoming events:
{url}

Return a JSON array of events with these fields:
- name: The name of the event
- start_date: When the event starts
- end_date: When the event ends
- venue: Where the event takes place
- price: The cost of attending

Return only the JSON array, no extra text.
"""

# Use the custom prompt with the processor
processor = URLEventProcessor()
result = processor.process_url("https://example.com/events", prompt_template=custom_prompt)
```

## Architecture

The project is organized into the following modules:

- `url_processor.py`: Core module for processing URLs and extracting events
- `event_parser.py`: Parses and validates extracted event data
- `config.py`: Contains configuration settings
- `cli.py`: Provides the command-line interface

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
