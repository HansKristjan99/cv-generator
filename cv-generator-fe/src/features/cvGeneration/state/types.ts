import type { RequirementsAnalysis } from "../../../api/job-applications/jobApplications";
import type { ChatMessage, PreviewKind, SessionSummary } from "../../../types/chat";
import type { ClStructuredData, CvStructuredData } from "../../../types/cv";

export type Status = "idle" | "loading" | "succeeded" | "failed";

export type CvGenerationState = {
  activeSessionId: string | null;
  messageHistory: ChatMessage[];
  draftMessage: string;
  setupStatus: Status;
  generationStatus: Status;
  historyStatus: Status;
  enhanceStatus: Status;
  manualEditStatus: Status;
  error: string | null;
  jobDescription: string | null;
  jobRequirements: RequirementsAnalysis | null;
  sourceCvText: string | null;
  sourceCvPdfBase64: string | null;
  latestCvPdfBase64: string | null;
  latestCoverLetterPdfBase64: string | null;
  latestCvStructured: CvStructuredData | null;
  latestClStructured: ClStructuredData | null;
  previewSelection: PreviewKind | null;
  monthlySessionsUsed: number | null;
  monthlyInventsUsed: number | null;
  isUnlimited: boolean;
  chatSessions: SessionSummary[];
};
