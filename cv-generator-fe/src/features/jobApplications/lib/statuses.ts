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

export type Stage = "saved" | "applied" | "interviewing" | "offer" | "closed";

export type StageDef = {
  id: Stage;
  label: string;
  subtitle: string;
  tone: StatusTone;
  defaultStatus: string;
};

export const STAGES: StageDef[] = [
  { id: "saved", label: "Saved", subtitle: "leads & wishlists", tone: "neutral", defaultStatus: "initial" },
  { id: "applied", label: "Applied", subtitle: "awaiting reply", tone: "sky", defaultStatus: "cv_submitted" },
  { id: "interviewing", label: "Interviewing", subtitle: "active processes", tone: "mint", defaultStatus: "interview" },
  { id: "offer", label: "Offer", subtitle: "celebrate when ready", tone: "primary", defaultStatus: "offer" },
  { id: "closed", label: "Closed", subtitle: "rejected / withdrawn", tone: "danger", defaultStatus: "rejected" },
];

const STAGE_BY_STATUS: Record<string, Stage> = {
  initial: "saved",
  cv_submitted: "applied",
  phone_screen: "interviewing",
  interview: "interviewing",
  final_interview: "interviewing",
  offer: "offer",
  hired: "offer",
  rejected: "closed",
  withdrawn: "closed",
};

export function stageForStatus(status: string): Stage {
  return STAGE_BY_STATUS[status] ?? "saved";
}

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
