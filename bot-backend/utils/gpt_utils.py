import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_docs(user_message, docs_text):
    prompt = f"""
You are a helpful assistant. Answer the user's question based on the knowledge below.

Knowledge:
{docs_text[:3000]}  # Truncated for safety

Question: {user_message}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def generate_flashcards(topic):
    prompt = f"""
Generate 5 flashcards on the topic: {topic}.
Provide them as JSON with keys "question" and "answer".
"""
    response = openai.ChatCompletion.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
