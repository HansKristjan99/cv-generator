export type AssistantMessageType = "text" | "question" | "cv";

export type ChatMessage = {
  role: "user" | "assistant";
  type: AssistantMessageType;
  content: string;
};

export type CvGeneratedResponse = { latex: string; pdf_base64: string };
export type CvQuestionResponse = { questions: string[] };

export type GenerateCvResponse = {
  conversation_id: string;
  content: CvGeneratedResponse | CvQuestionResponse;
};

export type SendChatMessageInput = {
  conversationId: string | null;
  userMessage: string;
  cvText?: string;
  cvFile?: File | null;
  jobDescription?: string;
};
