import { FLASHCARD_ENDPOINT, QUIZ_ENDPOINT } from "@/api/constants";
import { getAccessToken } from "@/features/auth/auth";
import type { Flashcard, Quiz } from "@/features/quiz/types";
import { shuffle } from "@/lib/utils";
import axios, { AxiosError } from "axios";

export async function getQuestions(topic: string | undefined): Promise<{
  flashcards: Flashcard[];
  message: string;
}> {
  const accessToken = getAccessToken();

  const body = {
    topic,
  };

  return await axios
    .post<{
      flashcard: {
        data: {
          question: string;
          answer: string;
        }[];
        explain: string;
      };
      message: string;
    }>(FLASHCARD_ENDPOINT, body, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    })
    .then((response) => {
      console.log(response.data);
      const {
        flashcard: { data },
        message,
      } = response.data;
      return {
        flashcards: data || [],
        message: message,
      };
    })
    .catch((error: AxiosError) => {
      throw Error(error.message);
    });
}

export async function getQuizzes(topic: string | undefined): Promise<{
  quizzes: Quiz[];
  message: string;
}> {
  const accessToken = getAccessToken();

  const body = {
    topic,
  };

  return await axios
    .post<{
      quiz: {
        data: {
          question: string;
          answers: {
            answer: string;
            is_correct_answer: boolean;
          }[];
        }[];
      };
      message: string;
    }>(QUIZ_ENDPOINT, body, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    })
    .then((response) => {
      console.log(response.data);
      const {
        quiz: { data },
        message,
      } = response.data;

      return {
        quizzes: (data || []).map((quiz) => ({
          question: quiz.question,
          answers: shuffle(
            quiz.answers.map((answer) => ({
              answer: answer.answer,
              isCorrectAnswer: answer.is_correct_answer,
            }))
          ),
        })),
        message: message,
      };
    })
    .catch((error: AxiosError) => {
      throw Error(error.message);
    });
}
