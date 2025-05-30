from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from dotenv import load_dotenv
import uuid
from datetime import datetime as dt
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash

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
user_container = db.get_container_client(container="Users")
chat_container = db.get_container_client(container="Messages")


def upload_to_blob(container_name, filename, file_content):
    container_client = blob_service_client.get_container_client(f"sample-data/{container_name}")
    source_blob_client = container_client.get_blob_client(filename)
    source_blob_client.upload_blob(file_content, overwrite=True)
    return f"Uploaded to sample-data/{container_name}/{filename}"


def add_user(username, password):
    result = user_container.query_items(
            query="SELECT * FROM Users u WHERE u.UserName = @username",
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        )
    existing_users = [item for item in result]
    if existing_users:
        return "Username already exists", existing_users[0]["id"]

    user_item = {
        "id": str(uuid.uuid4()),
        "UserName": username,
        "Password": generate_password_hash(password)
    }
    user_container.create_item(user_item)

    return "User registered successfully", user_item["id"]

def check_user(username, password):
    result = user_container.query_items(
            query="SELECT * FROM Users u WHERE u.UserName = @username",
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        )
    users = [item for item in result]
    if not users or not check_password_hash(users[0]["Password"], password):
        return "Invalid credentials", None
    else:
        return "Login successful", users[0]["id"]

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


def store_message(user_id, role, content, topic):
    chat_item = {
        "id": str(uuid.uuid4()),
        "UserId": user_id,
        "SessionId": str(int(dt.now().timestamp())),
        "Role": role,  # "user" or "assistant"
        "Topic": topic,
        "Content": content,
        "Timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    chat_container.create_item(chat_item)


def get_user_chat_history(user_id, topic):
    query = f"SELECT * FROM Messages c WHERE c.UserId = @user_id AND c.Topic like '%{topic}%' ORDER BY c.Timestamp"
    params=[{"name": "@user_id", "value": user_id}]
    items = list(chat_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return [(item['Role'], item['Content']) for item in items]


def get_past_topic(user_id):
    query = f"SELECT c.Topic FROM Messages c WHERE c.UserId = @user_id ORDER BY c.Timestamp"
    params = [{"name": "@user_id", "value": user_id}]
    items = list(chat_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return [item['Topic'] for item in items]
