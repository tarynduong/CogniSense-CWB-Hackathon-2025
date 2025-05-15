
from flask import Blueprint, jsonify, request
from utils.azure_utils import upload_to_blob, get_all_text_blobs
from utils.knowledge_utils import extract_text_from_url
from utils.gpt_utils import chat_with_docs, generate_flashcards

bot_bp = Blueprint("bot_bp", __name__)

@bot_bp.route("/ingest_url", methods=["POST"])
def ingest_url():
    if "url" in request.form:
        url = request.form["url"]
        text = extract_text_from_url(url)
        filename = url.replace("https://", "").split("/")[-1].replace("-", "_") + ".txt"
    else:
        return jsonify({"error": "No URL provided"}), 400
    
    upload_to_blob("blogs", filename, text)
    
    return jsonify({"message": "Uploaded successfully", "filename": filename}), 201

@bot_bp.route("/ingest_file", methods=["POST"])
def ingest_file():
    if request.form["type"] == "":
        return jsonify({"error": "No file type is specified."}), 400
    
    file_type = request.form.get("type")
    file = request.files["file"]
    filename = file.filename
    file_content = file.read()

    upload_to_blob(file_type, filename, file_content)
    
    return jsonify({"message": "Files uploaded", "filename": filename}), 201

@bot_bp.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    all_docs = get_all_text_blobs()  # Load all text from Azure
    reply = chat_with_docs(user_message, all_docs)
    return jsonify({"reply": reply})

@bot_bp.route("/flashcards", methods=["POST"])
def flashcards():
    topic = request.json.get("keywords")
    flashcards = generate_flashcards(topic)
    return jsonify({"flashcards": flashcards})

@bot_bp.route("/quizzes", methods=["POST"])
def quizzes():
    topic = request.json.get("keywords")
    quizzes = generate_flashcards(topic)
    return jsonify({"quizzes": quizzes})