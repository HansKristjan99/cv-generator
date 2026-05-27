import { cx } from "../../../utils/cx";
import { canSave } from "../lib/canSave";
import type { Editor, JobDraft, MemoryKind } from "../lib/types";
import { NEW_ID } from "../lib/types";
import styles from "../userMemory.module.css";
import { EditorActions } from "./editorActions";
import { Field } from "./field";
import { JobBulletEditor } from "./jobBulletEditor";

const JOB_FIELDS = [
  { name: "company_name", label: "Company", required: true },
  { name: "job_title", label: "Job title", required: true },
  { name: "location", label: "Location" },
  { name: "start_date", label: "Start date" },
  { name: "end_date", label: "End date" },
];

type Props = {
  editor: Editor;
  setEditor: (editor: Editor | null) => void;
  saveEditor: () => void;
  removeItem: (kind: MemoryKind, id: string) => void;
  saving: boolean;
};

export function JobEditor({ editor, setEditor, saveEditor, removeItem, saving }: Props) {
  const draft = editor.draft as JobDraft;
  const setDraft = (next: JobDraft) => setEditor({ ...editor, draft: next });

  return (
    <article className={cx(styles.itemCard, styles.itemCardOpen)}>
      <div className={styles.editorHead}>
        <div>
          <p className={styles.editorEyebrow}>{editor.id === NEW_ID ? "New" : "Editing"}</p>
          <h3 className={styles.editorTitle}>Job Experience</h3>
        </div>
      </div>

      <div className={styles.fieldGrid}>
        {JOB_FIELDS.map((field) => (
          <Field
            key={field.name}
            field={field}
            value={draft[field.name as keyof JobDraft] as string}
            onChange={(value) => setDraft({ ...draft, [field.name]: value })}
          />
        ))}
      </div>

      <div className={styles.bullets}>
        <div className={styles.bulletsHead}>
          <span>Bullets</span>
          <button
            type="button"
            className={styles.inlineButton}
            onClick={() =>
              setDraft({
                ...draft,
                bullets: [
                  ...draft.bullets,
                  { id: "", bullet_points: "", relevant_technologies: "" },
                ],
              })
            }
          >
            Add bullet
          </button>
        </div>
        {draft.bullets.length === 0 ? <p className={styles.emptySmall}>No bullets yet.</p> : null}
        {draft.bullets.map((bullet, index) => (
          <JobBulletEditor
            key={`${bullet.id || "new"}:${index}`}
            editor={editor}
            setEditor={setEditor}
            draft={draft}
            bullet={bullet}
            index={index}
          />
        ))}
      </div>

      <EditorActions
        canSave={canSave(editor)}
        saving={saving}
        canRemove={editor.id !== NEW_ID}
        onSave={saveEditor}
        onCancel={() => setEditor(null)}
        onRemove={() => removeItem("job_experiences", editor.id)}
      />
    </article>
  );
}
