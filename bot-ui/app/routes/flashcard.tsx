import { Flashcard } from "@/features/quiz/flashcard";
import type { Route } from "./+types/flashcard";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Flashcard" },
    { name: "description", content: "Flashcard" },
  ];
}

export default function QuizPage() {
  return (
    <>
      <Flashcard />
    </>
  );
}
