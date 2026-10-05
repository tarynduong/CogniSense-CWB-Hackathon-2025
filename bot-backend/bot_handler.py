from flask import Blueprint, jsonify, request
from utils.gpt_utils import generate_answer, detect_topic, generate_quiz_from_history, generate_flashcard_from_history, agentic_chat
from utils.azure_utils import add_user, check_user, upload_to_blob, search_content, store_message, get_user_chat_history, get_recent_messages
from utils.knowledge_utils import decode_token, extract_text_from_url, preprocess_user_query, encode_token


bot_bp = Blueprint("bot_bp", __name__)


@bot_bp.route("/ingest_url", methods=["POST"])
def ingest_url():
    if "url" in request.form:
        url = request.form["url"]
        text = extract_text_from_url(url)
        filename = url.replace("https://", "").split("/")[-2] + ".txt" if url.replace("https://", "").split("/")[-1] == "" else url.replace("https://", "").split("/")[-1] + ".txt"
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

    # Short-term memory: last 6 messages so the agent can resolve follow-up questions.
    history = get_recent_messages(user_id, limit=6)

    try:
        chat_result = agentic_chat(user_query, history=history)

        # Only compute a topic when the agent actually treated this as a
        # knowledge question. For greetings/smalltalk we skip the extra model
        # call entirely to keep responses fast.
        topic = detect_topic(user_query) if chat_result["used_search"] else "general"

        store_message(user_id, "user", user_query, topic)

        answer = chat_result["answer"]
        if chat_result["used_search"] and chat_result["sources"]:
            source_str = ", ".join(chat_result["sources"])
            answer = f"Source: {source_str}\n\n{answer}"

        store_message(user_id, "assistant", answer, topic)

        return jsonify({
            "topic": topic,
            "answer": answer,
            # Tracking info so you can see what the agent did:
            "used_search": chat_result["used_search"],
            "search_query": chat_result["search_query"],
            "query_source": chat_result["query_source"],  # "agent" | "fallback" | "none"
        })
    except Exception as e:
        return jsonify({"error": "Chat failed", "details": str(e)}), 500


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

    history = get_user_chat_history(user_id, topic)
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

    history = get_user_chat_history(user_id, topic)
    message, flashcard = generate_flashcard_from_history(history, topic, user_id)

    return jsonify({"flashcard": flashcard, "message": message})
