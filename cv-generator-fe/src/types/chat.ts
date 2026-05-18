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
