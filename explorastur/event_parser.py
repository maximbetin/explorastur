"""Module for parsing, validating, and formatting event data."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Event(BaseModel):
  """Model representing an event with validation."""

  title: str
  date: Optional[str] = None
  time: Optional[str] = None
  location: Optional[str] = None
  description: Optional[str] = None

  @validator("date", pre=True)
  def validate_date(cls, v):
    """Validate and normalize date format if possible."""
    if not v:
      return v

    # Try to parse and normalize date if it's in a recognizable format
    try:
      # Try different date formats
      for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y"):
        try:
          parsed_date = datetime.strptime(v, fmt)
          return parsed_date.strftime("%Y-%m-%d")  # Normalize to ISO format
        except ValueError:
          continue
    except Exception:
      # If we can't parse it, return as is
      pass

    return v


def parse_events(events_data: List[Dict[str, Any]]) -> List[Event]:
  """
  Parse and validate a list of event dictionaries into Event objects.

  Args:
      events_data: List of event dictionaries from the LLM

  Returns:
      List of validated Event objects
  """
  validated_events = []

  for event_dict in events_data:
    try:
      event = Event(**event_dict)
      validated_events.append(event)
    except Exception as e:
      # Log the error but continue processing other events
      print(f"Error validating event: {e}")

  return validated_events


def format_events(events: List[Event], format_type: str = "json") -> str:
  """
  Format a list of events into the specified output format.

  Args:
      events: List of Event objects
      format_type: Output format type (json, console)

  Returns:
      Formatted events as a string
  """
  if format_type == "json":
    # Convert to JSON
    return json.dumps([event.dict() for event in events], indent=2)

  elif format_type == "console":
    # Format for console output
    output = []

    for i, event in enumerate(events, 1):
      event_dict = event.dict()
      output.append(f"Event {i}:")
      output.append(f"  Title: {event_dict['title']}")

      for field in ["date", "time", "location", "description"]:
        if event_dict.get(field):
          output.append(f"  {field.capitalize()}: {event_dict[field]}")

      output.append("")  # Empty line between events

    return "\n".join(output)

  else:
    raise ValueError(f"Unsupported format type: {format_type}")
