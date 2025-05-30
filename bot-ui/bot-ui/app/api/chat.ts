import { CHAT_ENDPOINT } from "@/api/constants";
import { getAccessToken } from "@/features/auth/auth";
import axios, { AxiosError } from "axios";

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
      return {
        topic: undefined,
        answer: undefined,
        error:
          (error.response?.data as { error: string; details: string })
            .details || error.message,
      };
    });
}
