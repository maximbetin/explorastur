import requests
from bs4 import BeautifulSoup

def scrape_events(url):
    """
    Scrapes events from the given URL.

    Args:
        url (str): The URL of the webpage to scrape.

    Returns:
        list: A list of dictionaries, each containing event details.
    """
    response = requests.get(url)
    response.raise_for_status()  # Ensure the request was successful
    soup = BeautifulSoup(response.text, 'html.parser')

    events = []
    # Iterate over all divs with class 'main'
    for div in soup.find_all('div', class_='main'):
        article_body = div.find('div', class_='article-body')
        if not article_body:
            continue  # Skip if no article body is found

        # Split the text by specific markers or patterns that indicate new events
        paragraphs = article_body.find_all('p', class_='western')
        current_event = {}
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Check if the paragraph contains an underlined link
            link_tag = p.find('u')
            if link_tag:
                link = p.find('a').get('href')
                current_event['Link'] = link

            # Check for a pattern that indicates a new event
            if ':' in text and any(char.isdigit() for char in text.split(':')[0]):
                # If there's an existing event, append it before starting a new one
                if current_event:
                    events.append(current_event)
                    current_event = {}

            # Append text to the current event description
            if 'Event' not in current_event:
                current_event['Event'] = text
            else:
                current_event['Event'] += " " + text

        # Append the last event if it exists and is valid
        if current_event and ':' in current_event.get('Event', ''):
            events.append(current_event)

    return events

def process_and_display_events(events):
    """
    Processes and displays the list of events.

    Args:
        events (list): A list of dictionaries containing event details.
    """
    for index, event in enumerate(events, start=1):
        # Extract the date from the description
        description = event.get('Event', 'No description')
        date_end_index = description.find(':')
        if date_end_index != -1:
            # Separate the date from the rest of the description
            event_date = description[:date_end_index].strip()
            event_description = description[date_end_index + 1:].strip()
        else:
            event_date = "Unknown date"
            event_description = description

        # Display the event details
        print(f"Event {index}: {event_date}")
        print(f"Description: {event_description}")
        if 'Link' in event:
            print(f"Link: {event['Link']}")
        print("-" * 40)

def main():
    """
    Main function to scrape and display events from a predefined URL.
    """
    url = "https://blog.telecable.es/agenda-planes-asturias/"
    events = scrape_events(url)
    process_and_display_events(events)

if __name__ == "__main__":
    main()
