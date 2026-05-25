import { authFetch, readErrorMessage } from "../auth-utils/authFetch";
import type {
  LoadConversationResponse,
  SendChatMessageInput,
  SessionSummary,
  StartGenerateResponse,
} from "../../types/chat";

export async function sendChatMessage(input: SendChatMessageInput): Promise<StartGenerateResponse> {
  const formData = new FormData();
  formData.append("user_message", input.userMessage);
  formData.append("kind", input.kind ?? "cv");

  if (input.sessionId) {
    formData.append("session_id", input.sessionId);
  } else {
    if (input.cvText?.trim()) {
      formData.append("text", input.cvText.trim());
    }
    if (input.cvFile) {
      formData.append("file", input.cvFile);
    }
    if (input.jobDescription?.trim()) {
      formData.append("job_description", input.jobDescription.trim());
    }
    if (input.pageCount) {
      formData.append("page_count", String(input.pageCount));
    }
  }

  const response = await authFetch("/cv/generate/", { method: "POST", body: formData });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as StartGenerateResponse;
}

export async function getChatSessions(): Promise<SessionSummary[]> {
  const response = await authFetch("/cv/sessions/");
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as SessionSummary[];
}

export async function getChatHistory(sessionId: string): Promise<LoadConversationResponse> {
  const response = await authFetch(`/cv/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as LoadConversationResponse;
}
