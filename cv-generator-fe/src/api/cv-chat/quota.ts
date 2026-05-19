import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type CvQuota = {
  sessions_used: number;
  sessions_limit: number | null;
  messages_limit: number | null;
  invents_used: number;
  invents_limit: number | null;
  is_unlimited: boolean;
};

export async function getCvQuota(): Promise<CvQuota> {
  const response = await authFetch("/api/cv/quota");
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as CvQuota;
}
