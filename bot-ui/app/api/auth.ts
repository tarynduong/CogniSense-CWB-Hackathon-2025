import { LOGIN_ENDPOINT, REGISTER_ENDPOINT } from "@/api/constants";
import axios, { AxiosError } from "axios";

export async function login(
  username: string,
  password: string
): Promise<{
  error: string | undefined;
  accessToken: string | undefined;
}> {
  const body = {
    username,
    password,
  };

  return await axios
    .post<{
      message: string;
      access_token: string;
    }>(LOGIN_ENDPOINT, body, {
      headers: {
        "Content-Type": "application/json",
      },
    })
    .then((response) => {
      const { message: _, access_token } = response.data;
      return {
        error: undefined,
        accessToken: access_token,
      };
    })
    .catch((error: AxiosError) => {
      return {
        error:
          ((error.response?.data as any).message as string) || error.message,
        accessToken: undefined,
      };
    });
}

export async function signup(
  username: string,
  password: string
): Promise<{
  error: string | undefined;
  accessToken: string | undefined;
}> {
  const body = {
    username,
    password,
  };

  return await axios
    .post<{
      message: string;
      access_token: string;
    }>(REGISTER_ENDPOINT, body, {
      headers: {
        "Content-Type": "application/json",
      },
    })
    .then((response) => {
      const { message: _, access_token } = response.data;
      return {
        error: undefined,
        accessToken: access_token,
      };
    })
    .catch((error) => {
      return {
        error:
          ((error.response?.data as any).message as string) || error.message,
        accessToken: undefined,
      };
    });
}
