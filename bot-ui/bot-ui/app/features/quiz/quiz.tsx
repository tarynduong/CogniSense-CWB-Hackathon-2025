import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ArrowBigRight, RotateCcw } from "lucide-react";
import type { Quiz, QuizAnswer } from "@/features/quiz/types";
import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowUpIcon } from "@/components/icons";
import { Textarea } from "@/components/ui/textarea";
import { getQuizzes } from "@/api/quiz";
import { cn } from "@/lib/utils";

export function Quiz() {
  const [topic, setTopic] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [selectedAnswer, setSelectedAnswer] = useState<QuizAnswer | null>(null);

  const [questions, setQuestions] = useState<Quiz[]>([]);
  // Index of the current question
  const [currentQuestion, setCurrentQuestion] = useState<number>(0);
  const [isFetching, setFetching] = useState<boolean>(false);

  const onNextQuestion = () => {
    setSelectedAnswer(null);
    setCurrentQuestion(currentQuestion + 1);
  };

  const onResetQuestion = () => {
    setSelectedAnswer(null);
    setCurrentQuestion(0);
  };

  const onSubmitTopic = async (topic: string) => {
    setFetching(true);
    setError("");
    await getQuizzes(topic)
      .then((data) => {
        data.message && setError(data.message);
        setQuestions(data.quizzes);
      })
      .catch((error) => {
        setError(error.message);
        setQuestions([]);
      })
      .finally(() => {
        setFetching(false);
      });
  };

  const isLastQuestion = currentQuestion + 1 == questions.length;
  const question = questions[currentQuestion] ?? {};

  return (
    <div className="flex flex-col items-center justify-center min-w-0 h-dvh">
      <div className="flex flex-col mx-auto px-4 pb-4 md:pb-6 gap-2 w-full md:max-w-3xl mb-12">
        <div className="relative w-full flex flex-col gap-4">
          <Textarea
            data-testid="multimodal-input"
            placeholder="Input your topic here"
            className={
              "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-2xl !text-base bg-muted pb-10 dark:border-zinc-700"
            }
            rows={2}
            autoFocus
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />

          <div className="absolute bottom-0 right-0 p-2 w-fit flex flex-row justify-end">
            <Button
              data-testid="send-button"
              className="rounded-full p-1.5 h-fit border dark:border-zinc-600"
              onClick={() => onSubmitTopic(topic)}
            >
              <ArrowUpIcon size={14} />
            </Button>
          </div>
        </div>
        {error && (
          <p className="text-red-500 whitespace-normal break-words">{error}</p>
        )}
      </div>
      {isFetching && (
        <Card className="w-full max-w-md">
          <CardContent>
            <div className="flex flex-col items-left space-y-4">
              <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      {!isFetching && questions.length > 0 && (
        <Card className="w-full max-w-md">
          <>
            <CardHeader>
              <CardTitle>{question.question}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {question.answers.map((ans, index) => {
                const isSelected = selectedAnswer === ans;
                const isCorrect = ans.isCorrectAnswer;

                return (
                  <Button
                    key={index}
                    variant={
                      isSelected && !isCorrect ? "destructive" : "outline"
                    }
                    className={cn(
                      "w-full h-auto text-left whitespace-normal break-words",
                      selectedAnswer && isCorrect ? "bg-green-500" : null
                    )}
                    onClick={() => setSelectedAnswer(ans)}
                    disabled={!!selectedAnswer}
                  >
                    {ans.answer}
                  </Button>
                );
              })}
            </CardContent>
            <CardFooter className="justify-between">
              <div>
                {currentQuestion + 1} / {questions.length}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={isLastQuestion ? onResetQuestion : onNextQuestion}
              >
                {isLastQuestion ? <RotateCcw /> : <ArrowBigRight />}
              </Button>
            </CardFooter>
          </>
        </Card>
      )}
    </div>
  );
}
