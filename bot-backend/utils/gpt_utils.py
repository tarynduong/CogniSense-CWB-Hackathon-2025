from nltk.classify.textcat import re
from openai import AzureOpenAI
import os
import json
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from .azure_utils import get_past_topic, search_content
from .knowledge_utils import preprocess_user_query

load_dotenv()

logger = logging.getLogger("cognisense.agent")
logging.basicConfig(level=logging.INFO)

AZURE_EMBEDDING_OPENAI_API_KEY = os.getenv("AZURE_EMBEDDING_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL")
AZURE_CHAT_MODEL = os.getenv("AZURE_CHAT_MODEL") or ""
AZURE_CHAT_OPENAI_API_KEY = os.getenv("AZURE_CHAT_OPENAI_API_KEY")
# AZURE_CHAT_ENDPOINT = os.getenv("AZURE_CHAT_ENDPOINT")

openai_embedding_client = AzureOpenAI(
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_EMBEDDING_OPENAI_API_KEY
)

openai_chat_client = AzureOpenAI(
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_CHAT_OPENAI_API_KEY
)


def get_embedding(text):
    embedding_response = openai_embedding_client.embeddings.create(
        model=AZURE_EMBEDDING_MODEL,
        input=[text]
    )
    return embedding_response.data[0].embedding


chat_system_prompt = """
    [ROLE]
        - You are CogniSense, an intelligent, thoughtful Question-Answering assistant.
        - You behave like a knowledgeable teammate who collaborates, explains, reasons, and helps business users manage and make sense of vast amount of content they consume, such as documents, web links, and personal notes.
        - You can reflect, ask clarifying questions, and use retrieved information to guide conversations.

    [TASK]
    Your job is to:
        - Understand the user's intent, keywords, and topic, both implicitly and explicitly.
        - Use only the retrieved content below to give accurate, context-aware, and well-organized responses.
        - Apply reasoning and multi-step thinking to synthesize insights from the retrieved information.
        - Maintain conversation context across turns, and know when to ask to clarifying questions or user already shifts topics.

    [INSTRUCTIONS]
        1. Always base your answers on the retrieved documents provided below.
        2. When needed, reason step-by-step using internal thinking (Chain of Thought).
        3. If the answer is not directly in the documents, say so honestly and suggest what to ask next.
        4. Keep answers conversational, structured, and helpful — not robotic.
        5. If the user changes the topic, recognize the shift and reset context appropriately.
        6. Avoid hallucination. Never make up facts. Only infer what's logically supported by documents or past dialogue.

    [EXAMPLE INPUT]
    User: "Can you explain how agentic RAG works in practical applications?"

    [RETRIEVED DOCUMENTS]
    1. "Agentic RAG combines retrieval-augmented generation with planning, memory, and reasoning steps to act autonomously on user queries..."
    2. "In practical terms, it enables systems to break down tasks, plan answers, and remember context like a teammate..."
    3. "This differs from classic RAG which only retrieves chunks and passes them to the LLM without persistent memory or reasoning layers."

    [THINKING]
    - Step 1: Understand the user is asking for practical uses, not just a definition.
    - Step 2: Combine insights from all documents.
    - Step 3: Summarize with examples.

    [RESPONSE]
    Agentic RAG works by combining retrieval with memory and planning. For example, if a user asks a multi-step question like how to implement a knowledge bot, the system not only retrieves relevant docs but also breaks down the problem, tracks previous answers, and adapts. It’s like working with a colleague who not only finds information but also helps you act on it.

    [OUTPUT FORMAT]
    Always respond in thoughtful paragraphs. Use bullet points or numbered lists if explaining steps. Include the file name of the retrieved documents when citing information.
"""

