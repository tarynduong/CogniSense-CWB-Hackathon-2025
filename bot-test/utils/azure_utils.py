import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv(override=True)

# CREDENTIALS
CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)

def upload_to_blob(container_name, filename, file_content):
    container_client = blob_service_client.get_container_client(container_name)
    source_blob_client = container_client.get_blob_client(filename)
    source_blob_client.upload_blob(file_content, overwrite=True)
    return f"Uploaded to {container_name}/{filename}"
