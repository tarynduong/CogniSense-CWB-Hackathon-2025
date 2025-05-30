import type { Route } from "./+types/quiz";
import { Quiz } from "@/features/quiz/quiz";

export function meta({}: Route.MetaArgs) {
  return [{ title: "Quiz" }, { name: "description", content: "Quiz" }];
}

export default function QuizPage() {
  return (
    <>
      <Quiz />
    </>
  );
}
