# CogniSense - AI Personal Assistant Backend

CogniSense is an intelligent, conversational AI assistant that helps users manage and make sense of their content, including documents, web links, and personal notes. This repository contains the backend services for the CogniSense application.

## Features

- **Conversational AI**: Powered by Azure OpenAI models for natural language understanding and generation
- **Document Management**: Upload, store, and search various document types (PDF, DOCX, TXT)
- **Web Content Extraction**: Process and index content from URLs
- **Vector Search**: Use embeddings for semantic search across your content
- **User Authentication**: Secure JWT-based authentication system
- **Learning Tools**: Generate quizzes and flashcards from conversation history
- **Topic Detection**: Automatically categorize conversations by topic

## Technology Stack

- **Framework**: Flask
- **AI Services**: Azure OpenAI
- **Database**: Azure Cosmos DB
- **Storage**: Azure Blob Storage
- **Search**: Azure Cognitive Search
- **Natural Language Processing**: NLTK for text preprocessing
- **Authentication**: JWT

## Project Structure

```
bot-backend/
├── utils/
│   ├── azure_utils.py     # Azure services integration
│   ├── data_utils.py      # Data structures and utilities
│   ├── gpt_utils.py       # OpenAI API integration
│   ├── knowledge_utils.py # NLP and token handling
│   └── nltk_data/         # NLTK data directory
├── bot_handler.py         # API endpoint handlers
├── nltk_download.py       # Script to download NLTK resources
├── requirements.txt       # Project dependencies
└── web_app.py             # Flask application setup
```

## Sample data
Data is stored in Azure Storage Account and categorized into 3 types:

- Documents: text files that are not notes (PDF, TXT)
- Notes: meeting discussion, exam notes, personal notes
- Blogs: file text TXT extracted from web link

## Setup and Installation

### Prerequisites

- Python 3.13+
- Azure account with the following services:
  - Azure AI services multi-service account (for OCR skill)
  - Azure OpenAI (for embedding and LLM model)
  - Azure Cosmos DB (for storing user login and chat history)
  - Azure Blob Storage (for storing sample data)
  - Azure AI Search (indexing service)
  - Azure App Service (2 apps, one for frontend and the other for backend)

### Installation Steps for Backend

1. Clone the repository:
   ```
   git clone <repository-url>
   cd bot-backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Download NLTK data:
   ```
   python nltk_download.py
   ```

5. Create a `.env` file folllowith the file `.env.example`

6. Run the application:
   ```
   python web_app.py
   ```
   
7. Start up command in Azure Web APP
  ```
  gunicorn --bind=0.0.0.0:8000 --timeout 600 web_app:app
  ```

## API Endpoints

### Authentication

- **POST /bot/register**: Register a new user
  - Request: `{ "username": "user", "password": "pass" }`
  - Response: `{ "message": "User registered successfully", "access_token": "jwt-token" }`

- **POST /bot/login**: Login an existing user
  - Request: `{ "username": "user", "password": "pass" }`
  - Response: `{ "message": "Login successful", "access_token": "jwt-token" }`

### Content Management

- **POST /bot/ingest_url**: Extract and store content from a URL
  - Request: Form data with `url` field
  - Response: `{ "message": "Uploaded to...", "filename": "filename.txt" }`

- **POST /bot/ingest_file**: Upload and store a file
  - Request: Form data with `file` and `type` fields
  - Response: `{ "message": "Uploaded to...", "filename": "filename.ext" }`

### Conversation

- **POST /bot/chat**: Send a message to the AI assistant
  - Request: `{ "query": "your question here" }`
  - Response: `{ "topic": "detected topic", "answer": "AI response" }`

### Learning Tools

- **POST /bot/quiz**: Generate quizzes from conversation history
  - Request: `{ "topic": "optional topic" }`
  - Response: `{ "message": "status message", "quiz": { "data": [...] } }`

- **POST /bot/flashcard**: Generate flashcards from conversation history
  - Request: `{ "topic": "optional topic" }`
  - Response: `{ "message": "status message", "flashcard": { "data": [...] } }`

## Authorization

All endpoints except `/bot/register` and `/bot/login` require a valid JWT token in the Authorization header:

```
Authorization: Bearer your-jwt-token
```

## Development

### Adding New Features

1. Implement feature logic in appropriate utility modules
2. Add new API endpoints in `bot_handler.py`
3. Register new endpoints in `web_app.py` if needed

### Testing

Run the Flask development server with:

```
flask --app web_app run
```

The server runs in debug mode by default, accessible at http://localhost:5000
