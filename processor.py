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
        Format the events list to a markdown file with events grouped by source.
        Events with the same date will be grouped together within each source.
        """
        if not events:
            return "# No events found"

        # Start building markdown
        markdown = "# Eventos en Asturias\n\n"
        markdown += f"_Actualizado: {datetime.datetime.now().strftime('%d/%m/%Y')}_\n\n"

        # Group events by their source URL
        events_by_source = {}
        for event in events:
            # Check if the event has a source field (added during scraping)
            if 'source' in event and event['source']:
                source = event['source']
            else:
                # Fallback to URL-based detection
                url = event['url']
                if 'blog.telecable.es' in url:
                    source = 'Telecable'
                elif 'turismoasturias.es' in url:
                    source = 'Turismo Asturias'
                elif 'oviedo.es/centrossociales' in url:
                    source = 'Centros Sociales Oviedo'
                elif 'visitoviedo.info' in url:
                    source = 'Visit Oviedo'
                else:
                    # If the URL doesn't match known patterns, check for other known URLs
                    if (url.startswith('https://www.museobbaa.com/') or
                        url.startswith('https://avilescomarca.info/') or
                        url.startswith('https://antonionajarro.com/') or
                        url.startswith('https://www.gijon.es/') or
                        url.startswith('https://www.instagram.com/') or
                        url.startswith('https://www.laboralciudaddelacultura.com/') or
                        url.startswith('https://evamcbel.com/') or
                        url.startswith('https://www.centroniemeyer.es/') or
                        url.startswith('https://www.facebook.com/') or
                        url.startswith('https://www.lahuellasonora.com/') or
                        url.startswith('https://evaristovalle.com/') or
                        url.startswith('https://elgranmusicaldelos80y90.com/')):
                        source = 'Telecable'
                    else:
                        source = 'Otros eventos'

            if source not in events_by_source:
                events_by_source[source] = []

            events_by_source[source].append(event)

        # Add source links as headers
        source_urls = {
            'Telecable': 'https://blog.telecable.es/agenda-planes-asturias/',
            'Turismo Asturias': 'https://www.turismoasturias.es/agenda-de-asturias',
            'Centros Sociales Oviedo': 'https://www.oviedo.es/centrossociales/avisos',
            'Visit Oviedo': 'https://www.visitoviedo.info/agenda',
            'Biodevas': 'https://biodevas.org',
            'Avilés': 'https://aviles.es/proximos-eventos'
        }

        # Sort sources to ensure consistent order
        for source in sorted(events_by_source.keys()):
            source_events = events_by_source[source]

            # Sort all events by date
            source_events.sort(key=lambda x: self.date_processor.date_sort_key(x['date']))

            # Add source heading and link
            if source in source_urls:
                markdown += f"## [{source}]({source_urls[source]})\n\n"
            else:
                markdown += f"## {source}\n\n"

            # Group events by date
            events_by_date = {}
            for event in source_events:
                date = event['date']
                if date not in events_by_date:
                    events_by_date[date] = []
                events_by_date[date].append(event)

            # Add events grouped by date for this source
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

                    # Add the event title
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