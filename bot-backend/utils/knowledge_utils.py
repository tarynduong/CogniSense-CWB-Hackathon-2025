from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
import requests
import string
import jwt
import hashlib
from datetime import datetime as dt
import os
from dotenv import load_dotenv

load_dotenv(override=True)

_RAW_SECRET_KEY = os.getenv("SECRET_KEY") or ""
# Derive a stable 32-byte key so HS256 always meets RFC 7518's minimum key
# length. This avoids PyJWT's InsecureKeyLengthWarning / InvalidKeyError when
# the configured SECRET_KEY is shorter than 32 bytes, without changing config.
SECRET_KEY = hashlib.sha256(_RAW_SECRET_KEY.encode("utf-8")).digest()

nltk.data.path.append("./utils/nltk_data")


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


class UrlFetchError(Exception):
    """
    Raised when a URL cannot be ingested. `reason` is a machine-readable code
    the API layer maps to a user-facing notification:
      - "blocked"      : site refused automated access (403/429/Cloudflare)
      - "timeout"      : site too slow
      - "unreachable"  : DNS / connection failure
      - "http_error"   : other HTTP error status
      - "not_webpage"  : link is not HTML (e.g. a PDF or binary)
      - "no_content"   : page loaded but no readable text (often JS-rendered)
    """

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def _beautifulsoup_extract(html: bytes) -> str:
    """Fallback extractor: strip scripts/styles and collapse whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for script_or_style in soup.find_all(["script", "style", "noscript"]):
        script_or_style.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def extract_text_from_url(url: str) -> str:
    """
    Extract the main text content from a web page.

    Strategy (graceful fallback):
      1. Fetch the HTML with a browser-like User-Agent (avoids many 403s).
      2. Try trafilatura, which isolates the main article body and drops
         navigation/boilerplate -- works on far more sites than raw parsing.
      3. If trafilatura returns nothing, fall back to BeautifulSoup.

    Returns the extracted text (may be empty if the page is JavaScript-rendered
    or otherwise unreadable; the caller should handle the empty case).
    """
    try:
        response = requests.get(url, headers=_BROWSER_HEADERS, timeout=20)
    except requests.exceptions.Timeout:
        raise UrlFetchError("timeout", "The site took too long to respond.")
    except requests.exceptions.RequestException as e:
        raise UrlFetchError("unreachable", f"Could not connect to the site. ({e})")

    status = response.status_code
    # 403/401/429 and Cloudflare-style 503 almost always mean anti-bot blocking.
    if status in (401, 403, 429, 451) or status == 503:
        raise UrlFetchError(
            "blocked",
            f"The site blocked automated access (HTTP {status}).",
        )
    if status >= 400:
        raise UrlFetchError(
            "http_error",
            f"The site returned an error (HTTP {status}).",
        )

    content_type = response.headers.get("Content-Type", "").lower()
    if "html" not in content_type and "text" not in content_type:
        # Not an HTML/text page (e.g. a direct PDF link); not scrapeable here.
        raise UrlFetchError(
            "not_webpage",
            f"That link isn't a readable web page (content type: {content_type or 'unknown'}).",
        )

    # 1) Preferred: trafilatura main-content extraction.
    text = ""
    try:
        import trafilatura
        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        if extracted:
            text = extracted.strip()
    except Exception:
        # trafilatura unavailable or failed -> fall through to BeautifulSoup.
        text = ""

    # 2) Fallback: BeautifulSoup.
    if not text:
        text = _beautifulsoup_extract(response.content)

    if not text or not text.strip():
        raise UrlFetchError(
            "no_content",
            "The page loaded but no readable text was found "
            "(it may be JavaScript-rendered).",
        )

    return text


def encode_token(id):
    token = jwt.encode(
        {"user_id": id, "exp": int(dt.now().timestamp()) + 86400},
        SECRET_KEY,
        algorithm="HS256"
    )
    return token


def decode_token(token):
    if not token:
        return "Unauthorized: missing token", 401
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return "Unauthorized: token expired", 401
    except jwt.InvalidKeyError:
        # Server-side key misconfiguration, not a bad user token.
        return "Server authentication error", 500
    except jwt.InvalidTokenError:
        return "Unauthorized: invalid token", 401

    exp = payload.get("exp")
    if exp is None or exp < dt.now().timestamp():
        return "Unauthorized", 401
    return payload, 200


def preprocess_user_query(query):
    """
    === Summary ===
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
    expanded_query = " ".join(unique_keywords)
    return expanded_query
