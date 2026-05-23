import { authFetch, readErrorMessage } from "../auth-utils/authFetch";
import type { ClStructuredData, CvStructuredData, ManualEditResponse } from "../../types/cv";

export async function manualEditCv(
  sessionId: string,
  kind: "cv" | "cover_letter",
  data: CvStructuredData | ClStructuredData,
): Promise<ManualEditResponse> {
  const response = await authFetch(`/api/cv/sessions/${sessionId}/edit`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, data }),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as ManualEditResponse;
}
