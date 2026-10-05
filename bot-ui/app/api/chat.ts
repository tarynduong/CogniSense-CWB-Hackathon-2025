import { CHAT_ENDPOINT, CHAT_STREAM_ENDPOINT } from "@/api/constants";
import { getAccessToken } from "@/features/auth/auth";
import axios, { AxiosError } from "axios";

export type ChatStage = "understanding" | "searching" | "writing";

export type ChatStreamResult = {
  topic?: string;
  answer?: string;
  usedSearch?: boolean;
  searchQuery?: string;
  querySource?: string;
  error?: string;
};

/**
 * Streams a chat request, invoking `onStage` as the backend reports each
 * pipeline stage, and resolving with the final answer once complete.
 */
export async function chatWithBotStream(
  query: string,
  onStage: (stage: ChatStage, detail: { query?: string }) => void
): Promise<ChatStreamResult> {
  const accessToken = getAccessToken();

  let response: Response;
  try {
    response = await fetch(CHAT_STREAM_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ query }),
    });
  } catch (err) {
    return {
      error:
        err instanceof Error
          ? err.message
          : "Unable to reach the server. Please try again.",
    };
  }

  if (!response.ok || !response.body) {
    let details: string | undefined;
    try {
      const data = await response.json();
      details = data?.details || data?.message || data?.error;
    } catch {
      /* response wasn't JSON */
    }
    return {
      error: details || `Request failed with status ${response.status}`,
    };
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const result: ChatStreamResult = {};

  const handleEvent = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    let event: any;
    try {
      event = JSON.parse(trimmed);
    } catch {
      return; // ignore malformed line
    }

    if (event.type === "stage") {
      onStage(event.stage as ChatStage, { query: event.query });
    } else if (event.type === "done") {
      result.answer = event.answer;
      result.topic = event.topic;
      result.usedSearch = event.used_search;
      result.searchQuery = event.search_query;
      result.querySource = event.query_source;
    } else if (event.type === "error") {
      result.error = event.details || "Chat failed.";
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex: number;
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);
      handleEvent(line);
    }
  }
  // Flush any remaining buffered content.
  if (buffer.trim()) handleEvent(buffer);

  if (!result.answer && !result.error) {
    result.error = "No response received from the server.";
  }
  return result;
}

export async function chatWithBot(query: string): Promise<{
  topic: string | undefined;
  answer: string | undefined;
  error: string | undefined;
}> {
  const accessToken = getAccessToken();

  const body = {
    query,
  };

  return await axios
    .post<{
      topic: string;
      answer: string;
    }>(CHAT_ENDPOINT, body, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    })
    .then((response) => {
      const { topic, answer } = response.data;
      return {
        topic,
        answer,
        error: undefined,
      };
    })
    .catch((error: AxiosError) => {
      const data = error.response?.data as
        | { error?: string; details?: string; message?: string }
        | undefined;
      return {
        topic: undefined,
        answer: undefined,
        error:
          data?.details ||
          data?.message ||
          data?.error ||
          error.message ||
          "Unable to reach the server. Please try again.",
      };
    });
}
