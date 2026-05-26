import type { UserMemoryPatch } from "../../../api/user-memory/userMemory";
import type { Editor, JobDraft } from "./types";

const nullable = (value: string) => value.trim() || null;

export function buildPatch(editor: Editor): UserMemoryPatch {
  if (editor.kind === "job_experiences") {
    const draft = editor.draft as JobDraft;
    return {
      job_experiences: [
        {
          id: draft.id || null,
          company_name: draft.company_name.trim(),
          job_title: draft.job_title.trim(),
          start_date: nullable(draft.start_date),
          end_date: nullable(draft.end_date),
          location: nullable(draft.location),
          bullets: [
            ...draft.bullets.map((bullet) => ({
              id: bullet.id || null,
              bullet_points: bullet.bullet_points.trim(),
              relevant_technologies: nullable(bullet.relevant_technologies),
            })),
            ...editor.removedChildIds.map((id) => ({ id, delete: true })),
          ],
        },
      ],
    };
  }

  const draft = editor.draft as Record<string, string>;
  const payload = Object.fromEntries(
    Object.entries(draft)
      .filter(([key]) => key !== "id")
      .map(([key, value]) => [key, key === "content" ? value.trim() : nullable(value)]),
  );
  return { [editor.kind]: [{ id: draft.id || null, ...payload }] };
}
