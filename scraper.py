#!/usr/bin/env python3
"""
ExplorAstur - Simple Telecable event scraper for Asturias
---------------------------------------------------------
Simple script that scrapes events from Telecable blog
and outputs them to a markdown file.
"""

import os
import yaml
import datetime
import logging
import requests
from bs4 import BeautifulSoup
import re
import sys

# Create directories
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Configure logging
logger = logging.getLogger('explorastur')
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # Add file handler
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/explorastur_{today}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")

def get_current_month_year():
    """Get the current month name in Spanish and year."""
    months = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }
    now = datetime.datetime.now()
    return f"{months[now.month]} {now.year}"

def scrape_telecable():
    """Scrape events from Blog Telecable Asturias."""
    events = []
    url = "https://blog.telecable.es/agenda-planes-asturias/"

    logger.info(f"Fetching URL: {url}")

    # Get current month and year
    current_month_year = get_current_month_year()

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
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

    # Variables to track current section
    current_section = ""
    current_image = ""

    # Process the article body to find events
    for element in article_body.find_all(['h2', 'p', 'figure']):
        # Process h2 tags as section markers
        if element.name == 'h2':
            current_section = element.get_text(strip=True)
            current_image = ""
            continue

        # Process figures with images
        if element.name == 'figure' and not current_image:
            img = element.find('img')
            if img and img.get('src'):
                current_image = img.get('src')
            continue

        # Process paragraphs for events
        if element.name == 'p' and element.get('class') and 'western' in element.get('class'):
            # Case 1: Bold titles (most concerts and events)
            bold = element.find('b')
            if bold:
                # Extract event title and check if it looks like an event
                event_title = bold.get_text(strip=True)
                if not re.search(r'\d+\s+de\s+[a-zA-Z]+', event_title) and not 'mayo' in event_title.lower():
                    continue

                # Extract data from the text
                full_text = element.get_text(strip=True)

                # Extract date
                date_match = re.search(r'(\d+(?:\s+y\s+\d+)?\s+de\s+[a-zA-Z]+)', event_title) or re.search(r'(\d+(?:\s+y\s+\d+)?\s+de\s+[a-zA-Z]+)', full_text)
                event_date = date_match.group(1) if date_match else ""

                # Check for month-long events
                month_long = False
                if not event_date and ("Durante todo el mes" in event_title or "todo el mes" in full_text):
                    event_date = current_month_year
                    month_long = True

                # Extract location
                location_patterns = [
                    r'en\s+(?:el|la|los|las)\s+(.*?)(?:\.|el día|\s+los días)',
                    r'en\s+(.*?)(?:\.|el día|\s+los días)',
                    r'(?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría)\s+[^\.]+',
                ]

                event_location = ""
                for pattern in location_patterns:
                    location_match = re.search(pattern, full_text)
                    if location_match:
                        event_location = location_match.group(0).replace("en ", "")
                        break

                # Extract URL from links
                event_url = ""
                links = element.find_all('a')
                if links:
                    for link in links:
                        if link.get('href'):
                            event_url = link.get('href')
                            # Skip if the URL is the same as the blog URL
                            if event_url == url:
                                event_url = ""
                            break

                # If no URL was found, check the next paragraph
                if not event_url:
                    next_p = element.find_next('p')
                    if next_p:
                        links = next_p.find_all('a')
                        if links:
                            for link in links:
                                if link.get('href') and link.get('href') != url:
                                    event_url = link.get('href')
                                    break

                # Clean up the title - remove date prefix if it matches the extracted date
                clean_title = event_title.replace(':', '').strip()
                if event_date and clean_title.startswith(event_date):
                    clean_title = clean_title[len(event_date):].strip()

                # Create event
                events.append({
                    'title': clean_title,
                    'date': event_date,
                    'location': event_location.strip(),
                    'description': full_text.replace(event_title, '').strip(),
                    'url': event_url if event_url.startswith(('http://', 'https://')) else f"{url.rstrip('/')}/{event_url.lstrip('/')}",
                    'image': current_image if current_image.startswith(('http://', 'https://')) else "",
                    'source': "Blog Telecable Asturias"
                })

            # Case 2: Festival listings (in fiestas sections)
            elif "fiestas" in current_section.lower():
                text = element.get_text(strip=True)

                # Skip short paragraphs
                if len(text) < 5:
                    continue

                # Find date pattern
                date_match = re.search(r'(\d+(?:\s+[a-zA-Z]+)?\s+de\s+[a-zA-Z]+)', text) or re.search(r'(\d+(?:\s+a|\s+al|\s+y)\s+\d+(?:\s+de)?\s+[a-zA-Z]+)', text)
                if not date_match:
                    continue

                event_date = date_match.group(1)

                # Extract title and clean it
                if ":" in text:
                    event_title = text.split(":", 1)[1].strip()
                else:
                    event_title = text

                # Clean up title - remove date patterns
                for pattern in [r'\d+\s+de\s+[a-zA-Z]+:', r'\d+\s+a\s+\d+\s+de\s+[a-zA-Z]+:', r'\d+-\d+\s+de\s+[a-zA-Z]+:']:
                    event_title = re.sub(pattern, '', event_title).strip()

                # Extract URL
                event_url = ""
                link = element.find('a')
                if link and link.get('href'):
                    event_url = link.get('href')
                    # Skip if the URL is the same as the blog URL
                    if event_url == url:
                        event_url = ""

                # Create event
                events.append({
                    'title': event_title,
                    'date': event_date,
                    'location': 'Asturias',
                    'description': text,
                    'url': event_url if event_url.startswith(('http://', 'https://')) else f"{url.rstrip('/')}/{event_url.lstrip('/')}",
                    'image': current_image if current_image.startswith(('http://', 'https://')) else "",
                    'source': "Blog Telecable Asturias"
                })

    logger.info(f"Successfully extracted {len(events)} events")
    return events

