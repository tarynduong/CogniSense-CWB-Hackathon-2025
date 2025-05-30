import type { Route } from "./+types/home";
import { Chat } from "../features/chat/chat";

export function meta({}: Route.MetaArgs) {
  return [{ title: "Chat" }, { name: "description", content: "Chat" }];
}

export default function Home() {
  return (
    <>
      <Chat />
    </>
  );
}
