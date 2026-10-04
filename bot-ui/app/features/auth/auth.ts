import { jwtDecode } from "jwt-decode";

type JwtPayload = {
  exp: number;
  user_id: string;
};

export const getAccessToken = () => {
  const accessToken = localStorage.getItem("accessToken");
  if (!accessToken || !isValidAccessToken(accessToken)) {
    removeAccessToken();
    return null;
  }
  return accessToken;
};

export const saveAccessToken = (accessToken: string) => {
  localStorage.setItem("accessToken", accessToken);
};

export const removeAccessToken = () => {
  localStorage.removeItem("accessToken");
};

export const isValidAccessToken = (accessToken: string) => {
  try {
    const decodedToken = jwtDecode<JwtPayload>(accessToken);
    if (!decodedToken.exp || decodedToken.exp < Date.now() / 1000) {
      return false;
    }

    if (!decodedToken.user_id) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
};
