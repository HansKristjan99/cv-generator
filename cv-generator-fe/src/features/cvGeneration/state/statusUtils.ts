import type { SessionStatus } from "../../../types/chat";
import type { Status } from "./types";

export const isGeneratingSession = (status: SessionStatus) =>
  status === "pending" || status === "running";

export const toGenerationStatus = (status: SessionStatus): Status => {
  if (isGeneratingSession(status)) return "loading";
  if (status === "failed") return "failed";
  return "idle";
};
