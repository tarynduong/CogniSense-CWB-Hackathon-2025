const API_ENDPOINT =
  import.meta.env.AZURE_CHAT_OPENAI_API_KEY || "http://127.0.0.1:5000/bot";

export const LOGIN_ENDPOINT = `${API_ENDPOINT}/login`;
export const REGISTER_ENDPOINT = `${API_ENDPOINT}/register`;
export const UPLOAD_FILE_ENDPOINT = `${API_ENDPOINT}/ingest_file`;
export const UPLOAD_URL_ENDPOINT = `${API_ENDPOINT}/ingest_url`;
export const CHAT_ENDPOINT = `${API_ENDPOINT}/chat`;
export const QUIZ_ENDPOINT = `${API_ENDPOINT}/quiz`;
export const FLASHCARD_ENDPOINT = `${API_ENDPOINT}/flashcard`;
