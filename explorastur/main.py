"""Main module for the Explorastur application."""
import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Any, Union

from explorastur.config import DEFAULT_OUTPUT_FORMAT, DEFAULT_OUTPUT_FILE, DEFAULT_PROMPT_TEMPLATE
from explorastur.html_fetcher import get_html_content
from explorastur.llm_client import LLMClient
from explorastur.event_parser import parse_events, format_events, Event


def extract_events_from_source(
    source: str,
    selector: Optional[str] = None,
    prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
    api_base_url: Optional[str] = None
) -> List[Event]:
  """
  Extract events from a source (URL or HTML content).

  Args:
      source: URL or HTML content
      selector: Optional CSS selector to filter content
      prompt_template: Template for the LLM prompt
      api_base_url: Optional custom API URL for the LLM

  Returns:
      List of extracted event objects
  """
  # Step 1: Get HTML content
  html_content = get_html_content(source, selector)

  if not html_content:
    raise ValueError("No HTML content found or extracted")

  # Step 2: Process with LLM
  llm_client = LLMClient(api_base_url) if api_base_url else LLMClient()

  try:
    events_data = llm_client.extract_events(html_content, prompt_template)
    llm_client.close()

    # Step 3: Parse and validate events
    events = parse_events(events_data)
    return events

  finally:
    llm_client.close()


def save_events(events: List[Event], output_format: str = DEFAULT_OUTPUT_FORMAT, output_file: Optional[str] = None):
  """
  Save or display the extracted events.

  Args:
      events: List of Event objects
      output_format: Format to output (json, console)
      output_file: Optional file path to save results
  """
  # Format the events
  formatted_output = format_events(events, output_format)

  # Output based on configuration
  if output_file:
    with open(output_file, "w", encoding="utf-8") as f:
      f.write(formatted_output)
    print(f"Events saved to {output_file}")
  else:
    print(formatted_output)


def main():
  """Main entry point for the command-line interface."""
  parser = argparse.ArgumentParser(description="Extract event information from web pages using a local LLM")

  # Input source arguments
  source_group = parser.add_mutually_exclusive_group(required=True)
  source_group.add_argument("--url", help="URL to fetch HTML content from")
  source_group.add_argument("--html", help="HTML content string or file path")

  # Optional arguments
  parser.add_argument("--selector", help="CSS selector to filter HTML content")
  parser.add_argument("--llm-api", help="Base URL for the LLM API")
  parser.add_argument("--format", choices=["json", "console"], default=DEFAULT_OUTPUT_FORMAT,
                      help="Output format")
  parser.add_argument("--output", help="Output file path")

  args = parser.parse_args()

  try:
    # Determine the source
    if args.url:
      source = args.url
    elif args.html:
      # Check if it's a file path
      if os.path.isfile(args.html):
        with open(args.html, "r", encoding="utf-8") as f:
          source = f.read()
      else:
        source = args.html

    # Extract events
    events = extract_events_from_source(
        source=source,
        selector=args.selector,
        api_base_url=args.llm_api
    )

    # Save or display events
    save_events(
        events=events,
        output_format=args.format,
        output_file=args.output
    )

    return 0

  except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
  sys.exit(main())
