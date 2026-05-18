import { authFetch, readErrorMessage } from "../auth-utils/authFetch";
import type { CvQuestion } from "../../types/chat";

export type InventCvAnswersInput = {
  conversation_id: string;
  job_description: string;
  questions: CvQuestion[];
};

export type InventCvAnswersResponse = { invented_answers: string };

export async function inventCvAnswers(
  input: InventCvAnswersInput,
): Promise<InventCvAnswersResponse> {
  const response = await authFetch("/api/cv/invent/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as InventCvAnswersResponse;
}
