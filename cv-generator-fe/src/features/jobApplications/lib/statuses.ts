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

const ACRONYMS = new Set(["cv", "cl"]);

export function statusLabel(status: string): string {
  // "phone_screen" -> "Phone screen"; "cv_submitted" -> "CV submitted"
  const trimmed = status.trim();
  if (!trimmed) return "Untitled";
  const tokens = trimmed.split("_").filter(Boolean);
  if (tokens.length === 0) return "Untitled";
  const formatted = tokens.map((token, index) => {
    const lower = token.toLowerCase();
    if (ACRONYMS.has(lower)) return lower.toUpperCase();
    if (index === 0) return lower.charAt(0).toUpperCase() + lower.slice(1);
    return lower;
  });
  return formatted.join(" ");
}
