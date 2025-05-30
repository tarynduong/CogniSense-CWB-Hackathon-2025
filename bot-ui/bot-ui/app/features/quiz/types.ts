export type Flashcard = {
  question: string;
  answer: string;
};

export type QuizAnswer = {
  answer: string;
  isCorrectAnswer: boolean;
};

export type Quiz = {
  question: string;
  answers: QuizAnswer[];
};
