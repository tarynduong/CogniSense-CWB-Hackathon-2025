from flask import Blueprint, jsonify, request
from utils.gpt_utils import generate_answer, detect_topic, generate_quiz_from_history, generate_flashcard_from_history
from utils.azure_utils import add_user, check_user, upload_to_blob, search_content, store_message, get_user_chat_history
from utils.knowledge_utils import decode_token, extract_text_from_url, preprocess_user_query, encode_token


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

    return jsonify({"message": message, "filename": filename}), 200


@bot_bp.route("/ingest_file", methods=["POST"])
def ingest_file():
    if request.form["type"] == "":
        return jsonify({"error": "No file type is specified."}), 400

    file_type = request.form.get("type")
    file = request.files["file"]
    filename = file.filename
    file_content = file.read()

    message = upload_to_blob(file_type, filename, file_content)

    return jsonify({"message": message, "filename": filename}), 200


@bot_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    message, user_id = add_user(username, password)
    token = encode_token(user_id)

    return jsonify({"message": message, "access_token": token}), 200


@bot_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    message, user_id = check_user(username, password)
    if user_id is None:
        return jsonify({"message": message}), 401
    token = encode_token(user_id)

    return jsonify({"message": message, "access_token": token}), 200


@bot_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    header = request.headers.get("Authorization")
    token = header[7:] if header else None # remove Bearer
    result, status_code = decode_token(token)
    if status_code != 200:
        return jsonify({"message": result}), status_code

    user_id = result['user_id']
    user_query = data.get("query")
    topic = detect_topic(user_query)
    store_message(user_id, "user", user_query, topic)
    expanded_query = preprocess_user_query(user_query)
    try:
        file_type, search_results = search_content(expanded_query)
        source = []
        match_chunk = []
        for doc in search_results:
            if "metadata_storage_name" in doc and doc["metadata_storage_name"] not in source:
                source.append(doc["metadata_storage_name"])
            if "chunk" in doc and doc["chunk"] not in match_chunk:
                match_chunk.append(doc["chunk"])

        fallback_message = (
            f"I couldn't find any relevant results in **{file_type.upper()}** files, "
            f"but here are some matches from other file types."
        ) if file_type is not None else None

        docs_text = "\n\n".join(match_chunk)
        source_str = ", ".join(source)
        answer = f"Source: {source_str}\n\n" + generate_answer(expanded_query, docs_text)
        if fallback_message:
            answer = fallback_message + answer
        store_message(user_id, "assistant", answer, topic)

        return jsonify({"topic": topic, "answer": answer})
    except Exception as e:
        return jsonify({"error": "Search failed", "details": str(e)}), 500


@bot_bp.route("/quiz", methods=["POST"])
def quiz():
    data = request.get_json()
    header = request.headers.get("Authorization")
    token = header[7:] if header else None # remove Bearer
    result, status_code = decode_token(token)
    if status_code != 200:
        return jsonify({"message": result}), status_code

    user_id = result['user_id']
    topic = data.get("topic")

    history = get_user_chat_history(user_id, topic if topic else "GenAI") # Use GenAI as default topic
    message, quiz = generate_quiz_from_history(history, topic, user_id)

    return jsonify({"message": message, "quiz": quiz})


@bot_bp.route("/flashcard", methods=["POST"])
def flashcard():
    data = request.get_json()
    header = request.headers.get("Authorization")
    token = header[7:] if header else None # remove Bearer
    result, status_code = decode_token(token)
    if status_code != 200:
        return jsonify({"message": result}), status_code

    user_id = result['user_id']
    topic = data.get("topic")

    history = get_user_chat_history(user_id, topic if topic else "GenAI") # Use GenAI as default topic
    message, flashcard = generate_flashcard_from_history(history, topic, user_id)

    return jsonify({"flashcard": flashcard, "message": message})
