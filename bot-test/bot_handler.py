from flask import Blueprint, jsonify, request
from utils.azure_utils import upload_to_blob
from utils.knowledge_utils import extract_text_from_url
# from utils.data_utils import APIResponse, APIResponseEncoder

bot_bp = Blueprint("bot_bp", __name__)

@bot_bp.route("/ingest_url", methods=["POST"])
def ingest_url():
    if "url" in request.form:
        url = request.form["url"]
        text = extract_text_from_url(url)
        filename = url.replace("https://", "").split("/")[-1].replace("-", "_") + ".txt"
    else:
        return jsonify({"error": "No URL provided"}), 400
    
    message = upload_to_blob("blogs", filename, text)
    
    return jsonify({"message": message, "filename": filename}), 201

@bot_bp.route("/ingest_file", methods=["POST"])
def ingest_file():
    if request.form["type"] == "":
        return jsonify({"error": "No file type is specified."}), 400
    
    file_type = request.form.get("type")
    file = request.files["file"]
    filename = file.filename
    file_content = file.read()

    message = upload_to_blob(file_type, filename, file_content)
    
    return jsonify({"message": message, "filename": filename}), 201