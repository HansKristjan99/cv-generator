export type AssistantMessageType = "text" | "question" | "cv";

export type CvQuestion = {
  question: string;
  corresponding_requirement: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  type: AssistantMessageType;
  content: string;
  /** Present on question-type assistant messages; powers the "Enhance" button. */
  questions?: CvQuestion[];
};

export type CvGeneratedResponse = { latex: string; pdf_base64: string };
export type CvQuestionResponse = { questions: CvQuestion[] };
export type OtherTextResponse = { text: string };

export type GenerateCvResponse = {
  conversation_id: string;
  content: CvGeneratedResponse | CvQuestionResponse | OtherTextResponse;
};

export function isCvGenerated(c: GenerateCvResponse["content"]): c is CvGeneratedResponse {
  return "latex" in c;
}
export function isCvQuestions(c: GenerateCvResponse["content"]): c is CvQuestionResponse {
  return "questions" in c;
}
export function isOtherText(c: GenerateCvResponse["content"]): c is OtherTextResponse {
  return "text" in c;
}

export type SendChatMessageInput = {
  conversationId: string | null;
  userMessage: string;
  cvText?: string;
  cvFile?: File | null;
  jobDescription?: string;
};

export type StartGenerateResponse = {
  job_id: string;
  session_id: string;
  conversation_id: string;
};

export type JobStatusResponse = {
  status: "pending" | "running" | "succeeded" | "failed";
  result: GenerateCvResponse | null;
  error: string | null;
};

export type SessionSummary = {
  id: string;
  title: string | null;
  message_count: number;
  created_at: string;
};

export type LoadConversationResponse = {
  conversation_id: string;
  title: string | null;
  messages: ChatMessage[];
  latest_pdf_base64: string | null;
};