def generate_answer(query, docs):
    messages = [
        {"role": "system", "content": chat_system_prompt},
        {
            "role": "user",
            "content": (
                f"Question:\n{query}\n\n"
                f"[RETRIEVED DOCUMENTS]\n{docs}"
            ),
        },
    ]

    response = openai_chat_client.chat.completions.create(
        model=AZURE_CHAT_MODEL,
        messages=messages
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Agentic chat
# ---------------------------------------------------------------------------

SEARCH_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the user's uploaded documents, notes, and web links for "
                "information needed to answer a knowledge question. Call this "
                "whenever the user asks about the content of their materials. Do "
                "NOT call it for greetings, thanks, or general small talk."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "A clean, concept-focused search query that captures "
                            "what to look for. Strip instruction words like "
                            "'extract', 'summarize', or 'prove this idea' and keep "
                            "the underlying topic/keywords. Resolve references to "
                            "earlier turns (e.g. 'that', 'it') into explicit terms."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    }
]

agent_behavior = """
    [AGENT BEHAVIOR]
    - You have a tool `search_knowledge_base`. Decide for yourself whether the user's message needs it.
    - For greetings or small talk, answer directly and briefly WITHOUT calling the tool.
    - For questions about the user's materials, call the tool with a clean, concept-focused query, then answer using the retrieved documents.
    - Use the prior conversation turns to resolve follow-up questions.
"""

agent_system_prompt = chat_system_prompt + agent_behavior


def _history_to_messages(history):
    """Convert [(role, content), ...] into chat message dicts the model accepts."""
    msgs = []
    for role, content in history or []:
        role = "assistant" if role == "assistant" else "user"
        msgs.append({"role": role, "content": content})
    return msgs


def _run_search(query):
    """Run the index search and format sources + chunks. Returns (sources, docs_text)."""
    file_type, search_results = search_content(query)
    sources = []
    chunks = []
    for doc in search_results:
        name = doc.get("metadata_storage_name")
        if name and name not in sources:
            sources.append(name)
        chunk = doc.get("chunk")
        if chunk and chunk not in chunks:
            chunks.append(chunk)
    return sources, "\n\n".join(chunks)


def agentic_chat(user_message, history=None):
    """
    Agentic chat turn.

    Returns a dict:
      {
        "answer": str,
        "used_search": bool,        # did the agent decide to search?
        "search_query": str | None, # the query actually used
        "query_source": "agent" | "fallback" | "none",
        "sources": [filenames],
      }

    The model decides whether to call the search tool. If it does, we run the
    search and let it answer from the results. If the tool call is malformed we
    fall back to preprocess_user_query() + raw message so retrieval still works.
    """
    result = {
        "answer": "",
        "used_search": False,
        "search_query": None,
        "query_source": "none",
        "sources": [],
    }

    messages = [{"role": "system", "content": agent_system_prompt}]
    messages.extend(_history_to_messages(history))
    messages.append({"role": "user", "content": user_message})

    # Turn 1: let the agent decide whether to search
    try:
        first = openai_chat_client.chat.completions.create(
            model=AZURE_CHAT_MODEL,
            messages=messages,
            tools=SEARCH_TOOL,
            tool_choice="auto",
            reasoning_effort="low",
        )
    except Exception as e:
        logger.exception("agentic_chat: initial model call failed")
        raise

    choice = first.choices[0].message
    tool_calls = getattr(choice, "tool_calls", None)

    # No tool call => smalltalk / direct answer
    if not tool_calls:
        logger.info("agentic_chat: NO SEARCH (direct answer / smalltalk)")
        result["answer"] = choice.content or ""
        return result

    # Agent chose to search
    tool_call = tool_calls[0]
    search_query = None
    query_source = "agent"
    try:
        args = json.loads(tool_call.function.arguments or "{}")
        search_query = (args.get("query") or "").strip()
    except (ValueError, TypeError):
        search_query = None

    if not search_query:
        # Agent asked to search but gave an unusable query -> fallback.
        search_query = preprocess_user_query(user_message)
        query_source = "fallback"

    logger.info(
        "agentic_chat: SEARCH query_source=%s query=%r",
        query_source, search_query,
    )

    try:
        sources, docs_text = _run_search(search_query)
    except Exception:
        logger.exception("agentic_chat: search_content failed; retrying with fallback query")
        search_query = preprocess_user_query(user_message)
        query_source = "fallback"
        logger.info("agentic_chat: SEARCH (retry) query_source=%s query=%r", query_source, search_query)
        sources, docs_text = _run_search(search_query)

    result["used_search"] = True
    result["search_query"] = search_query
    result["query_source"] = query_source
    result["sources"] = sources

    # Turn 2: give the agent the tool result and let it answer ---
    messages.append({
        "role": "assistant",
        "tool_calls": [{
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }],
    })
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": f"[RETRIEVED DOCUMENTS]\n{docs_text}" if docs_text else "No relevant documents were found.",
    })

    second = openai_chat_client.chat.completions.create(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        reasoning_effort="low",
    )
    result["answer"] = second.choices[0].message.content or ""
    return result


