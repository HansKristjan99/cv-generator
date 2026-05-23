import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { saveManualEdit } from "../features/cvGeneration/cvGenerationSlice";
import type {
  Award,
  ClStructuredData,
  CvStructuredData,
  Education,
  JobExperience,
  Project,
  SkillSection,
} from "../types/cv";
import styles from "./manualEditModal.module.css";

type Props = {
  kind: "cv" | "cover_letter";
  initialData: CvStructuredData | ClStructuredData;
  onClose: () => void;
};

export function ManualEditModal({ kind, initialData, onClose }: Props) {
  const dispatch = useAppDispatch();
  const saving = useAppSelector((s) => s.cvGeneration.manualEditStatus === "loading");
  const [draft, setDraft] = useState<CvStructuredData | ClStructuredData>(
    structuredClone(initialData),
  );

  const cv = kind === "cv" ? (draft as CvStructuredData) : null;
  const cl = kind === "cover_letter" ? (draft as ClStructuredData) : null;

  function patchCv(patch: Partial<CvStructuredData>) {
    setDraft((prev) => ({ ...(prev as CvStructuredData), ...patch }));
  }
  function patchCl(patch: Partial<ClStructuredData>) {
    setDraft((prev) => ({ ...(prev as ClStructuredData), ...patch }));
  }

  async function handleSave() {
    const result = await dispatch(saveManualEdit({ kind, data: draft }));
    if (saveManualEdit.fulfilled.match(result)) {
      onClose();
    }
  }

  return (
    <div className={styles.backdrop} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.panel} role="dialog" aria-modal="true">
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>
            {kind === "cv" ? "Edit CV" : "Edit Cover Letter"}
          </span>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className={styles.body}>
          {cv && (
            <CvForm
              data={cv}
              onChange={patchCv}
            />
          )}
          {cl && (
            <ClForm
              data={cl}
              onChange={patchCl}
            />
          )}
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className={styles.saveBtn} onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save & re-render"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── CV form ──────────────────────────────────────────────────── */

function CvForm({
  data,
  onChange,
}: {
  data: CvStructuredData;
  onChange: (patch: Partial<CvStructuredData>) => void;
}) {
  return (
    <>
      <Section title="Contact">
        <FieldRow>
          <Field label="Name" value={data.name} onChange={(v) => onChange({ name: v })} />
          <Field label="Location" value={data.location} onChange={(v) => onChange({ location: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Email" value={data.email} onChange={(v) => onChange({ email: v })} />
          <Field label="Phone" value={data.phone ?? ""} onChange={(v) => onChange({ phone: v || null })} />
        </FieldRow>
        <Field
          label="Links (one per line)"
          value={data.links.join("\n")}
          multiline
          onChange={(v) => onChange({ links: v.split("\n").map((l) => l.trim()).filter(Boolean) })}
        />
      </Section>

      <Section title="Summary">
        <Field
          label="Professional summary"
          value={data.summary}
          multiline
          rows={4}
          onChange={(v) => onChange({ summary: v })}
        />
      </Section>

      <Section title="Experience">
        <ListEditor
          items={data.experience}
          onChange={(experience) => onChange({ experience })}
          newItem={newJob}
          renderItem={(job, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Company" value={job.company} onChange={(v) => onItemChange({ ...job, company: v })} />
                <Field label="Position" value={job.position} onChange={(v) => onItemChange({ ...job, position: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="Location" value={job.location} onChange={(v) => onItemChange({ ...job, location: v })} />
                <Field label="Start date" value={job.start_date} onChange={(v) => onItemChange({ ...job, start_date: v })} />
                <Field label="End date" value={job.end_date} onChange={(v) => onItemChange({ ...job, end_date: v })} />
              </FieldRow>
              <Field
                label="Bullets (one per line)"
                value={job.bullets.join("\n")}
                multiline
                rows={4}
                onChange={(v) => onItemChange({ ...job, bullets: v.split("\n").map((l) => l.trim()).filter(Boolean) })}
              />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Education">
        <ListEditor
          items={data.education}
          onChange={(education) => onChange({ education })}
          newItem={newEducation}
          renderItem={(edu, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Institution" value={edu.institution} onChange={(v) => onItemChange({ ...edu, institution: v })} />
                <Field label="Degree" value={edu.degree} onChange={(v) => onItemChange({ ...edu, degree: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="Location" value={edu.location} onChange={(v) => onItemChange({ ...edu, location: v })} />
                <Field label="Start date" value={edu.start_date} onChange={(v) => onItemChange({ ...edu, start_date: v })} />
                <Field label="End date" value={edu.end_date} onChange={(v) => onItemChange({ ...edu, end_date: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="GPA" value={edu.gpa ?? ""} onChange={(v) => onItemChange({ ...edu, gpa: v || null })} />
                <Field label="Thesis" value={edu.thesis ?? ""} onChange={(v) => onItemChange({ ...edu, thesis: v || null })} />
              </FieldRow>
              <Field label="Coursework" value={edu.coursework ?? ""} onChange={(v) => onItemChange({ ...edu, coursework: v || null })} />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Skills">
        <ListEditor
          items={data.skills}
          onChange={(skills) => onChange({ skills })}
          newItem={newSkill}
          renderItem={(skill, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <Field label="Category" value={skill.title} onChange={(v) => onItemChange({ ...skill, title: v })} />
              <Field label="Items (comma-separated)" value={skill.items} onChange={(v) => onItemChange({ ...skill, items: v })} />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Projects">
        <ListEditor
          items={data.projects}
          onChange={(projects) => onChange({ projects })}
          newItem={newProject}
          renderItem={(proj, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Name" value={proj.name} onChange={(v) => onItemChange({ ...proj, name: v })} />
                <Field label="URL" value={proj.url ?? ""} onChange={(v) => onItemChange({ ...proj, url: v || null })} />
              </FieldRow>
              <Field label="Description" value={proj.description} multiline onChange={(v) => onItemChange({ ...proj, description: v })} />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Awards">
        <ListEditor
          items={data.awards}
          onChange={(awards) => onChange({ awards })}
          newItem={newAward}
          renderItem={(award, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Title" value={award.title} onChange={(v) => onItemChange({ ...award, title: v })} />
                <Field label="Issuer" value={award.issuer ?? ""} onChange={(v) => onItemChange({ ...award, issuer: v || null })} />
                <Field label="Date" value={award.date ?? ""} onChange={(v) => onItemChange({ ...award, date: v || null })} />
              </FieldRow>
            </ItemCard>
          )}
        />
      </Section>
    </>
  );
}

/* ─── Cover letter form ────────────────────────────────────────── */

function ClForm({
  data,
  onChange,
}: {
  data: ClStructuredData;
  onChange: (patch: Partial<ClStructuredData>) => void;
}) {
  return (
    <>
      <Section title="Your details">
        <FieldRow>
          <Field label="Name" value={data.name} onChange={(v) => onChange({ name: v })} />
          <Field label="Title" value={data.title} onChange={(v) => onChange({ title: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Email" value={data.email} onChange={(v) => onChange({ email: v })} />
          <Field label="Phone" value={data.phone ?? ""} onChange={(v) => onChange({ phone: v || null })} />
        </FieldRow>
        <FieldRow>
          <Field label="Location" value={data.location} onChange={(v) => onChange({ location: v })} />
          <Field label="LinkedIn" value={data.linkedin ?? ""} onChange={(v) => onChange({ linkedin: v || null })} />
        </FieldRow>
      </Section>

      <Section title="Addressing">
        <FieldRow>
          <Field label="Recipient" value={data.recipient} onChange={(v) => onChange({ recipient: v })} />
          <Field label="Company" value={data.company} onChange={(v) => onChange({ company: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Greeting" value={data.greeting} onChange={(v) => onChange({ greeting: v })} />
          <Field label="Sign-off" value={data.closer} onChange={(v) => onChange({ closer: v })} />
        </FieldRow>
      </Section>

      <Section title="Body">
        <Field
          label="Letter body (paragraphs separated by blank lines)"
          value={data.body}
          multiline
          rows={14}
          onChange={(v) => onChange({ body: v })}
        />
      </Section>
    </>
  );
}

/* ─── Shared sub-components ────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}

function FieldRow({ children }: { children: React.ReactNode }) {
  return <div className={styles.fieldRow}>{children}</div>;
}

function Field({
  label,
  value,
  onChange,
  multiline = false,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  rows?: number;
}) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      {multiline ? (
        <textarea
          className={styles.input}
          value={value}
          rows={rows}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          type="text"
          className={styles.input}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

function ListEditor<T>({
  items,
  onChange,
  newItem,
  renderItem,
}: {
  items: T[];
  onChange: (items: T[]) => void;
  newItem: () => T;
  renderItem: (item: T, idx: number, onItemChange: (updated: T) => void, onRemove: () => void) => React.ReactNode;
}) {
  return (
    <div className={styles.listEditor}>
      {items.map((item, idx) =>
        renderItem(
          item,
          idx,
          (updated) => {
            const next = [...items];
            next[idx] = updated;
            onChange(next);
          },
          () => onChange(items.filter((_, i) => i !== idx)),
        ),
      )}
      <button type="button" className={styles.addBtn} onClick={() => onChange([...items, newItem()])}>
        + Add
      </button>
    </div>
  );
}

function ItemCard({ onRemove, children }: { onRemove: () => void; children: React.ReactNode }) {
  return (
    <div className={styles.itemCard}>
      <div className={styles.itemCardContent}>{children}</div>
      <button type="button" className={styles.removeBtn} onClick={onRemove} aria-label="Remove">
        Remove
      </button>
    </div>
  );
}

/* ─── Default new-item factories ──────────────────────────────── */

const newJob = (): JobExperience => ({
  company: "",
  location: "",
  position: "",
  start_date: "",
  end_date: "Present",
  bullets: [],
});

const newEducation = (): Education => ({
  institution: "",
  location: "",
  degree: "",
  start_date: "",
  end_date: "",
  gpa: null,
  thesis: null,
  coursework: null,
});

const newSkill = (): SkillSection => ({ title: "", items: "" });

const newProject = (): Project => ({ name: "", description: "", url: null });

const newAward = (): Award => ({ title: "", issuer: null, date: null });
