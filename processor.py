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
                # Get location from title if missing
                if not event['location'] and event['title']:
                    event['location'] = self.text_processor.extract_location_from_title(event['title'])

                # For Centro Sociales events that lack full location info
                if event['source'] == 'Centros Sociales Oviedo' and event['location']:
                    if event['location'] == 'Plaza':
                        event['location'] = 'Plaza de Asturias, Oviedo'
                    elif event['location'] == 'Centro Social El':
                        event['location'] = 'Centro Social El Cortijo, Oviedo'
                    elif event['location'] == 'Centro Social Bra':
                        event['location'] = 'Centro Social Braulio, Oviedo'
                    elif event['location'] == 'Centro Social' or event['location'] == 'Social':
                        event['location'] = 'Centro Social de Oviedo'
                    elif 'Centro Social' in event['location'] and len(event['location']) < 25:
                        # Add "Oviedo" if it's a Centro Social without a full name
                        if 'Oviedo' not in event['location']:
                            event['location'] = f"{event['location'].strip()}, Oviedo"

                # Clean up the location field
                if event['location']:
                    event['location'] = self._clean_location(event['location'])

                filtered_events.append(event)

        # Sort events by date
        filtered_events.sort(
            key=lambda x: self.date_processor.date_sort_key(x['date'])
        )

        return filtered_events

    def _clean_location(self, location):
        """Clean up location text to extract just the venue and city"""
        if not location:
            return ""

        # Replace line breaks with spaces
        location = re.sub(r'[\r\n]+', ' ', location)

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

        # Handle specific patterns before general cleaning
        # Fix specific location formatting issues
        if "El Atrio" in location and "Cuba" in location:
            return "Centro Comercial 'El Atrio' (C/ Cámara, Cuba, Dr.), Avilés"

        if "La Florida con" in location:
            return "Centro Social La Florida, Oviedo"

        if "Factoría Cultural" in location:
            return "Factoría Cultural, Avilés"

        if "NIEMEYER" in location:
            return "Centro Niemeyer, Avilés"

        # Fix "Dr," which should be "Dr." in addresses
        location = re.sub(r'Dr,', 'Dr.', location)

        # Fix Address format issues
        location = re.sub(r'C/ ([^,]+), ([^,]+), ([^,]+)$', r'C/ \1, \2, \3', location)

        # Clean up excessive commas and spacing in addresses
        location = re.sub(r',\s*,', ',', location)
        location = re.sub(r'\s+', ' ', location)

        # Remove descriptive text and limit to location name
        if len(location) > 80:
            # Try to extract just the venue name by looking for common patterns
            venue_match = re.match(r'^([^,.]+(?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría|Museo|Arena)[^,.]{0,30})', location)
            if venue_match:
                location = venue_match.group(1).strip()

            # If still too long, truncate and add ellipsis
            if len(location) > 80:
                location = location[:77] + '...'

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

        # Handle truncated locations
        if location.strip() == 'Plaza':
            return 'Plaza de Asturias, Oviedo'

        if location.strip() == 'Centro Social':
            return 'Centro Social de Oviedo'

        if 'Centro Social' in location and len(location.strip()) < 20:
            return f"{location}, Oviedo"

        # Return the cleaned location
        return location.strip()

    def format_to_markdown(self, events):
        """
        Format the events list to a simple flat markdown list with event name, location, link and source.
        No categorization by source or date.
        """
        if not events:
            return "# No events found"

        # Start building markdown
        markdown = "# Eventos en Asturias\n\n"
        markdown += f"_Actualizado: {datetime.datetime.now().strftime('%d/%m/%Y')}_\n\n"

        # Group events by date
        date_groups = {}
        month_long_events = []

        # Process each event
        for event in events:
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

            # Convert all-uppercase or partially uppercase titles to title case
            # Simpler approach: Convert all uppercase words to title case
            words = title.split()
            fixed_words = []

            # List of small words that should be lowercase unless they're the first word
            small_words = ['a', 'e', 'o', 'y', 'u', 'de', 'la', 'el', 'del', 'los', 'las', 'en', 'con', 'por',
                          'para', 'al', 'su', 'sus', 'tu', 'tus', 'mi', 'mis', 'un', 'una', 'unos', 'unas', 'lo', 'que']

            for i, word in enumerate(words):
                # Skip small common words and acronyms (2 chars or less)
                if word.isupper() and len(word) > 2:
                    word = word.capitalize()
                # Check if it's a lowercase common preposition/article and not the first word
                elif word.lower() in small_words and i > 0:
                    word = word.lower()
                # Capitalize first word
                elif i == 0 and not word.isupper():
                    word = word.capitalize()
                fixed_words.append(word)

            title = ' '.join(fixed_words)

            # Get source name and URL
            source_name = ""
            source_url = ""

            if 'source' in event and event['source']:
                source_name = event['source']
                # Determine source URL based on source name
                if source_name == 'Telecable':
                    source_url = 'https://blog.telecable.es/agenda-planes-asturias/'
                elif source_name == 'Turismo Asturias':
                    source_url = 'https://www.turismoasturias.es/agenda-de-asturias'
                elif source_name == 'Centros Sociales Oviedo':
                    source_url = 'https://www.oviedo.es/centrossociales/avisos'
                elif source_name == 'Visit Oviedo':
                    source_url = 'https://www.visitoviedo.info/agenda'
                elif source_name == 'Biodevas':
                    source_url = 'https://biodevas.org/'
                elif source_name == 'Avilés':
                    source_url = 'https://aviles.es/es/proximos-eventos'
            else:
                # Fallback to URL-based detection
                url = event['url']
                if 'blog.telecable.es' in url:
                    source_name = 'Telecable'
                    source_url = 'https://blog.telecable.es/agenda-planes-asturias/'
                elif 'turismoasturias.es' in url:
                    source_name = 'Turismo Asturias'
                    source_url = 'https://www.turismoasturias.es/agenda-de-asturias'
                elif 'oviedo.es/centrossociales' in url:
                    source_name = 'Centros Sociales Oviedo'
                    source_url = 'https://www.oviedo.es/centrossociales/avisos'
                elif 'visitoviedo.info' in url:
                    source_name = 'Visit Oviedo'
                    source_url = 'https://www.visitoviedo.info/agenda'
                elif 'biodevas.org' in url:
                    source_name = 'Biodevas'
                    source_url = 'https://biodevas.org/'
                elif 'aviles.es' in url:
                    source_name = 'Avilés'
                    source_url = 'https://aviles.es/es/proximos-eventos'
                else:
                    source_name = 'Otros eventos'
                    source_url = url

            # Clean date string - remove problematic strings and extra whitespace
            date_str = event['date']
            if date_str:
                # Clean up date string - remove "el dia", "h" markers and fix line breaks
                date_str = re.sub(r',\s*el\s+dia', '', date_str)
                date_str = re.sub(r',\s*h\s*-\s*\d+:\d+\s*h', '', date_str)
                date_str = re.sub(r'\s+h\s*$', '', date_str)
                # Remove excessive line breaks and whitespace
                date_str = re.sub(r'\s+', ' ', date_str).strip()

            # Extract time information if present
            time_str = None
            if date_str and re.search(r'a las \d+[:h]\d*', date_str):
                # Extract time part and remove it from date string
                time_match = re.search(r'a las (\d+[:h]\d*\w*)', date_str)
                if time_match:
                    time_str = time_match.group(1)
                    # Clean up time
                    time_str = re.sub(r'h$', ':00h', time_str)
                    if not re.search(r'h', time_str):
                        time_str += 'h'
                    date_str = re.sub(r'a las \d+[:h]\d*\w*', '', date_str).strip()

            # Create event dictionary for grouping
            event_info = {
                'title': title,
                'time': time_str,
                'location': event['location'] if event['location'] and event['location'].lower() != 'asturias' else '',
                'url': event['url'],
                'source_name': source_name,
                'source_url': source_url
            }

            # Group by date
            if "Todo el mes" in date_str or "Durante todo el mes" in date_str:
                month_long_events.append(event_info)
            else:
                if date_str not in date_groups:
                    date_groups[date_str] = []
                date_groups[date_str].append(event_info)

        # First add month-long events
        if month_long_events:
            markdown += "## Durante todo el mes\n\n"
            for event_info in month_long_events:
                # Format the event title
                markdown += f"- **{event_info['title']}**\n"

                # Add location if available
                if event_info['location']:
                    # Clean any multi-line locations before adding to markdown
                    location = self._clean_location(event_info['location'])
                    markdown += f"  - Lugar: {location}\n"

                # Add URL if available
                if event_info['url']:
                    markdown += f"  - Link: {event_info['url']}\n"

                # Add source reference with link
                markdown += f"  - Fuente: [{event_info['source_name']}]({event_info['source_url']})\n\n"

        # Sort dates
        sorted_dates = sorted(date_groups.keys(), key=lambda x: self.date_processor.date_sort_key(x))

        # Now add the rest of the events grouped by date
        for date_str in sorted_dates:
            markdown += f"## {date_str}\n\n"

            for event_info in date_groups[date_str]:
                # Format the event title with time if available
                if event_info['time']:
                    markdown += f"- **{event_info['time']}** - {event_info['title']}\n"
                else:
                    markdown += f"- **{event_info['title']}**\n"

                # Add location if available
                if event_info['location']:
                    # Clean any multi-line locations before adding to markdown
                    location = self._clean_location(event_info['location'])
                    markdown += f"  - Lugar: {location}\n"

                # Add URL if available
                if event_info['url']:
                    markdown += f"  - Link: {event_info['url']}\n"

                # Add source reference with link
                markdown += f"  - Fuente: [{event_info['source_name']}]({event_info['source_url']})\n\n"

        return markdown