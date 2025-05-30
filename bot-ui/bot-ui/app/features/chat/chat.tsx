import { chatWithBot } from "@/api/chat";
import { ArrowUpIcon } from "@/components/icons";
import { Markdown } from "@/components/markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Message } from "@/features/chat/types";
import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

function Messages({ messages }: { messages: Message[] }) {
  return (
    <>
      {messages.map(({ role, text }, i) => {
        return (
          <AnimatePresence key={i}>
            <motion.div
              data-testid={`message-${role}`}
              className="w-full mx-auto max-w-3xl px-4 group/message"
              initial={{ y: 5, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              data-role={role}
            >
              <div
                className={cn(
                  "flex gap-4 w-full group-data-[role=user]/message:ml-auto group-data-[role=user]/message:max-w-2xl",
                  {
                    "group-data-[role=user]/message:w-fit": true,
                  }
                )}
              >
                <div
                  className={cn("flex flex-col gap-4 w-full", {
                    "min-h-20": i == messages.length - 1,
                  })}
                >
                  <div className="flex flex-row gap-2 items-start">
                    <div
                      data-testid="message-content"
                      className={cn("flex flex-col gap-4", {
                        "bg-primary text-primary-foreground px-3 py-2 rounded-xl":
                          role === "user",
                      })}
                    >
                      <Markdown>{text}</Markdown>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        );
      })}
    </>
  );
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isFetching, setFetching] = useState<boolean>(false);
  const [currentMessage, setCurrentMessage] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const onSubmitMessage = async (message: Message) => {
    if (message.text.trim() === "") return;
    setFetching(true);
    setMessages((prev) => [...prev, message]);
    setCurrentMessage("");

    // API Call here
    const { answer } = await chatWithBot(message.text);
    if (answer) {
      setMessages((prev) => [
        ...prev,
        {
          text: answer,
          role: "assistant",
        },
      ]);
    }
    setFetching(false);
  };
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col min-w-0 h-dvh">
      <div className="flex flex-col min-w-0 gap-6 flex-1 overflow-y-scroll pt-4 relative">
        {messages.length == 0 && (
          <div
            key="overview"
            className="max-w-3xl mx-auto md:mt-20 px-8 size-full flex flex-col justify-center"
          >
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ delay: 0.5 }}
              className="text-2xl font-semibold"
            >
              Hello there!
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ delay: 0.6 }}
              className="text-2xl text-zinc-500"
            >
              How can I help you today?
            </motion.div>
          </div>
        )}
        {messages.length > 0 && <Messages messages={messages} />}
        <div ref={bottomRef} />
      </div>

      <div className="flex mx-auto px-4 pb-4 md:pb-6 gap-2 w-full md:max-w-3xl">
        <div className="relative w-full flex flex-col gap-4">
          <Textarea
            data-testid="multimodal-input"
            placeholder="Send a message..."
            className={
              "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-2xl !text-base bg-muted pb-10 dark:border-zinc-700"
            }
            rows={2}
            autoFocus
            value={currentMessage}
            onChange={(e) => setCurrentMessage(e.target.value)}
          />

          <div className="absolute bottom-0 right-0 p-2 w-fit flex flex-row justify-end">
            <Button
              data-testid="send-button"
              className="rounded-full p-1.5 h-fit border dark:border-zinc-600"
              onClick={() =>
                onSubmitMessage({
                  text: currentMessage,
                  role: "user",
                })
              }
            >
              {isFetching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowUpIcon size={14} />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
