import { SignUp } from "@/features/auth/signup";
import type { Route } from "./+types/signup";
import { saveAccessToken } from "@/features/auth/auth";
import { redirect } from "react-router";
import { signup } from "@/api/auth";

export function meta({}: Route.MetaArgs) {
  return [{ title: "Sign Up" }, { name: "description", content: "Sign Up" }];
}

export async function clientAction({
  request,
}: Route.ClientActionArgs): Promise<{
  error: string;
}> {
  const formData = await request.formData();
  const username = formData.get("username")?.toString() || "";
  const password = formData.get("password")?.toString() || "";

  const { error, accessToken } = await signup(username, password);
  if (error) {
    return {
      error: error,
    };
  }
  if (accessToken) saveAccessToken(accessToken);
  throw redirect("/");
}

export default function SignUpPage({ actionData }: Route.ComponentProps) {
  return (
    <>
      <SignUp error={actionData?.error} />
    </>
  );
}
