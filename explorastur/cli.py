"""Command-line interface for testing URL event extraction."""
import argparse
import json
import sys
from typing import List, Optional
from pathlib import Path

from explorastur.url_processor import URLEventProcessor, ProcessingResult


def format_result(result: ProcessingResult, format_type: str = "json") -> str:
  """Format a processing result for output."""
  if format_type == "json":
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

  # Console format
  output = [f"\nURL: {result.url}"]
  if result.error:
    output.append(f"Error: {result.error}")
  else:
    output.append(f"Found {len(result.events)} events:")
    for i, event in enumerate(result.events, 1):
      event_dict = event.dict()
      output.append(f"\nEvent {i}:")
      output.append(f"  Title: {event_dict['title']}")
      for field in ["date", "time", "location", "description"]:
        if event_dict.get(field):
          output.append(f"  {field.capitalize()}: {event_dict[field]}")

  return "\n".join(output)


def save_results(results: List[ProcessingResult], output_file: Optional[str] = None):
  """Save or display processing results."""
  formatted = [result.to_dict() for result in results]

  if output_file:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
      json.dump(formatted, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {output_file}")
  else:
    print(json.dumps(formatted, indent=2, ensure_ascii=False))


def main():
  """Main entry point for the CLI."""
  parser = argparse.ArgumentParser(
      description="Extract event information from URLs using LLM"
  )

  # Input arguments
  input_group = parser.add_mutually_exclusive_group(required=True)
  input_group.add_argument("--url", help="Single URL to process")
  input_group.add_argument("--urls", help="File containing URLs to process (one per line)")
  input_group.add_argument("--url-list", nargs="+", help="List of URLs to process")

  # Optional arguments
  parser.add_argument("--llm-api", help="Base URL for the LLM API")
  parser.add_argument("--format", choices=["json", "console"], default="console",
                      help="Output format for single URL processing")
  parser.add_argument("--output", help="Output file for saving results")

  args = parser.parse_args()

  # Initialize processor
  processor = URLEventProcessor(api_base_url=args.llm_api) if args.llm_api else URLEventProcessor()

  try:
    # Get URLs to process
    urls: List[str] = []
    if args.url:
      urls = [args.url]
    elif args.urls:
      with open(args.urls, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    elif args.url_list:
      urls = args.url_list

    # Process URLs
    if len(urls) == 1:
      # Single URL processing
      result = processor.process_url(urls[0])
      print(format_result(result, args.format))
    else:
      # Multiple URL processing
      results = processor.process_urls(urls)
      save_results(results, args.output)

    return 0

  except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    return 1

  finally:
    processor.close()


if __name__ == "__main__":
  sys.exit(main())
