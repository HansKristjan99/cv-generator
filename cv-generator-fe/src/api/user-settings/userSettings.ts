import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type UserSettings = {
  preferred_template_id: string | null;
};

export async function getUserSettings(): Promise<UserSettings> {
  const response = await authFetch("/users/settings");
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return (await response.json()) as UserSettings;
}

export async function updateUserSettings(settings: UserSettings): Promise<UserSettings> {
  const response = await authFetch("/users/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return (await response.json()) as UserSettings;
}
