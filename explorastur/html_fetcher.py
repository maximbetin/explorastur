"""Module for fetching and processing HTML content."""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Union


def fetch_url(url: str) -> str:
  """
  Fetch HTML content from a URL.

  Args:
      url: The URL to fetch content from

  Returns:
      The HTML content as a string

  Raises:
      Exception: If the request fails
  """
  response = requests.get(url, headers={"User-Agent": "Explorastur/1.0"})
  response.raise_for_status()
  return response.text


def extract_with_selector(html: str, selector: str) -> str:
  """
  Extract content from HTML using a CSS selector.

  Args:
      html: The HTML content
      selector: CSS selector to extract content

  Returns:
      The extracted HTML as a string
  """
  soup = BeautifulSoup(html, "html.parser")
  elements = soup.select(selector)

  if not elements:
    return ""

  # Return the HTML content of all matched elements
  return "\n".join(str(element) for element in elements)


def get_html_content(source: str, selector: Optional[str] = None) -> str:
  """
  Get HTML content from a URL or direct HTML string, optionally filtering with a selector.

  Args:
      source: URL or HTML content string
      selector: Optional CSS selector to filter content

  Returns:
      The processed HTML content
  """
  # Check if source is a URL (simple heuristic)
  is_url = source.startswith(("http://", "https://"))

  # Fetch content if it's a URL
  html = fetch_url(source) if is_url else source

  # Apply selector if provided
  if selector and html:
    html = extract_with_selector(html, selector)

  return html
