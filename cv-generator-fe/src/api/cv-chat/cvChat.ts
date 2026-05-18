import { authFetch, readErrorMessage } from "../auth-utils/authFetch";
import type { GenerateCvResponse, SendChatMessageInput } from "../../types/chat";

export async function sendChatMessage(input: SendChatMessageInput): Promise<GenerateCvResponse> {
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

  return (await response.json()) as GenerateCvResponse;
}
