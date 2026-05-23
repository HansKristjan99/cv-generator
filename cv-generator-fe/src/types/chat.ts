export type AssistantMessageType = "text" | "question" | "cv" | "cover_letter";

export type GenerationKind = "cv" | "cover_letter";

/** Which artifact the conversation preview pane is currently showing. */
export type PreviewKind = "jd" | "source_cv" | "generated_cv" | "cover_letter";

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
  /** Required CV length in pages (1–3); only used when starting a new session. */
  pageCount?: number;
  /** What to generate; defaults to "cv". Only used when starting a new session. */
  kind?: GenerationKind;
};

export type StartGenerateResponse = {
  session_id: string;
  status: SessionStatus;
};

export type SessionStatus = "idle" | "pending" | "running" | "failed";

export type SessionSummary = {
  id: string;
  title: string | null;
  kind: GenerationKind;
  message_count: number;
  page_count: number;
  status: SessionStatus;
  error: string | null;
  created_at: string;
};

export type LoadConversationResponse = {
  title: string | null;
  kind: GenerationKind;
  status: SessionStatus;
  error: string | null;
  page_count: number;
  messages: ChatMessage[];
  job_description: string | null;
  source_cv_text: string | null;
  source_cv_pdf_base64: string | null;
  latest_cv_pdf_base64: string | null;
  latest_cover_letter_pdf_base64: string | null;
  latest_cv_structured: import("./cv").CvStructuredData | null;
  latest_cover_letter_structured: import("./cv").ClStructuredData | null;
};
