import type { CvGenerationState } from "./types";

export const initialState: CvGenerationState = {
  activeSessionId: null,
  messageHistory: [],
  draftMessage: "",
  setupStatus: "idle",
  generationStatus: "idle",
  historyStatus: "idle",
  enhanceStatus: "idle",
  manualEditStatus: "idle",
  error: null,
  jobDescription: null,
  sourceCvText: null,
  sourceCvPdfBase64: null,
  latestCvPdfBase64: null,
  latestCoverLetterPdfBase64: null,
  latestCvStructured: null,
  latestClStructured: null,
  previewSelection: null,
  monthlySessionsUsed: null,
  monthlyInventsUsed: null,
  isUnlimited: false,
  chatSessions: [],
};

export const PREVIEW_RESET = {
  jobDescription: null,
  sourceCvText: null,
  sourceCvPdfBase64: null,
  latestCvPdfBase64: null,
  latestCoverLetterPdfBase64: null,
  latestCvStructured: null,
  latestClStructured: null,
  previewSelection: null,
} as const;
