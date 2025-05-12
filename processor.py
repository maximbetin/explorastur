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

        Args:
            events (list): List of event dictionaries

        Returns:
            list: Filtered and processed events
        """
        if not events:
            return []

        # Current date to filter events
        current_date = datetime.datetime.now().day
        filtered_events = []

        for event in events:
            # Skip events with no title or date
            if not event.get('title') or not event.get('date'):
                continue

            # Skip non-events (like "Talleres" header sections)
            if self.text_processor.is_non_event(event['title']):
                continue

            # Check if the event is in the future
            if self.date_processor.is_future_event(event['date'], current_date):
                # Complete missing location information
                self._complete_location_info(event)
                filtered_events.append(event)

        # Sort events by date
        filtered_events.sort(
            key=lambda x: self.date_processor.date_sort_key(x['date'])
        )

        return filtered_events

    def _complete_location_info(self, event):
        """
        Complete missing location information in an event.

        Args:
            event (dict): Event dictionary to update
        """
        # Get location from title if missing
        if not event.get('location') and event.get('title'):
            event['location'] = self.text_processor.extract_location_from_title(event['title'])

        # For Centro Sociales events that lack full location info
        if event.get('source') == 'Centros Sociales Oviedo' and event.get('location'):
            self._fix_centro_social_location(event)

        # Clean up the location field
        if event.get('location'):
            event['location'] = self._clean_location(event['location'])

    def _fix_centro_social_location(self, event):
        """
        Fix incomplete Centro Social location information.

        Args:
            event (dict): Event dictionary to update
        """
        location = event['location']

        # Map of partial locations to full locations
        location_map = {
            'Plaza': 'Plaza de Asturias, Oviedo',
            'Centro Social El': 'Centro Social El Cortijo, Oviedo',
            'Centro Social Bra': 'Centro Social Braulio, Oviedo',
            'Centro Social': 'Centro Social de Oviedo',
            'Social': 'Centro Social de Oviedo'
        }

        # Apply direct mappings
        if location in location_map:
            event['location'] = location_map[location]
        # Add Oviedo to Centro Social locations without full name
        elif 'Centro Social' in location and len(location) < 25 and 'Oviedo' not in location:
            event['location'] = f"{location.strip()}, Oviedo"

    def _clean_location(self, location):
        """
        Clean up location text to extract just the venue and city.

        Args:
            location (str): Raw location text

        Returns:
            str: Cleaned location text
        """
        if not location:
            return ""

        # Replace line breaks with spaces
        location = re.sub(r'[\r\n]+', ' ', location)

        # Fix formatting issues
        location = self._fix_formatting_issues(location)

        # Handle specific location patterns
        location = self._handle_specific_locations(location)

        # Clean up excessive commas and spacing in addresses
        location = re.sub(r',\s*,', ',', location)
        location = re.sub(r'\s+', ' ', location)

        # Extract venue and city or truncate if too long
        location = self._extract_venue_and_city(location)

        return location.strip()

    def _fix_formatting_issues(self, location):
        """
        Fix common formatting issues in location text.

        Args:
            location (str): Location text to fix

        Returns:
            str: Location with fixed formatting
        """
        # Fix concatenated words
        location = re.sub(r'([a-z])([A-Z])', r'\1 \2', location)

        # Fix missing spaces after punctuation
        location = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', location)
        location = re.sub(r'([a-zA-Z]),([A-Z])', r'\1, \2', location)
        location = re.sub(r'([a-zA-Z])"([a-zA-Z])', r'\1" \2', location)

        # Fix specific concatenation issues
        prefixes = ['la', 'el', 'de', 'del', 'un']
        for prefix in prefixes:
            location = re.sub(fr'{prefix}([A-Z])', fr'{prefix} \1', location)

        # Remove common Spanish prefixes
        location = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', location)
        location = re.sub(r'^en\s+', '', location)

        # Fix special case patterns
        location = re.sub(r'el día$', '', location)
        location = re.sub(r'con la banda.*$', '', location)
        location = re.sub(r'para presentar.*$', '', location)

        # Fix "Dr," which should be "Dr." in addresses
        location = re.sub(r'Dr,', 'Dr.', location)

        # Fix Address format issues
        location = re.sub(r'C/ ([^,]+), ([^,]+), ([^,]+)$', r'C/ \1, \2, \3', location)

        return location

    def _handle_specific_locations(self, location):
        """
        Handle specific location patterns.

        Args:
            location (str): Location text

        Returns:
            str: Handled location text
        """
        # Map of specific location patterns to their standardized forms
        specific_locations = {
            "El Atrio": "Centro Comercial 'El Atrio' (C/ Cámara, Cuba, Dr.), Avilés" if "Cuba" in location else location,
            "La Florida con": "Centro Social La Florida, Oviedo",
            "Factoría Cultural": "Factoría Cultural, Avilés",
            "NIEMEYER": "Centro Niemeyer, Avilés"
        }

        # Check for specific location patterns
        for pattern, replacement in specific_locations.items():
            if pattern in location:
                return replacement

        # Handle truncated locations
        if location.strip() == 'Plaza':
            return 'Plaza de Asturias, Oviedo'
        if location.strip() == 'Centro Social':
            return 'Centro Social de Oviedo'
        if 'Centro Social' in location and len(location.strip()) < 20:
            return f"{location}, Oviedo"

        return location

    def _extract_venue_and_city(self, location):
        """
        Extract venue and city from location or truncate if too long.

        Args:
            location (str): Location text

        Returns:
            str: Extracted venue and city or truncated location
        """
        # If location is too long, try to extract just the venue name
        if len(location) > 80:
            # Try to extract just the venue name by looking for common patterns
            venue_keywords = ['Teatro', 'Auditorio', 'Centro', 'Sala', 'Pabellón',
                              'Plaza', 'Factoría', 'Museo', 'Arena']
            venue_pattern = r'^([^,.]+(?:' + '|'.join(venue_keywords) + r')[^,.]{0,30})'
            venue_match = re.match(venue_pattern, location)

            if venue_match:
                location = venue_match.group(1).strip()

            # If still too long, truncate and add ellipsis
            if len(location) > 80:
                location = location[:77] + '...'

        # Extract venue and city when possible using more flexible patterns
        venue_keywords_str = '|'.join(['Teatro', 'Auditorio', 'Centro', 'Sala', 'Pabellón',
                                      'Plaza', 'Factoría', 'Museo', 'Arena'])
        venue_city_pattern = fr'([^,.]+(?:{venue_keywords_str})[^,.]+)(?:de|en)\s+([^,.]+)'

        match = re.search(venue_city_pattern, location)
        if match:
            venue = match.group(1).strip()
            city = match.group(2).strip()
            # Remove any trailing dates or times
            city = re.sub(r'\d+\s+de\s+\w+$', '', city).strip()
            city = re.sub(r'el\s+\w+\s+\d+$', '', city).strip()
            return f"{venue} ({city})"

        # If the pattern didn't match but there's a venue keyword, clean it up
        for keyword in ['Teatro', 'Auditorio', 'Centro', 'Sala', 'Pabellón',
                        'Plaza', 'Factoría', 'Museo', 'Recinto']:
            if keyword in location:
                # Just clean up the location without trying to separate venue/city
                location = re.sub(r'\d+\s+de\s+\w+', '', location).strip()
                location = re.sub(r'el\s+\w+\s+\d+', '', location).strip()
                return location

        return location

    def format_to_markdown(self, events):
        """
        Format the events list to a simple flat markdown list with event name, location, link and source.
        No categorization by source or date.

        Args:
            events (list): List of event dictionaries

        Returns:
            str: Markdown formatted text
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
            # Clean and format event data
            event_info = self._prepare_event_for_markdown(event)

            # Group by date
            date_str = event['date']
            if "Todo el mes" in date_str or "Durante todo el mes" in date_str:
                month_long_events.append(event_info)
            else:
                if date_str not in date_groups:
                    date_groups[date_str] = []
                date_groups[date_str].append(event_info)

        # First add month-long events
        if month_long_events:
            markdown += self._format_event_group("Durante todo el mes", month_long_events)

        # Sort dates
        sorted_dates = sorted(date_groups.keys(),
                             key=lambda x: self.date_processor.date_sort_key(x))

        # Now add the rest of the events grouped by date
        for date_str in sorted_dates:
            markdown += self._format_event_group(date_str, date_groups[date_str])

        return markdown

    def _prepare_event_for_markdown(self, event):
        """
        Prepare event data for markdown formatting.

        Args:
            event (dict): Raw event data

        Returns:
            dict: Prepared event info for markdown
        """
        # Clean up the title - remove any quotes
        title = event['title']
        title = self._clean_title(title)

        # Get source name and URL
        source_name, source_url = self._get_source_info(event)

        # Extract time information if present
        date_str, time_str = self._extract_time_info(event['date'])

        # Create event dictionary for grouping
        return {
            'title': title,
            'time': time_str,
            'location': event.get('location', '') if event.get('location', '').lower() != 'asturias' else '',
            'url': event.get('url', ''),
            'source_name': source_name,
            'source_url': source_url
        }

    def _clean_title(self, title):
        """
        Clean up event title by removing quotes and fixing capitalization.

        Args:
            title (str): Raw title text

        Returns:
            str: Cleaned title
        """
        # Remove quotes
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        elif title.startswith('"'):
            title = title[1:]
        elif title.endswith('"'):
            title = title[:-1]
        # Remove any remaining quotes anywhere in the title
        title = title.replace('"', '')

        # Convert all-uppercase or partially uppercase titles to title case
        words = title.split()
        fixed_words = []

        # List of small words that should be lowercase unless they're the first word
        small_words = ['a', 'e', 'o', 'y', 'u', 'de', 'la', 'el', 'del', 'los', 'las',
                      'en', 'con', 'por', 'para', 'al', 'su', 'sus', 'tu', 'tus',
                      'mi', 'mis', 'un', 'una', 'unos', 'unas', 'lo', 'que']

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

        return ' '.join(fixed_words)

    def _get_source_info(self, event):
        """
        Get source name and URL from event.

        Args:
            event (dict): Event data

        Returns:
            tuple: (source_name, source_url)
        """
        # Source URL mapping
        source_urls = {
            'Telecable': 'https://blog.telecable.es/agenda-planes-asturias/',
            'Turismo Asturias': 'https://www.turismoasturias.es/agenda-de-asturias',
            'Centros Sociales Oviedo': 'https://www.oviedo.es/centrossociales/avisos',
            'Visit Oviedo': 'https://www.visitoviedo.info/agenda',
            'Biodevas': 'https://biodevas.org/',
            'Avilés': 'https://aviles.es/es/proximos-eventos'
        }

        # Try to get source from event data
        if event.get('source'):
            source_name = event['source']
            return source_name, source_urls.get(source_name, event.get('url', ''))

        # Fallback to URL-based detection
        url = event.get('url', '')
        url_patterns = {
            'blog.telecable.es': ('Telecable', source_urls['Telecable']),
            'turismoasturias.es': ('Turismo Asturias', source_urls['Turismo Asturias']),
            'oviedo.es/centrossociales': ('Centros Sociales Oviedo', source_urls['Centros Sociales Oviedo']),
            'visitoviedo.info': ('Visit Oviedo', source_urls['Visit Oviedo']),
            'biodevas.org': ('Biodevas', source_urls['Biodevas']),
            'aviles.es': ('Avilés', source_urls['Avilés'])
        }

        for pattern, (name, source_url) in url_patterns.items():
            if pattern in url:
                return name, source_url

        return 'Otros eventos', url

    def _extract_time_info(self, date_str):
        """
        Extract time information from date string.

        Args:
            date_str (str): Date string that may contain time

        Returns:
            tuple: (cleaned_date_str, time_str)
        """
        if not date_str:
            return date_str, None

        # Clean up date string - remove problematic strings and extra whitespace
        date_str = re.sub(r',\s*el\s+dia', '', date_str)
        date_str = re.sub(r',\s*h\s*-\s*\d+:\d+\s*h', '', date_str)
        date_str = re.sub(r'\s+h\s*$', '', date_str)
        # Remove excessive line breaks and whitespace
        date_str = re.sub(r'\s+', ' ', date_str).strip()

        # Extract time information if present
        time_str = None
        if re.search(r'a las \d+[:h]\d*', date_str):
            # Extract time part and remove it from date string
            time_match = re.search(r'a las (\d+[:h]\d*\w*)', date_str)
            if time_match:
                time_str = time_match.group(1)
                # Clean up time
                time_str = re.sub(r'h$', ':00h', time_str)
                if not re.search(r'h', time_str):
                    time_str += 'h'
                date_str = re.sub(r'a las \d+[:h]\d*\w*', '', date_str).strip()

        return date_str, time_str

    def _format_event_group(self, group_title, events):
        """
        Format a group of events for markdown.

        Args:
            group_title (str): Title for the group
            events (list): List of events in the group

        Returns:
            str: Markdown formatted text for the group
        """
        markdown = f"## {group_title}\n\n"

        for event_info in events:
            # Format the event title with time if available
            if event_info['time']:
                markdown += f"- **{event_info['time']}** - {event_info['title']}\n"
            else:
                markdown += f"- **{event_info['title']}**\n"

            # Add location if available
            if event_info['location']:
                markdown += f"  - Lugar: {event_info['location']}\n"

            # Add URL if available
            if event_info['url']:
                markdown += f"  - Link: {event_info['url']}\n"

            # Add source reference with link
            markdown += f"  - Fuente: [{event_info['source_name']}]({event_info['source_url']})\n\n"

        return markdown