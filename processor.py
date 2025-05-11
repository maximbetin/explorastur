#!/usr/bin/env python3
"""
ExplorAstur - Event processor module
---------------------------------------------------------
Contains the EventProcessor class for filtering and formatting events.
"""

import datetime
import logging
import re
from utils import DateProcessor, TextProcessor

logger = logging.getLogger('explorastur')

class EventProcessor:
    """Class to filter, sort, and format events."""

    def __init__(self):
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()

    def process_events(self, events):
        """
        Process events by filtering out past events,
        fixing incomplete data, and sorting by date.
        """
        if not events:
            return []

        # Current date to filter events
        current_date = datetime.datetime.now().day

        # Filter to future events only
        filtered_events = []
        for event in events:
            # Skip events with no title or date
            if not event['title'] or not event['date']:
                continue

            # Skip non-events (like "Talleres" header sections)
            if self.text_processor.is_non_event(event['title']):
                continue

            # Check if the event is in the future
            if self.date_processor.is_future_event(event['date'], current_date):
                # Fix incomplete descriptions
                if not event['description'] and event['title']:
                    event['description'] = self.text_processor.fix_incomplete_description(
                        event['title'], event['description']
                    )

                # Get location from title if missing
                if not event['location'] and event['title']:
                    event['location'] = self.text_processor.extract_location_from_title(event['title'])

                # If location is still missing, try to extract from description
                if not event['location'] and event['description']:
                    event['location'] = self._extract_location_from_description(event['description'])

                # Clean up the location field
                if event['location']:
                    event['location'] = self._clean_location(event['location'])

                filtered_events.append(event)

        # Sort events by date
        filtered_events.sort(
            key=lambda x: self.date_processor.date_sort_key(x['date'])
        )

        return filtered_events

    def _extract_location_from_description(self, description):
        """Extract location information from the description"""
        # Common venue patterns in descriptions
        venue_patterns = [
            r'en (?:el|la|los|las)?\s+((?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría|Museo)[^\.]+)',
            r'en (?:el|la|los|las)?\s+((?:Gijón|Oviedo|Avilés)[^\.]+)',
        ]

        for pattern in venue_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()

        return ""

    def _clean_location(self, location):
        """Clean up location text to extract just the venue and city"""
        if not location:
            return ""

        # Fix concatenated words first
        location = re.sub(r'([a-z])([A-Z])', r'\1 \2', location)

        # Fix missing spaces after punctuation
        location = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', location)
        location = re.sub(r'([a-zA-Z]),([A-Z])', r'\1, \2', location)
        location = re.sub(r'([a-zA-Z])"([a-zA-Z])', r'\1" \2', location)

        # Fix specific concatenation issues
        location = re.sub(r'la([A-Z])', r'la \1', location)
        location = re.sub(r'el([A-Z])', r'el \1', location)
        location = re.sub(r'de([A-Z])', r'de \1', location)
        location = re.sub(r'del([A-Z])', r'del \1', location)
        location = re.sub(r'un([A-Z])', r'un \1', location)

        # Remove common Spanish prefixes
        location = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', location)
        location = re.sub(r'^en\s+', '', location)

        # Fix special case patterns
        location = re.sub(r'el día$', '', location)
        location = re.sub(r'con la banda.*$', '', location)
        location = re.sub(r'para presentar.*$', '', location)

        # Extract venue and city when possible using more flexible patterns
        venue_city_pattern = r'([^,.]+(?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría|Museo|Arena)[^,.]+)(?:de|en)\s+([^,.]+)'
        match = re.search(venue_city_pattern, location)
        if match:
            venue = match.group(1).strip()
            city = match.group(2).strip()
            # Remove any trailing dates or times
            city = re.sub(r'\d+\s+de\s+\w+$', '', city).strip()
            city = re.sub(r'el\s+\w+\s+\d+$', '', city).strip()
            return f"{venue} ({city})"

        # If the pattern didn't match but there's a venue keyword, clean it up
        venue_keywords = ['Teatro', 'Auditorio', 'Centro', 'Sala', 'Pabellón', 'Plaza', 'Factoría', 'Museo', 'Recinto']
        for keyword in venue_keywords:
            if keyword in location:
                # Just clean up the location without trying to separate venue/city
                location = re.sub(r'\d+\s+de\s+\w+', '', location).strip()
                location = re.sub(r'el\s+\w+\s+\d+', '', location).strip()
                return location

        return location.strip()

    def format_to_markdown(self, events):
        """
        Format the events list to a markdown file with all events in a single list.
        Events with the same date (such as "Durante todo el mes de mayo") will be grouped together.
        """
        if not events:
            return "# No events found"

        # Start building markdown
        markdown = "# Eventos en Asturias\n\n"
        markdown += f"_Actualizado: {datetime.datetime.now().strftime('%d/%m/%Y')}_\n\n"

        # Add source link as a header
        markdown += "## [Blog Telecable](https://blog.telecable.es/agenda-planes-asturias/)\n\n"

        # Sort all events by date
        events.sort(key=lambda x: self.date_processor.date_sort_key(x['date']))

        # Group events by date
        events_by_date = {}
        for event in events:
            date = event['date']
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)

        # Add all events grouped by date
        for date, date_events in events_by_date.items():
            # Add the date as a header
            markdown += f"**{date}**:\n"

            # Add each event under this date
            for event in date_events:
                # Clean up the title - remove any quotes
                title = event['title']
                if title.startswith('"') and title.endswith('"'):
                    title = title[1:-1]
                elif title.startswith('"'):
                    title = title[1:]
                elif title.endswith('"'):
                    title = title[:-1]
                # Remove any remaining quotes anywhere in the title
                title = title.replace('"', '')

                # Add the event title without quotes
                markdown += f"   - {title}\n"

                # Add location if available and not just "Asturias" - use "Lugar" in Spanish
                if event['location'] and event['location'].lower() != 'asturias':
                    markdown += f"     - Lugar: {event['location']}\n"

                # Add URL if available
                if event['url']:
                    markdown += f"     - Link: {event['url']}\n"

                # Add a small gap between events with the same date
                markdown += "\n"

            # Add an extra line break between different dates
            markdown += "\n"

        return markdown