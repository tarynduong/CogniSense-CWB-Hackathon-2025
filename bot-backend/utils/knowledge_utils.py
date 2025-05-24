from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
import requests
import string

nltk.data.path.append("./utils/nltk_data")

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

def preprocess_user_query(query):
    """
    === Features Summary ===
    - Remove stop words
    - Extract keywords
    - Lemmatize words to get the base form
    Using WordNetLemmatizer() to reduce words to their base or dictionary form and add these words into the query.
    For example: the lemma of "running" is "run", "better" => "good".
    - Synonym expansion (e.g., “meetings” ≈ “sessions”)
    Using the synsets() function from the WordNet interface in NLTK to get a list of "synsets" (synonym sets) for that word. 
    A synset is a group of words that have a similar meaning.
    """
    ## Step 1: Tokenize & lowercase query
    query = query.lower()
    tokens = nltk.word_tokenize(query)

    ## Step 2: Remove stopwords & punctuation 
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words and word not in string.punctuation]
    
    ## Step 3: Lemmatize words to get the base form
    lemmatizer = WordNetLemmatizer()
    base_words = [lemmatizer.lemmatize(token, pos='n') for token in tokens if token.isalnum()]

    ## Step 4: Expand synonyms
    synonyms = set(base_words)
    for word in base_words:
        synsets = wordnet.synsets(word)
        if synsets:
            # Take the first synonym from the first synset that isn't the word itself
            for lemma in synsets[0].lemmas():
                synonym = lemma.name().replace("_", " ").lower()
                if synonym != word and len(synonym) <= 25:
                    synonyms.add(synonym)
                    break  # Only add one synonym
    
    combined_list = tokens + base_words + list(synonyms)
    unique_keywords = []
    for i in combined_list:
        if i not in unique_keywords:
            unique_keywords.append(i)
    # fuzzy_terms = [f"{word}~" for word in unique_keywords if len(word) >= 3]
    # expanded_query = " OR ".join(fuzzy_terms)
    expanded_query = " ".join(unique_keywords)
    return expanded_query