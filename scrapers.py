"""
Web scrapers for events in Asturias.
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from utils import DateProcessor, TextProcessor
import datetime
from bs4.element import Tag
import json
from typing import Dict, List, Optional, Any, Union, Callable
from scraper_utils import fetch_page, parse_html, extract_text, extract_attribute, make_absolute_url

logger = logging.getLogger('explorastur')

class EventScraper:
    """Base class for event scrapers.

    Provides common functionality for all event scrapers and defines
    the interface that subclasses must implement.
    """

    def __init__(self):
        """Initialize the event scraper with common utilities."""
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()
        self.source_name = "Generic"

    def scrape(self) -> List[Dict[str, str]]:
        """Scrape events from the source.

        This method should be implemented by subclasses to scrape events
        from a specific source.

        Returns:
            List of event dictionaries
        """
        raise NotImplementedError("Subclasses must implement scrape method")

    def fetch_and_parse(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL and parse its HTML content.

        Args:
            url: The URL to fetch

        Returns:
            BeautifulSoup object or None if request or parsing failed
        """
        html = fetch_page(url)
        if html:
            return parse_html(html)
        return None

    def create_event(self, title: str, date: str, location: str, url: str,
                    description: str = "", source: Optional[str] = None) -> Dict[str, str]:
        """Create a standardized event dictionary.

        Args:
            title: Event title
            date: Event date
            location: Event location
            url: Event URL
            description: Event description (optional)
            source: Source name (optional)

        Returns:
            Event dictionary with standardized format
        """
        # Use source name from the class if not provided
        if not source:
            source = self.source_name

        # Ensure title isn't empty
        if not title or title == ":":
            title = ""  # Let the processor handle empty titles

        # Standardize the date format for all events
        date = self._standardize_date_format(date)

        return {
            'title': title,
            'date': date,
            'location': location,
            'description': description,
            'url': url,
            'source': source
        }

    def _standardize_date_format(self, date_str: str) -> str:
        """Standardize date format across all scrapers.

        Args:
            date_str: Date string to standardize

        Returns:
            Standardized date string
        """
        if not date_str:
            return date_str

        # Remove day of week prefix if present (e.g., "lunes 12 de mayo" → "12 de mayo")
        date_str = re.sub(r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+', '', date_str.strip())

        # Remove leading zeros in day numbers (e.g., "01 mayo" → "1 mayo")
        date_str = re.sub(r'\b0(\d)(\s+de|\s*[-\/])', r'\1\2', date_str)

        # Remove year suffixes for current year (e.g., "12 mayo 2025" → "12 mayo")
        current_year = datetime.datetime.now().year
        date_str = re.sub(f'\\s+{current_year}\\b', '', date_str)

        return date_str.strip()

    def process_pagination(self, base_url: str, start_url: str,
                          max_pages: int = 3,
                          extract_page_events: Optional[Callable[[BeautifulSoup], List[Dict[str, str]]]] = None,
                          next_page_selector: Optional[str] = None) -> List[Dict[str, str]]:
        """Process pagination for a website.

        Args:
            base_url: Base URL of the website
            start_url: Starting URL for pagination
            max_pages: Maximum number of pages to process
            extract_page_events: Function to extract events from a page
            next_page_selector: CSS selector for next page link

        Returns:
            List of event dictionaries from all pages
        """
        if not extract_page_events:
            raise ValueError("extract_page_events function must be provided")

        all_events = []
        current_page = 1
        current_url = start_url

        while current_page <= max_pages:
            logger.info(f"Fetching page {current_page}: {current_url}")

            try:
                soup = self.fetch_and_parse(current_url)
                if not soup:
                    break

                # Extract events from the current page
                page_events = extract_page_events(soup)
                all_events.extend(page_events)

                logger.info(f"Extracted {len(page_events)} events from page {current_page}")

                # If no next page selector provided, stop after first page
                if not next_page_selector:
                    break

                # Find the next page link
                next_link = soup.select_one(next_page_selector)
                if not next_link:
                    logger.info("No next page link found")
                    break

                # Check if next link is disabled
                classes = next_link.get('class', [])
                if classes and 'disabled' in classes:
                    logger.info("Next page link is disabled")
                    break

                # Get the URL for the next page
                next_url = next_link.get('href', '')
                if not next_url:
                    logger.info("No next page URL found")
                    break

                # Make the URL absolute if it's relative
                if isinstance(next_url, list):
                    next_url = next_url[0] if next_url else ""
                current_url = make_absolute_url(base_url, next_url)
                current_page += 1

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                break

        return all_events

class TelecableScraper(EventScraper):
    """Scraper for Telecable blog."""

    def __init__(self):
        super().__init__()
        self.url = "https://blog.telecable.es/agenda-planes-asturias/"
        self.current_month_year = self.date_processor.get_current_month_year()
        self.source_name = "Telecable"

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
        date = date_match.group(1).strip() if date_match else f"{current_month.capitalize()}"

        # For "todo el mes" or "Durante todo el mes" cases, add current month
        if "todo el mes" in title.lower() and not re.search(r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b', title.lower()):
            date = f"Durante todo el mes de {current_month}"

        # Clean up the date is now handled by the base class _standardize_date_format method
        # when creating the event

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
            return self.create_event(
                title=clean_title,
                date=date,
                location=location,
                description="",  # No description as requested
                url=url,
                source="Telecable"
            )

        return None

    def _clean_date_format(self, date_text):
        """Clean date text to remove leading zeros and year."""
        if not date_text:
            return date_text

        # Remove year patterns (e.g., "2025", " 2025")
        date_text = re.sub(r'\s*\d{4}', '', date_text)

        # Replace leading zeros in day numbers
        # Match patterns like "01 de mayo", "02-03 de mayo", etc.
        date_text = re.sub(r'\b0(\d)(\s+de|\s*[-\/])', r'\1\2', date_text)

        return date_text.strip()

class TurismoAsturiaScraper(EventScraper):
    """Scraper for Turismo Asturias events page."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.turismoasturias.es"
        self.url = f"{self.base_url}/agenda-de-asturias"
        self.max_pages = 3  # Maximum number of pages to scrape to avoid excessive requests
        self.source_name = "Turismo Asturias"

    def scrape(self):
        """Scrape events from Turismo Asturias website with pagination support."""
        logger.info(f"Starting pagination scrape of Turismo Asturias (max {self.max_pages} pages)")

        # Define page builder for pagination
        def get_page_url(page_num):
            if page_num == 1:
                return self.url
            else:
                return (f"{self.url}?p_p_id=as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_JXvXAPSD7JC0"
                       f"&p_p_lifecycle=0"
                       f"&_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_JXvXAPSD7JC0_calendarPath=%2Fhtml%2Fsuite%2Fdisplays%2Flist.jsp"
                       f"&p_r_p_startDate=&p_r_p_endDate=&p_r_p_searchText=&p_r_p_categoryId=0&p_r_p_categoryIds="
                       f"&_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_JXvXAPSD7JC0_calendarId=0"
                       f"&p_r_p_tag=&p_r_p_time="
                       f"&_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_JXvXAPSD7JC0_delta=12"
                       f"&_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_JXvXAPSD7JC0_cur={page_num}")

        # Define function to extract events from each page
        def extract_events_from_page(soup):
            event_cards = soup.select('div.card[itemscope][itemtype="http://schema.org/Event"]')
            if not event_cards:
                logger.warning("No event cards found on this page")
                return []

            logger.info(f"Found {len(event_cards)} event cards")

            # Process each event card
            page_events = []
            for card in event_cards:
                try:
                    event = self._extract_event_from_card(card)
                    if event:
                        page_events.append(event)
                except Exception as e:
                    logger.error(f"Error processing event card: {e}")
                    continue

            return page_events

        # Process first page
        events = []

        # Start with first page
        soup = self.fetch_and_parse(self.url)
        if not soup:
            return events

        # Extract events from first page
        first_page_events = extract_events_from_page(soup)
        events.extend(first_page_events)

        # Check if there's pagination
        pagination = soup.select_one('nav.pagination')
        if not pagination:
            logger.info("No pagination found, this is the only page")
            return events

        # Check if there are more pages
        pagination_info = soup.select_one('small.search-results')
        if pagination_info:
            info_text = pagination_info.get_text().strip()
            # Extract total results count if available
            # Search for pattern like "Mostrando el intervalo 1 - 12 de 16 resultados."
            total_match = re.search(r'de\s+(\d+)\s+resultados', info_text, re.IGNORECASE)
            if total_match:
                total_results = int(total_match.group(1))
                results_per_page = 12  # Default results per page
                total_pages = (total_results + results_per_page - 1) // results_per_page
                logger.info(f"Found pagination info: {total_results} total results across {total_pages} pages")

                # Process remaining pages if any
                for page_num in range(2, min(total_pages + 1, self.max_pages + 1)):
                    page_url = get_page_url(page_num)
                    page_soup = self.fetch_and_parse(page_url)
                    if page_soup:
                        page_events = extract_events_from_page(page_soup)
                        events.extend(page_events)
                        logger.info(f"Extracted {len(page_events)} events from page {page_num}")

        logger.info(f"Pagination complete. Scraped {len(events)} total events")
        return events

    def _extract_event_from_card(self, card):
        """Extract event details from a card element."""
        # Extract title
        title_elem = card.select_one('span[itemprop="name"]')
        title = title_elem.get_text().strip() if title_elem else ""

        if not title:
            return None

        # Extract URL
        url_elem = card.select_one('a[itemprop="url"]')
        url = url_elem.get('href', '') if url_elem else ""

        # Make URL absolute if it's relative
        if url and not url.startswith('http'):
            url = f"{self.base_url}{url}" if url.startswith('/') else f"{self.base_url}/{url}"

        # Extract location
        location_elem = card.select_one('span[itemprop="address"]')
        location = location_elem.get_text().strip() if location_elem else ""

        # Extract dates (start and end if available)
        start_date_elem = card.select_one('span[itemprop="startDate"]')
        end_date_elem = card.select_one('span[itemprop="endDate"]')

        start_date_str = ""
        end_date_str = ""

        if start_date_elem:
            start_date_attr = start_date_elem.get('date', '')
            if start_date_attr:
                try:
                    # Parse ISO format date
                    date_obj = datetime.datetime.strptime(start_date_attr.split()[0], '%Y-%m-%d')
                    # Format without leading zeros and without year
                    start_date_str = f"{int(date_obj.day)} {self._get_spanish_month(date_obj.month)}"
                except Exception as e:
                    logger.warning(f"Error parsing start date: {e}")
                    # Fallback to text inside span
                    start_date_str = card.select_one('.date:not(.hide) span:nth-of-type(2)').get_text().strip() if card.select_one('.date:not(.hide) span:nth-of-type(2)') else ""
                    # Try to clean up the fallback date text
                    start_date_str = self._clean_date_text(start_date_str)

        if end_date_elem:
            end_date_attr = end_date_elem.get('date', '')
            if end_date_attr:
                try:
                    # Parse ISO format date
                    date_obj = datetime.datetime.strptime(end_date_attr.split()[0], '%Y-%m-%d')
                    # Format without leading zeros and without year
                    end_date_str = f"{int(date_obj.day)} {self._get_spanish_month(date_obj.month)}"
                except Exception as e:
                    logger.warning(f"Error parsing end date: {e}")
                    # Fallback to text inside span
                    end_date_str = card.select_one('.date:not(.hide) span:nth-of-type(4)').get_text().strip() if card.select_one('.date:not(.hide) span:nth-of-type(4)') else ""
                    # Try to clean up the fallback date text
                    end_date_str = self._clean_date_text(end_date_str)

        # Format the date string
        if start_date_str and end_date_str:
            date = f"{start_date_str} - {end_date_str}"
        elif start_date_str:
            date = start_date_str
        else:
            # Fallback: try to get the visible date text
            date_elem = card.select_one('.date')
            date = date_elem.get_text().strip() if date_elem else ""
            # Clean up the date text
            date = re.sub(r'Tiempo\s*', '', date).strip()
            date = self._clean_date_text(date)

        # Extract description
        description_elem = card.select_one('.card-hover')
        description = ""  # No longer extracting descriptions

        # Create and return the event
        return self.create_event(title, date, location, description, url, source="Turismo Asturias")

    def _get_spanish_month(self, month_num):
        """Get Spanish month name from month number (1-12)"""
        spanish_months = [
            'enero', 'febrero', 'marzo', 'abril',
            'mayo', 'junio', 'julio', 'agosto',
            'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        return spanish_months[month_num - 1]

    def _clean_date_text(self, date_text):
        """Clean up date text to remove leading zeros and year"""
        if not date_text:
            return date_text

        # Try to remove year (typically "2025" or similar)
        date_text = re.sub(r'\s+20\d\d', '', date_text)

        # Try to remove leading zeros in day numbers
        date_text = re.sub(r'\b0(\d)\b', r'\1', date_text)

        return date_text.strip()

class OviedoCentrosSocialesScraper(EventScraper):
    """Scraper for Oviedo's social centers (Centros Sociales)."""

    def __init__(self):
        super().__init__()
        self.url = "https://www.oviedo.es/centrossociales/avisos"
        self.source_name = "Centros Sociales Oviedo"

    def scrape(self):
        """Scrape events from Oviedo's Centros Sociales website."""
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

            # Find agendas and other events
            agenda_headers = soup.select('div.taglib-header h3.header-title span')

            for header in agenda_headers:
                header_text = header.get_text().strip()

                # Find the content associated with this header
                header_parent = header.find_parent('div', class_='taglib-header')
                if not header_parent:
                    continue

                # Get the next asset-full-content section
                content_section = header_parent.find_next_sibling('div', class_='asset-full-content')
                if not content_section:
                    continue

                # Get the text content that contains the events
                if isinstance(content_section, (BeautifulSoup, Tag)):
                    text_div = content_section.select_one('div.text')
                else:
                    text_div = None
                if not text_div:
                    continue

                # Extract events based on the header type
                if "Agenda Centros Sociales" in header_text:
                    # Process an agenda which contains multiple events
                    agenda_events = self._extract_agenda_events(text_div, header_text)
                    events.extend(agenda_events)
                else:
                    # Process a single event/announcement
                    event = self._extract_single_event(text_div, header_text)
                    if event:
                        events.append(event)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

        logger.info(f"Successfully extracted {len(events)} events from Oviedo Centros Sociales")
        return events

    def _extract_agenda_events(self, text_div, header_text):
        """Extract multiple events from an agenda section."""
        events = []

        # Try to extract date range from header
        date_range = self._extract_date_range(header_text)

        # Find all event sections - each starts with a <p><strong> element
        event_sections = []
        current_section = {"title": "", "details": []}

        for element in text_div.find_all(['p', 'ul']):
            # If we find a title (in a <p><strong> element)
            if element.name == 'p' and element.find('strong'):
                # Save previous section if it exists
                if current_section["title"]:
                    event_sections.append(current_section)

                # Start a new section
                current_section = {
                    "title": element.get_text().strip(),
                    "details": []
                }
            # Add details to current section
            elif current_section["title"]:
                current_section["details"].append(element)

        # Don't forget the last section
        if current_section["title"]:
            event_sections.append(current_section)

        # Process each event section
        for section in event_sections:
            # Skip empty sections
            if not section["title"] or not section["details"]:
                continue

            # Extract individual events
            extracted_events = self._parse_event_section(section["title"], section["details"], date_range)
            events.extend(extracted_events)

        return events

    def _extract_single_event(self, text_div, title):
        """Extract a single event/announcement."""
        # Extract description
        description = self._get_full_text(text_div)

        # Try to find date in the text
        date_match = re.search(r'(\d{1,2}\sde\s\w+(\sde\s\d{4})?)', description)
        date = date_match.group(0) if date_match else ""

        # If no specific date but there's a deadline, use it
        if not date:
            deadline_match = re.search(r'hasta el (\d{1,2}\sde\s\w+(\sde\s\d{4})?)', description)
            if deadline_match:
                date = f"Hasta el {deadline_match.group(1)}"

        # Extract location (usually contains "CS" or "Centro Social")
        location_matches = re.findall(r'(CS\s[\w\s]+|Centro Social[\w\s]+)', description)
        location = "; ".join(location_matches) if location_matches else "Oviedo"

        return self.create_event(
            title=title,
            date=date,
            location=location,
            description=description,
            url=self.url,
            source="Centros Sociales Oviedo"
        )

    def _parse_event_section(self, section_title, details, date_range):
        """Parse an event section into individual events."""
        events = []

        # Clean the section title
        title = section_title.replace('<strong>', '').replace('</strong>', '').strip()

        # Basic description is the title
        description = title

        # Combine details
        details_text = ""
        for detail in details:
            if detail.name == 'ul':
                for li in detail.find_all('li'):
                    # Each list item could be a separate event or part of the same event
                    item_text = li.get_text().strip()

                    # Try to extract date, time and location
                    date_time_location = self._extract_date_time_location(item_text)

                    if date_time_location["date"]:
                        # If we have a date, this item is likely a separate event
                        event_title = f"{title} - {item_text.split('-')[0].strip()}" if '-' in item_text else title
                        event_description = f"{description}\n{item_text}"

                        events.append(self.create_event(
                            title=event_title,
                            date=date_time_location["date"],
                            location=date_time_location["location"] or "Oviedo",
                            description=event_description,
                            url=self.url,
                            source="Centros Sociales Oviedo"
                        ))
                    else:
                        # No date, just add to details
                        details_text += f"\n- {item_text}"
            else:
                details_text += f"\n{detail.get_text().strip()}"

        # If no individual events were extracted, create one general event
        if not events and date_range:
            events.append(self.create_event(
                title=title,
                date=date_range,
                location="Oviedo",
                description=f"{description}{details_text}",
                url=self.url,
                source="Centros Sociales Oviedo"
            ))

        return events

    def _extract_date_range(self, header_text):
        """Extract date range from header text."""
        date_match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+a\s+(\d{1,2})\s+de\s+(\w+)', header_text)
        if date_match:
            start_day, start_month, end_day, end_month = date_match.groups()
            return f"Del {start_day} al {end_day} de {end_month}"
        return ""

    def _extract_date_time_location(self, text):
        """Extract date, time and location from text."""
        result = {"date": "", "time": "", "location": ""}

        # Look for weekday + date pattern (e.g. "MIÉRCOLES 14 de mayo")
        weekday_date_match = re.search(r'([Ll]unes|[Mm]artes|[Mm]iércoles|[Jj]ueves|[Vv]iernes|[Ss]ábado|[Dd]omingo)\s+(\d{1,2})\s+de\s+(\w+)', text)
        if weekday_date_match:
            weekday, day, month = weekday_date_match.groups()
            result["date"] = f"{weekday} {day} de {month}"

        # Look for just date pattern (e.g. "17 de mayo")
        elif re.search(r'(\d{1,2})\s+de\s+(\w+)', text):
            date_match = re.search(r'(\d{1,2})\s+de\s+(\w+)', text)
            if date_match:
                day, month = date_match.groups()
                result["date"] = f"{day} de {month}"

        # Look for time pattern (e.g. "17h" or "17:00h")
        time_match = re.search(r'(\d{1,2})[:|.]*(\d{2})*h', text)
        if time_match:
            hour = time_match.group(1)
            minutes = time_match.group(2) if time_match.group(2) else "00"
            result["time"] = f"{hour}:{minutes}"

            # Add time to date if we have both
            if result["date"]:
                result["date"] = f"{result['date']} - {result['time']}"

        # Look for location (CS + name)
        location_match = re.search(r'(CS\s[\w\s]+|Centro Social[\w\s]+)', text)
        if location_match:
            result["location"] = location_match.group(0).strip()

        return result

    def _get_full_text(self, element):
        """Extract all text from an element and its children."""
        if not element:
            return ""

        texts = []
        for child in element.children:
            if child.name:
                texts.append(self._get_full_text(child))
            else:
                texts.append(child.strip())

        return " ".join(text for text in texts if text)

class VisitOviedoScraper(EventScraper):
    """Scraper for Visit Oviedo's tourism agenda."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.visitoviedo.info"
        self.url = f"{self.base_url}/agenda"
        self.max_pages = 3  # Maximum number of pages to scrape
        self.source_name = "Visit Oviedo"

    def scrape(self):
        """Scrape events from Visit Oviedo tourism website with pagination support."""
        logger.info(f"Starting pagination scrape of Visit Oviedo (max {self.max_pages} pages)")

        def extract_page_events(soup):
            """Extract events from a single page"""
            return self._process_page(soup)

        def find_next_page_url(soup):
            """Find the URL of the next page"""
            pagination = soup.select_one('div.paginator')
            if not pagination:
                return None

            # Look for "Siguiente" link
            next_link = pagination.select_one('ul.pager li a:-soup-contains("Siguiente")')
            if not next_link:
                # Alternative approach if the first selector doesn't work
                links = pagination.select('ul.pager li a')
                next_link = None
                for link in links:
                    if 'Siguiente' in link.text:
                        next_link = link
                        break

            if not next_link:
                return None

            return next_link.get('href', '')

        # Process all pages
        all_events = []
        current_page = 1
        current_url = self.url

        while current_page <= self.max_pages:
            logger.info(f"Fetching page {current_page}: {current_url}")

            try:
                soup = self.fetch_and_parse(current_url)
                if not soup:
                    break

                # Extract events from the current page
                page_events = extract_page_events(soup)
                all_events.extend(page_events)

                logger.info(f"Extracted {len(page_events)} events from page {current_page}")

                # Find the next page URL
                next_url = find_next_page_url(soup)
                if not next_url:
                    logger.info("No next page found or reached last page")
                    break

                # Handle different URL formats
                if isinstance(next_url, list):
                    next_url = next_url[0] if next_url else ""

                # Make the URL absolute
                if next_url and not next_url.startswith('http'):
                    next_url = f"{self.base_url}{next_url}"

                current_url = next_url
                current_page += 1

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                break

        logger.info(f"Pagination complete. Scraped {len(all_events)} total events")
        return all_events

    def _process_page(self, soup):
        """Process a single page and extract all events from it."""
        events = []

        try:
            # Find all day entries
            day_entries = soup.select('div.day-entry')

            for day_entry in day_entries:
                # Extract the date information
                day_wrapper = day_entry.select_one('div.day-wrapper')
                if not day_wrapper:
                    continue

                day_link = day_wrapper.select_one('a.day')
                if not day_link:
                    continue

                # Extract day, month, weekday
                day_of_month = day_link.select_one('span.day-of-month')
                month = day_link.select_one('span.month')
                day_of_week = day_link.select_one('span.day-of-week')

                if not (day_of_month and month and day_of_week):
                    continue

                date_str = f"{day_of_week.text.strip()} {day_of_month.text.strip()} de {month.text.strip()}"

                # Extract all event entries for this day
                event_entries = day_wrapper.select('div.entry')

                for event_entry in event_entries:
                    event_link = event_entry.select_one('a')
                    if not event_link:
                        continue

                    title_span = event_link.select_one('span.title')
                    hour_span = event_link.select_one('span.hour')
                    location_span = event_link.select_one('span.location')

                    if not (title_span and location_span):
                        continue

                    title = title_span.text.strip()
                    location = location_span.text.strip().replace('marker', '').strip()

                    # Add time to date if available
                    event_date = date_str
                    if hour_span:
                        time_text = hour_span.text.strip().replace('Tiempo', '').strip()
                        event_date = f"{date_str} - {time_text}"

                    # Get the event URL
                    event_url = event_link.get('href', '')
                    if event_url:
                        # Make URL absolute if it's relative
                        if not event_url.startswith('http'):
                            event_url = f"{self.base_url}{event_url}"
                    else:
                        event_url = self.url

                    # Create the event
                    event = self.create_event(
                        title=title,
                        date=event_date,
                        location=location,
                        description="",
                        url=event_url,
                        source="Visit Oviedo"
                    )

                    events.append(event)

        except Exception as e:
            logger.error(f"Error extracting events from page: {e}")

        return events

class BiodevasScraper(EventScraper):
    """Scraper for Biodevas.org activities in Asturias."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://biodevas.org"
        self.url = f"{self.base_url}/page/"
        self.max_pages = 3  # Maximum number of pages to scrape
        self.source_name = "Biodevas"
        self._processed_urls = set()  # Track processed URLs to avoid duplicates

    def scrape(self):
        """Scrape events from Biodevas.org with pagination support."""
        logger.info(f"Starting pagination scrape of Biodevas (max {self.max_pages} pages)")

        return self.process_pagination(
            base_url=self.base_url,
            start_url=self.base_url,
            max_pages=self.max_pages,
            extract_page_events=self._extract_events_from_page,
            next_page_selector='.next.page-numbers'
        )

    def _extract_events_from_page(self, soup):
        """Extract events from a single page of Biodevas.org."""
        events = []

        # Find all event articles
        articles = soup.select('article.hentry')
        if not articles:
            logger.warning("No event articles found on this page")
            return []

        logger.info(f"Found {len(articles)} event articles")

        for article in articles:
            try:
                event = self._extract_event_from_article(article)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error processing event article: {e}")
                continue

        return events

    def _extract_event_from_article(self, article):
        """Extract event information from an article element."""
        # Extract title
        title_elem = article.select_one('h2.entry-title a')
        if not title_elem:
            return None

        title = title_elem.get_text().strip()

        # Extract URL
        url = title_elem.get('href', '')

        # Skip if we've already processed this URL
        if url in self._processed_urls:
            return None
        self._processed_urls.add(url)

        # Extract tags for location info
        tags = article.select('.tags a')
        location = "Asturias"  # Default location

        # Look for location tags
        for tag in tags:
            tag_text = tag.get_text().strip()
            if tag_text in ["Oviedo", "Gijón", "Avilés", "Lugones", "Siero", "Villaviciosa"]:
                location = tag_text
                break

        # Extract date from content
        date = ""
        summary = article.select_one('.entry-summary')
        if summary:
            summary_text = summary.get_text().strip()

            # First try specific patterns common on this site
            date_match = re.search(r'(\d{1,2}).*?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)', summary_text, re.IGNORECASE)
            if date_match:
                date = date_match.group(0)
            else:
                # Use utility function from scraper_utils
                from scraper_utils import extract_date_from_text
                date = extract_date_from_text(summary_text)

            # If no date found, try to find if it's an ongoing activity
            if not date:
                if "todo tipo de públicos" in summary_text or "actividad gratuita" in summary_text.lower():
                    date = "Actividad permanente"

        # If no date found in summary, check if there are any date tags
        if not date:
            for tag in tags:
                tag_text = tag.get_text().strip().lower()
                # Check if tag contains a month name
                months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                if any(month in tag_text for month in months):
                    date = tag_text
                    break

        # Create and return the event
        return self.create_event(
            title=title,
            date=date,
            location=location,
            url=url,
            source=self.source_name
        )

class AvilesEventsScraper(EventScraper):
    """Scraper for upcoming events from the Avilés city website."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://aviles.es"
        self.url = f"{self.base_url}/proximos-eventos"
        self.source_name = "Avilés"

    def scrape(self):
        """Scrape events from the Avilés city website."""
        logger.info(f"Fetching events from Avilés website")

        # Only process the first page as pagination requires authentication
        soup = self.fetch_and_parse(self.url)
        if not soup:
            logger.error("Failed to fetch Avilés events page")
            return []

        return self._extract_events_from_page(soup)

    def _extract_events_from_page(self, soup):
        """Extract events from a single page."""
        events = []

        # Find all event cards
        event_cards = soup.select('.card.border-info')
        if not event_cards:
            logger.warning("No event cards found on this page")
            return []

        logger.info(f"Found {len(event_cards)} event cards")

        for card in event_cards:
            try:
                event = self._extract_event_from_card(card)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error processing event card: {e}")
                continue

        return events

    def _extract_event_from_card(self, card):
        """Extract event information from a card element."""
        # Extract title
        title_elem = card.select_one('h5')
        if not title_elem:
            return None

        title = title_elem.get_text().strip()

        # Extract dates and other metadata from badges
        badges = card.select('.badge.badge-secondary')

        # Initialize variables
        event_date = ""
        event_end_date = ""
        is_recurring = False
        recurrence_end = ""

        for badge in badges:
            badge_text = badge.get_text().strip()

            if badge_text.startswith("INICIO:"):
                # Extract start date and time
                date_parts = badge_text.replace("INICIO:", "").strip().split()
                if len(date_parts) >= 1:
                    # Format date properly
                    try:
                        date_obj = datetime.datetime.strptime(date_parts[0], "%d-%m-%Y")
                        day = date_obj.day
                        month = self._get_spanish_month(date_obj.month)
                        event_date = f"{day} de {month}"

                        # Add time if available
                        if len(date_parts) >= 2:
                            event_date += f" - {date_parts[1]}"
                    except Exception as e:
                        logger.warning(f"Error parsing start date: {e}")
                        event_date = badge_text.replace("INICIO:", "").strip()

            elif badge_text.startswith("Evento Recurrente"):
                is_recurring = True
                # Extract recurrence end date
                match = re.search(r'Finaliza:\s+(\d{2}-\d{2}-\d{4})', badge_text)
                if match:
                    try:
                        end_date = match.group(1)
                        date_obj = datetime.datetime.strptime(end_date, "%d-%m-%Y")
                        recurrence_end = f"hasta el {date_obj.day} de {self._get_spanish_month(date_obj.month)}"
                    except Exception as e:
                        logger.warning(f"Error parsing recurrence end date: {e}")
                        recurrence_end = badge_text.replace("Evento Recurrente - Finaliza:", "").strip()

        # If it's a recurring event, add that information to the date
        if is_recurring and recurrence_end:
            if event_date:
                event_date = f"{event_date} ({recurrence_end})"
            else:
                event_date = f"Evento recurrente {recurrence_end}"

        # Extract description and other details
        description_elem = card.select_one('.card-text')
        description = description_elem.get_text().strip() if description_elem else ""

        # Extract location from description
        location = "Avilés"  # Default location

        # Common venue keywords to look for
        venue_keywords = [
            "Teatro", "Auditorio", "Sala", "Centro", "Museo",
            "Plaza", "Pabellón", "Recinto", "Factoría", "Palacio",
            "Niemeyer", "CMAE", "Escuela"
        ]

        # Try to find venue in description
        for keyword in venue_keywords:
            pattern = rf"{keyword}\s+[A-Za-zÀ-ÿ\s\.]+"
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                location = match.group(0).strip()
                break

        # Look for specific venue mentions
        if "Palacio Valdés" in description or "Teatro Palacio" in description:
            location = "Teatro Palacio Valdés"
        elif "Centro Niemeyer" in description or "Niemeyer" in description:
            location = "Centro Niemeyer"
        elif "CMAE" in description:
            location = "Centro Municipal de Arte y Exposiciones (CMAE)"
        elif "Factoría Cultural" in description:
            location = "Factoría Cultural de Avilés"

        # Event URL - We don't have direct links in the cards,
        # so we'll use the main page URL
        url = self.url

        # Create and return the event
        return self.create_event(
            title=title,
            date=event_date,
            location=location,
            url=url,
            source=self.source_name
        )

    def _get_spanish_month(self, month_num):
        """Get Spanish month name from month number (1-12)."""
        spanish_months = [
            'enero', 'febrero', 'marzo', 'abril',
            'mayo', 'junio', 'julio', 'agosto',
            'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        return spanish_months[month_num - 1]