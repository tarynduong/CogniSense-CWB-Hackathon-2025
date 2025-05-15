import os
from azure.storage.blob import BlobServiceClient
from azure-cosmos import CosmosClient
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(override=True)

# CREDENTIALS
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
COSMOS_DB_CONNECTION_STRING = os.getenv("COSMOS_DB_CONNECTION_STRING")
COSMOS_DB_DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME")
COSMOS_DB_CONTAINER_NAME = os.getenv("COSMOS_DB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
cosmos_client = CosmosClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
database = cosmos_client.get_database_client(COSMOS_DB_DATABASE_NAME)
container = database.get_container_client(COSMOS_DB_CONTAINER_NAME)
openai_client = AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_key=OPENAI_KEY, api_version=OPENAI_API_VERSION)

# Add embeddings for properties from request to CosmosDB
data = request.get_json()
properties = data.get('properties')
for property in properties:
    text = data.get(property)
    if text:
        embedding = generate_embeddings(openai_client, text)
        data[f'{property}_embedding'] = embedding.to_list()
container.upsert_item(data)

def generate_embeddings(openai_client, text, dim=256):
    response = openai_client.embeddings.create(input=text, model='text-3-large', dimensions=dim)
    embeddings = response.model_dump()
    return embeddings['data'][0]['embedding']

def upload_to_blob(container_name, filename, file_content):
    container_client = blob_service_client.get_container_client(container_name)
    source_blob_client = container_client.get_blob_client(filename)
    source_blob_client.upload_blob(file_content, overwrite=True)
    return f"Uploaded to {container_name}/{filename}"

def get_all_text_blobs():
    text = ""
    for container_name in ["blogs", "notes", "documents"]:
        container = blob_service_client.get_container_client(container_name)
        blobs = container.list_blobs()
        for blob in blobs:
            blob_data = container.download_blob(blob).readall().decode()
            text += f"\n{blob_data}"
    return text
