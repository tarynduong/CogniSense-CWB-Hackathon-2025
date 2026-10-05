import { UPLOAD_FILE_ENDPOINT, UPLOAD_URL_ENDPOINT } from "@/api/constants";
import { getAccessToken } from "@/features/auth/auth";
import axios, { AxiosError } from "axios";

export async function uploadFile(file: File, fileType: string) {
  const accessToken = getAccessToken();

  const formData = new FormData();
  formData.append("file", file);
  formData.append("type", fileType);

  return axios.post(UPLOAD_FILE_ENDPOINT, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export async function uploadBlog(
  blogUrl: string
): Promise<{ ok: boolean; message?: string; error?: string }> {
  const accessToken = getAccessToken();

  const formData = new FormData();
  formData.append("url", blogUrl);

  try {
    const res = await axios.post(UPLOAD_URL_ENDPOINT, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
        Authorization: `Bearer ${accessToken}`,
      },
    });
    return { ok: true, message: res.data?.message };
  } catch (error) {
    const status = (error as AxiosError)?.response?.status;
    const data = (error as AxiosError)?.response?.data as
      | { error?: string; reason?: string; details?: string }
      | undefined;

    // Prefer the backend's human message. Never surface raw axios text like
    // "Request failed with status code 500" to the user.
    let friendly = data?.error;
    if (!friendly) {
      if (status === 500) {
        friendly =
          "We couldn't read this link — it may be blocked for scraping or require sign-in. Try a different source.";
      } else if (status === 504) {
        friendly = "The site took too long to respond. Please try again or use another link.";
      } else {
        friendly = "We couldn't import this link. Try a different source.";
      }
    }

    return { ok: false, error: friendly };
  }
}
