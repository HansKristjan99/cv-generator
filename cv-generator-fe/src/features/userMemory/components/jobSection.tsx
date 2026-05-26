import type { JobExperience } from "../../../api/user-memory/userMemory";
import { blankJob, jobToDraft } from "../lib/jobDrafts";
import { dates } from "../lib/itemField";
import type { Editor, MemoryKind } from "../lib/types";
import { NEW_ID } from "../lib/types";
import styles from "../userMemory.module.css";
import { CollapsedCard } from "./collapsedCard";
import { JobEditor } from "./jobEditor";
import { SectionHeader } from "./sectionHeader";

type Props = {
  jobs: JobExperience[];
  editor: Editor | null;
  setEditor: (editor: Editor | null) => void;
  saveEditor: () => void;
  removeItem: (kind: MemoryKind, id: string) => void;
  saving: boolean;
};

export function JobSection({ jobs, editor, setEditor, saveEditor, removeItem, saving }: Props) {
  const isAdding = editor?.kind === "job_experiences" && editor.id === NEW_ID;
  const openJobId = editor?.kind === "job_experiences" && editor.id !== NEW_ID ? editor.id : null;

  return (
    <section className={styles.section}>
      <SectionHeader
        title="Job Experience"
        eyebrow="Roles and impact"
        count={jobs.length}
        addLabel="Add role"
        onAdd={() =>
          setEditor({
            kind: "job_experiences",
            id: NEW_ID,
            draft: blankJob(),
            removedChildIds: [],
          })
        }
      />
      <div className={styles.itemList}>
        {isAdding && editor ? (
          <JobEditor
            editor={editor}
            setEditor={setEditor}
            saveEditor={saveEditor}
            removeItem={removeItem}
            saving={saving}
          />
        ) : null}
        {jobs.length === 0 && !isAdding ? <p className={styles.empty}>No roles saved yet.</p> : null}
        {jobs.map((job) => {
          if (openJobId === job.id && editor) {
            return (
              <JobEditor
                key={job.id}
                editor={editor}
                setEditor={setEditor}
                saveEditor={saveEditor}
                removeItem={removeItem}
                saving={saving}
              />
            );
          }
          return (
            <CollapsedCard
              key={job.id}
              title={job.job_title}
              meta={[job.company_name, job.location, dates(job.start_date, job.end_date)]
                .filter(Boolean)
                .join(" · ")}
              saving={saving}
              onOpen={() =>
                setEditor({
                  kind: "job_experiences",
                  id: job.id,
                  draft: jobToDraft(job),
                  removedChildIds: [],
                })
              }
              onDelete={() => removeItem("job_experiences", job.id)}
            />
          );
        })}
      </div>
    </section>
  );
}