topic_system_prompt = """
    [ROLE]
        - You are a smart assistant that classifies a user's message into a short topic name.

    [TASK]
    Your job is to:
        - Return a topic of maximum 5 words that summarizes the main subject or intent.

    [EXAMPLES]
    User: How does vector search work in AI?
    Topic: Vector Search

    Input: Can you generate a quiz about RAG?
    Topic: Retrieval-Augmented Generation
"""

def detect_topic(user_message: str) -> str:
    # Include in-memory caching to save tokens and reduce API calls for repeated queries
    topic_cache = {}
    if user_message in topic_cache:
        return topic_cache[user_message]

    response = openai_chat_client.chat.completions.create(
        model=AZURE_CHAT_MODEL,
        max_completion_tokens=256,
        reasoning_effort="minimal",
        messages=[
            {"role": "system", "content": topic_system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    content = response.choices[0].message.content
    topic = content.strip().lower() if content else "general"
    topic_cache[user_message] = topic
    return topic


class QuizAnswer(BaseModel):
    answer: str
    is_correct_answer: bool

class Quiz(BaseModel):
    question: str
    answers: list[QuizAnswer]

class Quizzes(BaseModel):
    data: list[Quiz]

def generate_quiz_from_history(history, topic, user_id):
    resp_message = ""
    if topic == "":
        resp_message += "Since no topic was specified, we will use the default topic 'GenAI' to generate flashcards.\n"
    if len(history) == 0:
        past_topics = get_past_topic(user_id)
        if len(past_topics) == 0:
            resp_message += "No past topics found.\n"
        else:
            resp_message += f"No history found for the recorded topic, please use one of the following past topics: {', '.join(past_topics)}\n"
        return resp_message, dict()

    messages = [
        {"role": "system", "content": "You are a learning assistant that turns past dialogue into study material."},
        {"role": "user", "content": "Here is a past conversation between me and an AI:\n\n" +
         "\n".join([f"{role.capitalize()}: {text}" for role, text in history]) +
         "\n\nCreate 5 quiz questions to help me review this material."}
    ]

    response = openai_chat_client.beta.chat.completions.parse(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        response_format=Quizzes
    )
    message = response.choices[0].message

    if message.refusal:
        raise ValueError("Refusal to generate quizzes: " + message.refusal)

    return resp_message, message.parsed.model_dump() if message.parsed else dict()


class Flashcard(BaseModel):
    question: str
    answer: str

class Flashcards(BaseModel):
    data: list[Flashcard]
    explain: str

def generate_flashcard_from_history(history, topic, user_id):
    resp_message = ""
    if topic == "":
        resp_message += "Since no topic was specified, we will use the default topic 'GenAI' to generate flashcards.\n"
    if len(history) == 0:
        past_topics = get_past_topic(user_id)
        if len(past_topics) == 0:
            resp_message += "No past topics found.\n"
        else:
            resp_message += f"No history found for the recorded topic, please use one of the following past topics: {', '.join(past_topics)}\n"
        return resp_message, dict()

    messages = [
        {"role": "system", "content": "You are a learning assistant that turns past dialogue into study material."},
        {"role": "user", "content": "Here is a past conversation between me and an AI:\n\n" +
            "\n".join([f"{role.capitalize()}: {text}" for role, text in history]) +
            "\n\nCreate 5 flashcards to help me review this material."}
    ]

    response = openai_chat_client.beta.chat.completions.parse(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        response_format=Flashcards
    )

    message = response.choices[0].message

    if message.refusal:
        raise ValueError("Refusal to generate flashcards: " + message.refusal)

    return resp_message, message.parsed.model_dump() if message.parsed else dict()
