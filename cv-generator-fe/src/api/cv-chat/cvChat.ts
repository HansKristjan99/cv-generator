import { authFetch, readErrorMessage } from "../auth-utils/authFetch";
import type {
  JobStatusResponse,
  LoadConversationResponse,
  SendChatMessageInput,
  SessionSummary,
  StartGenerateResponse,
} from "../../types/chat";

export async function sendChatMessage(input: SendChatMessageInput): Promise<StartGenerateResponse> {
  const formData = new FormData();
  formData.append("user_message", input.userMessage);

  if (input.conversationId) {
    formData.append("conversation_id", input.conversationId);
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
  }

  const response = await authFetch("/api/cv/generate/", { method: "POST", body: formData });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as StartGenerateResponse;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await authFetch(`/api/cv/jobs/${jobId}`);
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as JobStatusResponse;
}

export async function getChatSessions(): Promise<SessionSummary[]> {
  const response = await authFetch("/api/cv/sessions/");
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as SessionSummary[];
}

export async function getChatHistory(sessionId: string): Promise<LoadConversationResponse> {
  const response = await authFetch(`/api/cv/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as LoadConversationResponse;
}
