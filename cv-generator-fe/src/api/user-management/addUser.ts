import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type CurrentUser = {
  id: string;
  idp_sub: string;
  email: string;
};

export async function registerCurrentUser(): Promise<CurrentUser> {
  const response = await authFetch("/api/users/me", { method: "POST" });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as CurrentUser;
}
