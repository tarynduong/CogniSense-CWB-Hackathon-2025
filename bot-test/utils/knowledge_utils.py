from bs4 import BeautifulSoup
import requests

def extract_text_from_url(url: str):
    """
    Extracts the main content from a URL received from user, removing HTML tags, scripts.

    Args:
        url (str): The URL of the webpage to extract text from.

    Returns:
        str: The extracted text content.
    """
    # send an HTTP GET request to the URL
    response = requests.get(url)
    response.raise_for_status()
    # parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    for script_or_style in soup.find_all(['script', 'style']):
        script_or_style.decompose()
    # get the main text
    text = soup.get_text()
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

