import json
import queue
import threading
from flask import Blueprint, jsonify, request, Response, stream_with_context
from utils.gpt_utils import generate_answer, detect_topic, generate_quiz_from_history, generate_flashcard_from_history, agentic_chat
from utils.azure_utils import add_user, check_user, upload_to_blob, search_content, store_message, get_user_chat_history, get_recent_messages
from utils.knowledge_utils import decode_token, extract_text_from_url, preprocess_user_query, encode_token, UrlFetchError


bot_bp = Blueprint("bot_bp", __name__)


@bot_bp.route("/ingest_url", methods=["POST"])
def ingest_url():
    if "url" not in request.form or not request.form["url"].strip():
        return jsonify({"error": "No URL provided"}), 400

    url = request.form["url"].strip()

    # Map each failure reason to a user-facing notification and HTTP status.
    reason_messages = {
        "blocked": ("This link is blocked for scraping, so its content can't be imported. Try a different source.", 422),
        "timeout": ("The site took too long to respond. Please try again or use another link.", 504),
        "unreachable": ("Couldn't reach that link. Check the URL and try again.", 400),
        "http_error": ("The site returned an error and couldn't be read.", 422),
        "not_webpage": ("That link isn't a readable web page. For PDFs or documents, use file upload instead.", 415),
        "no_content": ("No readable text was found — the page may be JavaScript-rendered. Try a different link.", 422),
    }

    try:
        text = extract_text_from_url(url)
    except UrlFetchError as e:
        message, http_status = reason_messages.get(
            e.reason, ("Could not fetch or read that URL.", 400)
        )
        return jsonify({
            "error": message,
            "reason": e.reason,
            "details": e.message,
        }), http_status
    except Exception as e:
        return jsonify({
            "error": "Could not fetch or read that URL.",
            "reason": "unknown",
            "details": str(e),
        }), 400

    # Build a .txt filename from the last meaningful path segment.
    stripped = url.replace("https://", "").replace("http://", "").rstrip("/")
    last_segment = stripped.split("/")[-1] if "/" in stripped else stripped
    filename = (last_segment or "webpage") + ".txt"

    try:
        message = upload_to_blob("blogs", filename, text)
    except Exception as e:
        return jsonify({
            "error": "We read the link but couldn't save it. Please try again in a moment.",
            "reason": "storage_error",
            "details": str(e),
        }), 500

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


@bot_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    Streaming version of /chat. Emits newline-delimited JSON (NDJSON) events so
    the UI can show real pipeline stages:

      {"type": "stage", "stage": "understanding"}
      {"type": "stage", "stage": "searching", "query": "..."}
      {"type": "stage", "stage": "writing"}
      {"type": "done", "answer": "...", "topic": "...", "used_search": true,
       "search_query": "...", "query_source": "agent"}
      {"type": "error", "details": "..."}
    """
    data = request.get_json()
    header = request.headers.get("Authorization")
    token = header[7:] if header else None  # remove Bearer
    result, status_code = decode_token(token)
    if status_code != 200:
        return jsonify({"message": result}), status_code

    user_id = result["user_id"]
    user_query = data.get("query")
    history = get_recent_messages(user_id, limit=6)

    events = queue.Queue()

    def on_stage(stage, detail):
        payload = {"type": "stage", "stage": stage}
        if detail:
            payload.update(detail)
        events.put(payload)

    def worker():
        try:
            chat_result = agentic_chat(user_query, history=history, on_stage=on_stage)

            topic = detect_topic(user_query) if chat_result["used_search"] else "general"
            store_message(user_id, "user", user_query, topic)

            answer = chat_result["answer"]
            if chat_result["used_search"] and chat_result["sources"]:
                source_str = ", ".join(chat_result["sources"])
                answer = f"Source: {source_str}\n\n{answer}"

            store_message(user_id, "assistant", answer, topic)

            events.put({
                "type": "done",
                "answer": answer,
                "topic": topic,
                "used_search": chat_result["used_search"],
                "search_query": chat_result["search_query"],
                "query_source": chat_result["query_source"],
            })
        except Exception as e:
            events.put({"type": "error", "details": str(e)})
        finally:
            events.put(None)  # sentinel: stream complete

    def generate():
        threading.Thread(target=worker, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                break
            yield json.dumps(event) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
