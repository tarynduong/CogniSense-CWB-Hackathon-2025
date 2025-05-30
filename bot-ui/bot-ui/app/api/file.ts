import { UPLOAD_FILE_ENDPOINT, UPLOAD_URL_ENDPOINT } from "@/api/constants";
import { getAccessToken } from "@/features/auth/auth";
import axios from "axios";

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

export async function uploadBlog(blogUrl: string) {
  const accessToken = getAccessToken();

  const formData = new FormData();
  formData.append("url", blogUrl);

  return axios.post(UPLOAD_URL_ENDPOINT, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
