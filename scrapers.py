"""
Web scrapers for events in Asturias.
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from utils import DateProcessor, TextProcessor
import datetime

logger = logging.getLogger('explorastur')

class EventScraper:
    """Base class for event scrapers."""

    def __init__(self):
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()

    def scrape(self):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement scrape method")

    def _create_event(self, title, date, location, description, url):
        """Create a standardized event dictionary."""
        # Ensure title isn't empty
        if not title or title == ":":
            title = ""  # Let the processor handle empty titles

        return {
            'title': title,
            'date': date,
            'location': location,
            'description': description,
            'url': url
        }

class TelecableScraper(EventScraper):
    """Scraper for Telecable blog."""

    def __init__(self):
        super().__init__()
        self.url = "https://blog.telecable.es/agenda-planes-asturias/"
        self.current_month_year = self.date_processor.get_current_month_year()

    def scrape(self):
        """Scrape events from Blog Telecable Asturias directly from HTML structure."""
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"Error fetching {self.url}: {e}")
            return []

        # Parse HTML
        try:
            soup = BeautifulSoup(html, 'html.parser')
            article_body = soup.select_one('div.article-body')
            if not article_body:
                logger.error("Could not find article body")
                return []
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

        logger.info("Using Telecable parser")

        # Extract each category section from the HTML
        sections = self._extract_category_sections(article_body)

        # Process each section to extract events
        for category, section_content in sections.items():
            section_events = self._extract_events_from_section(section_content, category)
            events.extend(section_events)

        logger.info(f"Successfully extracted {len(events)} events")
        return events

    def _extract_category_sections(self, article_body):
        """Extract content by category section from the HTML."""
        sections = {}

        # Map Spanish section titles to our categories (but preserve original names)
        section_map = {
            "Conciertos y festivales en Asturias": "Conciertos y festivales en Asturias",
            "Las mejores obras de teatro en Asturias": "Las mejores obras de teatro en Asturias",
            "Exposiciones en los museos asturianos": "Exposiciones en los museos asturianos",
            "Nos vamos de fiestas en mayo en Asturias": "Nos vamos de fiestas en Asturias",
            "Más agenda cultural de Asturias en mayo": "Más agenda cultural de Asturias"
        }

        # Initialize sections with Spanish names from the page
        for spanish_name in section_map.values():
            sections[spanish_name] = []

        # Get all h2 headers which serve as category separators
        headers = article_body.find_all('h2')

        # Extract content for each section
        current_section = None
        current_content = []

        for element in article_body.children:
            # If we find a header, it means a new section starts
            if element.name == 'h2':
                # Store the previous section content if we were tracking one
                if current_section and current_section in section_map:
                    sections[section_map[current_section]].extend(current_content)

                # Start a new section
                header_text = element.get_text().strip()
                current_section = header_text
                current_content = []
            # Add content to the current section
            elif current_section:
                if element.name in ['p', 'figure']:
                    current_content.append(element)

        # Add the last section
        if current_section and current_section in section_map:
            sections[section_map[current_section]].extend(current_content)

        # Remove empty sections
        return {k: v for k, v in sections.items() if v}

    def _extract_events_from_section(self, section_content, category):
        """Extract individual events from a section's content."""
        events = []

        # Group content by event - each event starts with a <p> containing a bold title
        current_event = None
        event_details = []

        for element in section_content:
            if element.name == 'p' and element.find('b'):
                # If we were tracking an event, save it before starting a new one
                if current_event and event_details:
                    event = self._parse_event(current_event, event_details, category)
                    if event:
                        events.append(event)

                # Start a new event
                current_event = element.find('b').get_text().strip()
                event_details = [element]
            elif current_event:
                event_details.append(element)

        # Don't forget the last event
        if current_event and event_details:
            event = self._parse_event(current_event, event_details, category)
            if event:
                events.append(event)

        return events

    def _parse_event(self, title, details, category):
        """Parse event information from the title and details."""
        # Get current month and year to handle relative dates
        current_month = self.date_processor.get_current_month_name().lower()
        current_year = datetime.datetime.now().year

        # Extract title - remove date prefix if present
        clean_title = re.sub(r'^[\d\s\w\-]+(de \w+|\w+):\s*', '', title).strip()

        # Extract date from title - handle any month, not just mayo
        date_match = re.search(r'([\d\s\w\-]+(?:de \w+|\w+ \d{4}))', title)

        # Default date fallback uses current month/year
        date = date_match.group(1).strip() if date_match else f"{current_month.capitalize()} {current_year}"

        # For "todo el mes" or "Durante todo el mes" cases, add current month
        if "todo el mes" in title.lower() and not re.search(r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b', title.lower()):
            date = f"Durante todo el mes de {current_month}"

        # Extract link from the paragraph following the title
        url = ""
        location = ""

        # Common venue keywords to look for
        venue_keywords = [
            "Teatro", "Auditorio", "Sala", "Centro", "Museo",
            "Plaza", "Pabellón", "Recinto", "Factoría"
        ]

        # Known venue mappings for common events - these should be stable regardless of month/year
        venue_mappings = {
            "artistas asturianos": "Casa Municipal de Cultura de Avilés",
            "nido-ritual": "Centro Municipal de Arte y Exposiciones (CMAE) de Avilés",
            "estaciones interiores": "Museo de Bellas Artes de Asturias (Oviedo)",
            "la corte de faraón": "Teatro Campoamor de Oviedo",
            "santiago auserón": "Teatro de la Laboral de Gijón",
            "gran musical": "Gijón Arena - Plaza de Toros El Bibio",
            "vibra mahou fest": "Recinto Ferial Luis Adaro, Gijón",
            "querencia": "Teatro Palacio Valdés de Avilés",
            "berto romero": "Teatro de la Laboral de Gijón",
            "seis personajes": "Centro Niemeyer de Avilés",
            "los lunes al sol": "Teatro Jovellanos de Gijón",
            "pintores gijoneses": "Fundación Museo Evaristo Valle, Gijón",
            "pecos": "Pabellón de Exposiciones de La Magdalena de Avilés",
            "perro": "La Salvaje de Oviedo",
            "morgan": "Teatro de la Laboral de Gijón",
            "mägo de oz": "Gijón Arena - Plaza de Toros El Bibio",
            "miguel póveda": "Auditorio Príncipe Felipe de Oviedo",
            "paloma san basilio": "Teatro Jovellanos de Gijón",
            "jp harris": "Factoría Cultural de Avilés",
            "eddy smith": "Factoría Cultural de Avilés",
            "eva mcbel": "Sala Galaxy Gong de Oviedo",
            "el nido": "Sala Tribeca de Oviedo",
            "arizona baby": "Sala Santa Cecilia de Avilés",
            "martha graham": "Teatro Campoamor de Oviedo",
            "victoria viene": "Centro Niemeyer de Avilés",
            "saudade": "Teatro Jovellanos de Gijón"
        }

        # Check if we have a known venue based on the title
        clean_title_lower = clean_title.lower()
        for keyword, venue in venue_mappings.items():
            if keyword.lower() in clean_title_lower:
                location = venue
                break

        # Extract URL and location if not already found
        for detail in details:
            if detail.name == 'p' and detail.find('a'):
                link_element = detail.find('a')

                # Only extract URL if it's a proper link and not the blog itself
                link_href = link_element.get('href', '')
                if link_href and link_href.startswith('http') and 'blog.telecable.es' not in link_href:
                    url = link_href

                # Extract text from paragraph for location if needed
                if not location:
                    detail_text = detail.get_text()

                    # Try to find venue keywords in the text
                    venue_found = False
                    for venue in venue_keywords:
                        venue_match = re.search(f"{venue}\\s+[\\w\\s\\.,]+", detail_text, re.IGNORECASE)
                        if venue_match:
                            location = venue_match.group(0).strip()
                            venue_found = True
                            break

                    # If no venue keyword found, try common patterns
                    if not venue_found:
                        loc_patterns = [
                            r'en\s+(?:el|la)?\s+([\w\s\.\-]+)(?:de|en)\s+([\w\s]+)',
                            r'(?:el|la|los|las)\s+([\w\s\.]+)(?:de|en)\s+([\w\s\.\-]+)',
                            r'en\s+([\w\s\.\-]+)'
                        ]

                        for pattern in loc_patterns:
                            loc_match = re.search(pattern, detail_text)
                            if loc_match:
                                location = loc_match.group(0).strip()
                                # Remove "en el" or "en la" prefixes
                                location = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', location)
                                location = re.sub(r'^en\s+', '', location)
                                break

        # Create event with extracted info
        if clean_title:
            return self._create_event(
                title=clean_title,
                date=date,
                location=location,
                description="",  # No description as requested
                url=url
            )

        return None