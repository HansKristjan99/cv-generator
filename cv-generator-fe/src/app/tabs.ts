export type AppTab =
  | "cv"
  | "templates"
  | "user memory"
  | "session"
  | "applications"
  | "subscription";

export const SIDEBAR_TABS: Array<{ id: AppTab; label: string }> = [
  { id: "cv", label: "New CV" },
  { id: "templates", label: "Templates" },
  { id: "user memory", label: "Memory" },
  { id: "applications", label: "Applications" },
  { id: "subscription", label: "Subscription" },
];

export function isAppTab(value: string | null): value is AppTab {
  return (
    value === "cv" ||
    value === "templates" ||
    value === "user memory" ||
    value === "session" ||
    value === "applications" ||
    value === "subscription"
  );
}
