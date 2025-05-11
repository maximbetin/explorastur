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

    def categorize_events(self, events):
        """
        Categorize events into different types based on keywords in title or description.
        """
        categories = {
            "Conciertos y festivales en Asturias": [],
            "Las mejores obras de teatro en Asturias": [],
            "Exposiciones en los museos asturianos": [],
            "Nos vamos de fiestas en Asturias": [],
            "Más agenda cultural de Asturias": []
        }

        # Expanded Spanish keywords for better categorization
        concert_keywords = [
            'concierto', 'música', 'música en vivo', 'cantante', 'banda', 'rock', 'pop', 'jazz',
            'festival de música', 'musical', 'ópera', 'orquesta', 'recital', 'canción', 'sonidos',
            'en directo', 'canciones', 'gira', 'álbum', 'artista', 'artistas', 'morgan', 'pecos',
            'perro', 'arizona baby', 'jp harris', 'santiago auserón', 'eddy smith', 'el nido',
            'eva mcbel', 'la habitación roja', 'charlie sexton', 'johnny garso', 'mägo de oz',
            'miguel póveda', 'paloma san basilio', 'acústicos'
        ]

        theater_keywords = [
            'teatro', 'obra', 'escena', 'actores', 'directo', 'espectáculo', 'drama', 'comedia',
            'danza', 'bailarines', 'personajes', 'escenas', 'obra de teatro', 'martha graham',
            'campoamor', 'jovellanos', 'niemeyer', 'berto romero', 'seis personajes', 'victoria',
            'saudade', 'la corte de faraón', 'los lunes al sol', 'blaubeeren', 'la desgracia',
            'querencia', 'palacio valdés', 'laboral', 'filarmónica'
        ]

        exhibition_keywords = [
            'exposición', 'museo', 'galería', 'arte', 'obras', 'pintores', 'pintora',
            'muestra', 'colección', 'exhibición', 'artistas', 'estaciones interiores',
            'artistas asturianos', 'bellas artes', 'evaristo valle', 'cmae'
        ]

        festival_keywords = [
            'festival', 'feria', 'fiesta', 'jornadas', 'celebración', 'gastronomía',
            'gastronómicas', 'sidra', 'arroz con leche', 'l.e.v', 'vibra mahou',
            'san isidro', 'llámpara', 'floración', 'trasona', 'cabranes', 'ascensión'
        ]

        for event in events:
            title = event.get('title', '').lower()
            desc = event.get('description', '').lower()
            location = event.get('location', '').lower()
            url = event.get('url', '').lower()
            combined_text = f"{title} {desc} {location} {url}"

            # Set default category
            category = "Más agenda cultural de Asturias"

            # Musical events first - most specific
            if "arizona baby" in combined_text or "jp harris" in combined_text or "eddy smith" in combined_text:
                category = "Conciertos y festivales en Asturias"
            elif any(keyword in combined_text for keyword in concert_keywords):
                category = "Conciertos y festivales en Asturias"
            # Theater and performances
            elif "victoria viene a cenar" in combined_text or "seis personajes" in combined_text:
                category = "Las mejores obras de teatro en Asturias"
            elif any(keyword in combined_text for keyword in theater_keywords):
                category = "Las mejores obras de teatro en Asturias"
            # Exhibitions
            elif "estaciones interiores" in combined_text or "nido-ritual" in combined_text:
                category = "Exposiciones en los museos asturianos"
            elif any(keyword in combined_text for keyword in exhibition_keywords):
                category = "Exposiciones en los museos asturianos"
            # Festivals and events
            elif "festival del arroz" in combined_text or "llámpara" in combined_text:
                category = "Nos vamos de fiestas en Asturias"
            elif any(keyword in combined_text for keyword in festival_keywords):
                category = "Nos vamos de fiestas en Asturias"

            categories[category].append(event)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def format_to_markdown(self, events):
        """
        Format the events list to a markdown file with all events in a single list.
        """
        if not events:
            return "# No events found"

        # Start building markdown
        markdown = "# Eventos en Asturias\n\n"
        markdown += f"_Actualizado: {datetime.datetime.now().strftime('%d/%m/%Y')}_\n\n"

        # Add source link as a header
        markdown += "## [Blog Telecable](https://blog.telecable.es/agenda-planes-asturias/)\n\n"

        # Skip categorization and sort all events by date
        events.sort(key=lambda x: self.date_processor.date_sort_key(x['date']))

        # Add all events in a single list
        for event in events:
            # Clean up the title - remove any quotes since we're adding them in the markdown
            title = event['title']
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            elif title.startswith('"'):
                title = title[1:]
            elif title.endswith('"'):
                title = title[:-1]

            # Date first, then event title
            markdown += f"**{event['date']}**: \"{title}\"\n"

            # Add location if available and not just "Asturias" - use "Lugar" in Spanish
            if event['location'] and event['location'].lower() != 'asturias':
                markdown += f"   - Lugar: {event['location']}\n"

            # Add URL if available
            if event['url']:
                markdown += f"   - Link: {event['url']}\n"

            markdown += "\n"

        return markdown