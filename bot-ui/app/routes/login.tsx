import { saveAccessToken } from "@/features/auth/auth";
import type { Route } from "./+types/login";
import { Login } from "@/features/auth/login";
import { redirect } from "react-router";
import { login } from "@/api/auth";

export function meta({}: Route.MetaArgs) {
  return [{ title: "Login" }, { name: "description", content: "Login" }];
}

export async function clientAction({
  request,
}: Route.ClientActionArgs): Promise<{
  error: string;
}> {
  const formData = await request.formData();
  const username = formData.get("username")?.toString() || "";
  const password = formData.get("password")?.toString() || "";

  const { error, accessToken } = await login(username, password);
  if (error) {
    return {
      error: error,
    };
  }
  if (accessToken) saveAccessToken(accessToken);
  throw redirect("/");
}

export default function LoginPage({ actionData }: Route.ComponentProps) {
  return (
    <>
      <Login error={actionData?.error} />
    </>
  );
}