def main():
    """Main execution function."""
    logger.info("Starting ExplorAstur - Telecable events scraper")

    # Get current month year
    current_month_year = get_current_month_year()

    # Scrape events from Telecable
    events = scrape_telecable()

    if not events:
        logger.warning("No events found")
        return

    logger.info(f"Found {len(events)} events")

    # Clean events data
    clean_events = []
    for event in events:
        # Clean title - remove repeating date patterns
        title = event.get('title', '').strip()
        date_pattern = event.get('date', '').strip()
        if date_pattern and title.startswith(date_pattern):
            title = title[len(date_pattern):].strip()

        # Further clean titles that start with common date prefixes
        title = re.sub(r'^(\d+\s+de\s+[a-zA-Z]+\s+)', '', title)

        # Check if URL is blank or points to the main blog
        url = event.get('url', '').strip()
        if url == "https://blog.telecable.es/agenda-planes-asturias/":
            url = ""

        # Filter out non-events
        non_event_patterns = [
            r'agenda',
            r'asturias en [a-z]+',
            r'¿quieres saber',
            r'planes',
            r'vamos allá'
        ]

        is_non_event = False
        for pattern in non_event_patterns:
            if re.search(pattern, title.lower()):
                is_non_event = True
                break

        # Add to clean events only if it's not a non-event and has a meaningful title
        if title and not is_non_event:
            clean_events.append({
                'title': title,
                'date': date_pattern or current_month_year, # Default to current month/year if no date
                'location': event.get('location', '').strip() or "N/A",
                'url': url
            })

    # Export to markdown
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    output_file = f'output/events_{date_str}.md'

    # Sort by date
    clean_events.sort(key=lambda x: x.get('date', ''))

    # Build markdown - simple list format
    md = ["# Eventos en Asturias\n", f"_Actualizado: {datetime.datetime.now().strftime('%d-%m-%Y')}_\n\n"]

    # Add events in a simple list format
    for event in clean_events:
        date_info = event.get('date') or current_month_year
        location = event.get('location')

        # Format: Date: Title - Location - URL
        line = f"- {date_info}: {event.get('title')}"

        # Add location if available (not N/A)
        if location and location != "N/A":
            line += f" - {location}"

        # Add URL if available and not the blog URL
        if event.get('url'):
            line += f" - [Enlace]({event.get('url')})"

        md.append(line + "\n")

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(md))

    logger.info(f"Exported {len(clean_events)} events to {output_file}")
    logger.info("ExplorAstur completed successfully")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        sys.exit(1)