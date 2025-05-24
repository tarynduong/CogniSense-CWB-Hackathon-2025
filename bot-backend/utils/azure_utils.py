from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from dotenv import load_dotenv
import uuid
import datetime
import os
import re

load_dotenv(override=True)

# CREDENTIALS
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
AZURE_SEARCH_API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION")
AZURE_COSMOS_KEY = os.getenv("AZURE_COSMOS_KEY")
AZURE_COSMOS_ENDPOINT = os.getenv("AZURE_COSMOS_ENDPOINT")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

# Set up Service
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
)

cosmos_client = CosmosClient(AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY)
db = cosmos_client.get_database_client(database=COSMOS_DATABASE_NAME)
container = db.get_container_client(container=COSMOS_CONTAINER_NAME)

def upload_to_blob(container_name, filename, file_content):
    container_client = blob_service_client.get_container_client(f"sample-data/{container_name}")
    source_blob_client = container_client.get_blob_client(filename)
    source_blob_client.upload_blob(file_content, overwrite=True)
    return f"Uploaded to sample-data/{container_name}/{filename}"

def search_content(query):
    ## Recognize file extension if mentioned
    extensions = {
        ".pdf": ["pdf", "pdfs"],
        ".docx": ["docx", "word file"],
        ".txt": ["text", "txt", "text file"]
    }
    query = query.lower()
    file_type = None
    for key, value in extensions.items():
        for term in value:
            if re.search(term, query):
                file_type = key
    
    filter_expr = f"metadata_storage_file_extension eq '{file_type}'" if file_type else None

    # For vector and hybrid search queries purpose
    vector_query = VectorizableTextQuery(
        text=query,
        kind="text",
        k_nearest_neighbors=10,
        fields="content_vector"
    )
    search_results = search_client.search(
        search_text=query,
        query_type="full",
        search_fields=["metadata_storage_name", "chunk", "content"],
        search_mode="all",
        top=2,
        select="chunk, metadata_storage_name",
        filter=filter_expr,
        vector_queries=[vector_query]
    )

    return file_type, search_results

def store_message(user_id, role, content, topic="default"):
    item = {
        "session_id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,  # "user" or "assistant"
        "content": content,
        "timestamp": datetime.datetime.now(),
        "topic": topic
    }
    container.create_item(body=item)

def get_user_chat_history(user_id, topic="default"):
    query = f"SELECT * FROM c WHERE c.user_id = @user_id AND c.topic = @topic ORDER BY c.timestamp"
    params = [
        {"name": "@user_id", "value": user_id},
        {"name": "@topic", "value": topic}
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return [(item['role'], item['content']) for item in items]
    