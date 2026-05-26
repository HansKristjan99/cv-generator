import { simpleSections } from "./sections";
import type { Editor, JobDraft } from "./types";

export function canSave(editor: Editor): boolean {
  if (editor.kind === "job_experiences") {
    const draft = editor.draft as JobDraft;
    return (
      Boolean(draft.company_name.trim()) &&
      Boolean(draft.job_title.trim()) &&
      draft.bullets.every((bullet) => Boolean(bullet.bullet_points.trim()))
    );
  }

  const section = simpleSections.find((item) => item.kind === editor.kind);
  if (!section) return false;
  const draft = editor.draft as Record<string, string>;
  return section.fields.every((field) => {
    if (field.maxLength && (draft[field.name] ?? "").length > field.maxLength) return false;
    return !field.required || Boolean((draft[field.name] ?? "").trim());
  });
}
