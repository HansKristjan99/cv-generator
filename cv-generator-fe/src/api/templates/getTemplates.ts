import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type Template = {
  id: string;
  name: string;
  slug: string;
};

export async function getTemplates(): Promise<Template[]> {
  const response = await authFetch("/templates/");
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return (await response.json()) as Template[];
}
