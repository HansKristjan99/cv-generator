export const SUGGESTED_STATUSES = [
  "initial",
  "cv_submitted",
  "phone_screen",
  "interview",
  "final_interview",
  "offer",
  "hired",
  "rejected",
  "withdrawn",
] as const;

export type StatusTone = "sky" | "mint" | "primary" | "danger" | "neutral";

const TONE_BY_STATUS: Record<string, StatusTone> = {
  initial: "sky",
  cv_submitted: "sky",
  phone_screen: "mint",
  interview: "mint",
  final_interview: "mint",
  offer: "primary",
  hired: "primary",
  rejected: "danger",
  withdrawn: "danger",
};

export function statusTone(status: string): StatusTone {
  return TONE_BY_STATUS[status] ?? "neutral";
}

export function statusLabel(status: string): string {
  // "phone_screen" -> "Phone screen"
  const trimmed = status.trim();
  if (!trimmed) return "Untitled";
  const spaced = trimmed.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
