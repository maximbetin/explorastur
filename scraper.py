#!/usr/bin/env python3
"""
ExplorAstur - Simple event scraper for Asturias
-----------------------------------------------
This script scrapes event information from various websites
and outputs it to a markdown file.
"""

import os
import yaml
import datetime
import logging
import requests
from bs4 import BeautifulSoup
import re
import sys
from typing import List, Dict, Any, Optional, Tuple

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

def scrape_telecable(source):
    """Scrape events from Blog Telecable Asturias."""
    events = []

    # Fetch the page
    url = source.get('url')
    logger.info(f"Fetching URL: {url}")

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

    logger.info(f"Using specialized parser for {source.get('name')}")

    # Extract category sections (h2 elements)
    current_category = "General"
    current_category_image = ""

    # Process the article body to find categories and events
    for element in article_body.find_all(['h2', 'p', 'figure']):
        # Process h2 tags as category headers
        if element.name == 'h2':
            current_category = element.get_text(strip=True)
            current_category_image = ""
            continue

        # Process figures with images for the current category
        if element.name == 'figure' and not current_category_image:
            img = element.find('img')
            if img and img.get('src'):
                current_category_image = img.get('src')
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
                            break

                # If no URL was found, check the next paragraph
                if not event_url:
                    next_p = element.find_next('p')
                    if next_p:
                        links = next_p.find_all('a')
                        if links:
                            for link in links:
                                if link.get('href'):
                                    event_url = link.get('href')
                                    break

                # Create event
                events.append({
                    'title': event_title.replace(':', '').strip(),
                    'date': event_date,
                    'location': event_location.strip(),
                    'description': full_text.replace(event_title, '').strip(),
                    'url': event_url if event_url.startswith(('http://', 'https://')) else f"{url.rstrip('/')}/{event_url.lstrip('/')}",
                    'image': current_category_image if current_category_image.startswith(('http://', 'https://')) else "",
                    'category': current_category,
                    'source': source.get('name')
                })

            # Case 2: Festival listings (in fiestas sections)
            elif "Nos vamos de fiestas" in current_category or "fiestas" in current_category.lower():
                text = element.get_text(strip=True)

                # Skip short paragraphs
                if len(text) < 5:
                    continue

                # Find date pattern
                date_match = re.search(r'(\d+(?:\s+[a-zA-Z]+)?\s+de\s+[a-zA-Z]+)', text) or re.search(r'(\d+(?:\s+a|\s+al|\s+y)\s+\d+(?:\s+de)?\s+[a-zA-Z]+)', text)
                if not date_match:
                    continue

                event_date = date_match.group(1)

                # Extract title
                event_title = text.split(":", 1)[1].strip() if ":" in text else text

                # Extract URL
                event_url = ""
                link = element.find('a')
                if link and link.get('href'):
                    event_url = link.get('href')

                # Create event
                events.append({
                    'title': event_title,
                    'date': event_date,
                    'location': 'Asturias',
                    'description': text,
                    'url': event_url if event_url.startswith(('http://', 'https://')) else f"{url.rstrip('/')}/{event_url.lstrip('/')}",
                    'image': current_category_image if current_category_image.startswith(('http://', 'https://')) else "",
                    'category': 'Festivales y Fiestas',
                    'source': source.get('name')
                })

    logger.info(f"Successfully extracted {len(events)} events")
    return events

def main():
    """Main execution function."""
    logger.info("Starting ExplorAstur - Asturias events scraper")

    # Load configuration
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict) or 'sources' not in config or not isinstance(config['sources'], list):
                logger.error("Invalid configuration: missing or invalid 'sources'")
                return
        logger.info("Loaded configuration")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return

    all_events = []

    # Process each source
    for source in config.get('sources', []):
        source_name = source.get('name', 'Unknown')
        logger.info(f"Processing source: {source_name}")

        # Use the appropriate scraper based on source name
        if source_name == "Blog Telecable Asturias":
            events = scrape_telecable(source)
        else:
            logger.warning(f"Unsupported source: {source_name}")
            continue

        if events:
            logger.info(f"Found {len(events)} events from {source_name}")
            all_events.extend(events)
        else:
            logger.warning(f"No events found from {source_name}")

    # Clean events data
    clean_events = []
    for event in all_events:
        clean_events.append({
            'title': event.get('title', '').strip(),
            'date': event.get('date', '').strip(),
            'location': event.get('location', '').strip(),
            'description': event.get('description', '').strip(),
            'url': event.get('url', '').strip(),
            'image': event.get('image', '').strip(),
            'category': event.get('category', 'General').strip(),
            'source': event.get('source', 'Unknown').strip()
        })

    # Export to markdown
    if not clean_events:
        logger.warning("No events to export")
        return

    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    output_file = f'output/events_{date_str}.md'

    # Group by category
    by_category = {}
    for event in clean_events:
        category = event.get('category', 'General')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(event)

    # Build markdown
    md = ["# Eventos en Asturias\n", f"_Actualizado: {datetime.datetime.now().strftime('%d-%m-%Y')}_\n", "\n## Índice\n"]

    # Add table of contents
    for category in sorted(by_category.keys()):
        anchor = category.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        md.append(f"- [{category}](#{anchor}) ({len(by_category[category])} eventos)\n")

    # Add events by category
    for category in sorted(by_category.keys()):
        anchor = category.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        md.append(f"\n## {category}\n\n")

        for event in by_category[category]:
            md.append(f"### {event.get('title', 'Sin título')}\n\n")
            md.append(f"- **Fecha:** {event.get('date', 'Fecha no especificada')}\n")
            md.append(f"- **Lugar:** {event.get('location', 'Ubicación no especificada')}\n")
            md.append(f"- **Fuente:** {event.get('source', 'Desconocida')}\n")

            if event.get('url'):
                md.append(f"- **Enlace:** [{event.get('url')}]({event.get('url')})\n")

            if event.get('description'):
                md.append(f"\n{event.get('description')}\n\n")

            md.append("---\n\n")

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