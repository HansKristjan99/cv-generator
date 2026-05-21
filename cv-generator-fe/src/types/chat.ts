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

export type SendChatMessageInput = {
  sessionId: string | null;
  userMessage: string;
  cvText?: string;
  cvFile?: File | null;
  jobDescription?: string;
};

export type StartGenerateResponse = {
  session_id: string;
  status: SessionStatus;
};

export type SessionStatus = "idle" | "pending" | "running" | "failed";

export type SessionSummary = {
  id: string;
  title: string | null;
  message_count: number;
  status: SessionStatus;
  error: string | null;
  created_at: string;
};

export type LoadConversationResponse = {
  title: string | null;
  status: SessionStatus;
  error: string | null;
  messages: ChatMessage[];
  latest_pdf_base64: string | null;
};
