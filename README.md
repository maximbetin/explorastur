# ExplorAstur

ExplorAstur is a modular Python tool that extracts event information from web pages using a local LLM running in LM Studio. It fetches HTML content, processes it with a local LLM, and outputs structured event data.

## Features

- Fetch HTML content from URLs or process direct HTML snippets
- Extract specific content using CSS selectors
- Process HTML with a local LLM via OpenAI-compatible API
- Parse and validate extracted event information
- Output events in JSON or console-friendly format
- Modular design for easy extension or reuse

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
# Extract events from a URL
python -m explorastur.main --url https://example.com/events

# Extract events from a specific part of the page using a CSS selector
python -m explorastur.main --url https://example.com/events --selector ".event-list"

# Extract events from HTML content
python -m explorastur.main --html "<div class='event'>...</div>"

# Extract events from an HTML file
python -m explorastur.main --html path/to/file.html

# Specify a custom LLM API endpoint
python -m explorastur.main --url https://example.com/events --llm-api http://localhost:1234/v1

# Output to console in a readable format
python -m explorastur.main --url https://example.com/events --format console

# Save output to a file
python -m explorastur.main --url https://example.com/events --output events.json
```

### Python API

```python
from explorastur import extract_events_from_source, save_events

# Extract events from a URL
events = extract_events_from_source(
    source="https://example.com/events",
    selector=".event-list",  # Optional CSS selector
    api_base_url="http://localhost:1234/v1"  # Optional custom API URL
)

# Save events to a file
save_events(events, output_format="json", output_file="events.json")

# Or display in console format
save_events(events, output_format="console")
```

## Customization

### Custom Prompt Templates

You can modify the `DEFAULT_PROMPT_TEMPLATE` in `config.py` to change how the LLM extracts event information:

```python
from explorastur.config import DEFAULT_PROMPT_TEMPLATE

# Customize the prompt
custom_prompt = """
Extract the following information from the HTML content:
- name: The name of the event
- start_date: When the event starts
- end_date: When the event ends
- venue: Where the event takes place
- price: The cost of attending

HTML:
{html_content}

Format as JSON array.
"""

# Use the custom prompt
events = extract_events_from_source(
    source="https://example.com/events",
    prompt_template=custom_prompt
)
```

## Architecture

The project is organized into the following modules:

- `html_fetcher.py`: Fetches and processes HTML content
- `llm_client.py`: Communicates with the local LLM API
- `event_parser.py`: Parses and validates extracted event data
- `config.py`: Contains configuration settings
- `main.py`: Provides the CLI and orchestrates the entire process

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
