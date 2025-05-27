from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from .azure_utils import get_past_topic

load_dotenv()

AZURE_EMBEDDING_OPENAI_API_KEY = os.getenv("AZURE_EMBEDDING_OPENAI_API_KEY")
AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL")
AZURE_CHAT_MODEL = os.getenv("AZURE_CHAT_MODEL") or ""
AZURE_CHAT_OPENAI_API_KEY = os.getenv("AZURE_CHAT_OPENAI_API_KEY")
AZURE_CHAT_ENDPOINT = os.getenv("AZURE_CHAT_ENDPOINT")

openai_embedding_client = AzureOpenAI(
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_SERVICE,
    api_key=AZURE_EMBEDDING_OPENAI_API_KEY
)

openai_chat_client = AzureOpenAI(
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_CHAT_ENDPOINT,
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
        {"role": "user", "content": query},
        {"role": "function", "name": "search_docs", "content": f"Retrieved documents:\n{docs}"}
    ]

    response = openai_chat_client.chat.completions.create(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content


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
        temperature=0,
        max_tokens=10,
        messages=[
            {"role": "system", "content": topic_system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    topic = response.choices[0].message.content.strip().lower()
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
    messages = [
        {"role": "system", "content": "You are a learning assistant that turns past dialogue into study material."},
        {"role": "user", "content": "Here is a past conversation between me and an AI:\n\n" +
         "\n".join([f"{role.capitalize()}: {text}" for role, text in history]) +
         "\n\nCreate 5 quiz questions to help me review this material."}
    ]

    response = openai_chat_client.beta.chat.completions.parse(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        temperature=0.5,
        response_format=Quizzes
    )
    message = response.choices[0].message

    if message.refusal:
        raise ValueError("Refusal to generate quizzes: " + message.refusal)

    return message.parsed.model_dump() if message.parsed else dict()


class Flashcard(BaseModel):
    question: str
    answer: str

class Flashcards(BaseModel):
    data: list[Flashcard]
    explain: str

def generate_flashcard_from_history(history, topic, user_id):
    if topic == "":
        messages = [
            {"role": "system", "content": "You tell user that topic is not given so default topic which is Gen AI is used instead to generate flashcards"},
            {"role": "user", "content": "Create 5 flashcards to help me review this material."}
        ]
    past_topics = ', '.join(get_past_topic(user_id))
    if len(history) == 0:
        messages = [
            {"role": "system", "content": f"You are CogniSense, a personal assistant. Tell user that the topic they are looking for has not been discussed with you yet. List of topics user consumed in the past includes {past_topics}. Request them to choose either one of these topics and stop just that. Don't create anything user wants."},
            {"role": "user", "content": "Create 5 flashcards to help me review this material."}
        ]
    messages = [
        {"role": "system", "content": "You are a learning assistant that turns past dialogue into study material."},
        {"role": "user", "content": "Here is a past conversation between me and an AI:\n\n" +
         "\n".join([f"{role.capitalize()}: {text}" for role, text in history]) +
         "\n\nCreate 5 flashcards to help me review this material."}
    ]

    response = openai_chat_client.beta.chat.completions.parse(
        model=AZURE_CHAT_MODEL,
        messages=messages,
        temperature=0.5,
        response_format=Flashcards
    )

    message = response.choices[0].message

    if message.refusal:
        raise ValueError("Refusal to generate flashcards: " + message.refusal)

    return message.parsed.model_dump() if message.parsed else dict()
