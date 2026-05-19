import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import type {
  Award,
  EducationExperience,
  JobExperience,
  JobExperienceBullet,
  MemoryNote,
  Project,
  Skill,
  SkillCategory,
  UserMemory,
  UserMemoryPatch,
} from "../api/user-memory/userMemory";
import { cx } from "../utils/cx";
import styles from "./userMemoryPage.module.css";

type MemoryKind =
  | "job_experiences"
  | "education_experiences"
  | "projects"
  | "skill_categories"
  | "awards"
  | "notes";
type SimpleKind = Exclude<MemoryKind, "job_experiences" | "skill_categories">;
type SimpleItem = EducationExperience | Project | Award | MemoryNote;

type FieldConfig = {
  name: string;
  label: string;
  required?: boolean;
  multiline?: boolean;
  maxLength?: number;
};

type SimpleSectionConfig = {
  kind: SimpleKind;
  title: string;
  eyebrow: string;
  addLabel: string;
  empty: string;
  fields: FieldConfig[];
  summary: (item: SimpleItem) => string;
  meta: (item: SimpleItem) => string;
  blank: () => Record<string, string>;
};

type BulletDraft = {
  id: string;
  bullet_points: string;
  relevant_technologies: string;
};

type JobDraft = {
  id: string;
  company_name: string;
  job_title: string;
  start_date: string;
  end_date: string;
  location: string;
  bullets: BulletDraft[];
};

type SkillDraft = {
  id: string;
  name: string;
  proficiency: string;
};

type SkillCategoryDraft = {
  id: string;
  name: string;
  skills: SkillDraft[];
};

type Editor = {
  kind: MemoryKind;
  id: string;
  draft: Record<string, string> | JobDraft | SkillCategoryDraft;
  removedChildIds: string[];
};

const NEW_ID = "__new__";
const nullable = (value: string) => value.trim() || null;

const simpleSections: SimpleSectionConfig[] = [
  {
    kind: "education_experiences",
    title: "Education",
    eyebrow: "Schools and programs",
    addLabel: "Add education",
    empty: "No education saved yet.",
    fields: [
      { name: "degree", label: "Degree", required: true },
      { name: "institution", label: "Institution", required: true },
      { name: "field_of_study", label: "Field of study" },
      { name: "start_date", label: "Start date" },
      { name: "end_date", label: "End date" },
      { name: "description", label: "Description", multiline: true },
    ],
    summary: (item) => (item as EducationExperience).degree,
    meta: (item) => [itemField(item, "institution"), itemField(item, "field_of_study")]
      .filter(Boolean)
      .join(" · "),
    blank: () => ({
      id: "",
      degree: "",
      field_of_study: "",
      institution: "",
      start_date: "",
      end_date: "",
      description: "",
    }),
  },
  {
    kind: "projects",
    title: "Projects",
    eyebrow: "Selected work",
    addLabel: "Add project",
    empty: "No projects saved yet.",
    fields: [
      { name: "title", label: "Title", required: true },
      { name: "description", label: "Description", multiline: true },
      { name: "link", label: "Link" },
    ],
    summary: (item) => (item as Project).title,
    meta: (item) => itemField(item, "description"),
    blank: () => ({ id: "", title: "", description: "", link: "" }),
  },
  {
    kind: "awards",
    title: "Awards and Achievements",
    eyebrow: "Recognition",
    addLabel: "Add achievement",
    empty: "No awards or achievements saved yet.",
    fields: [
      { name: "title", label: "Title", required: true },
      { name: "issuer", label: "Issuer" },
      { name: "date", label: "Date" },
      { name: "description", label: "Description", multiline: true },
      { name: "link", label: "Link" },
    ],
    summary: (item) => (item as Award).title,
    meta: (item) => [itemField(item, "issuer"), itemField(item, "date")].filter(Boolean).join(" · "),
    blank: () => ({ id: "", title: "", issuer: "", date: "", description: "", link: "" }),
  },
  {
    kind: "notes",
    title: "What else should we know about you?",
    eyebrow: "Additional notes",
    addLabel: "Add note",
    empty: "No additional notes saved yet.",
    fields: [{ name: "content", label: "Note", required: true, multiline: true, maxLength: 600 }],
    summary: (item) => (item as MemoryNote).content,
    meta: (item) => `${(item as MemoryNote).content.length}/600 characters`,
    blank: () => ({ id: "", content: "" }),
  },
];

export function UserMemoryPage() {
  const [memory, setMemory] = useState<UserMemory | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void apiClient
      .getUserMemory()
      .then((data) => {
        if (!cancelled) setMemory(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load memory");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const total = useMemo(() => {
    if (!memory) return 0;
    return (
      memory.job_experiences.length +
      memory.education_experiences.length +
      memory.projects.length +
      memory.skill_categories.length +
      memory.skill_categories.reduce((count, category) => count + category.skills.length, 0) +
      memory.awards.length +
      memory.notes.length
    );
  }, [memory]);

  const saveEditor = async () => {
    if (!editor || !canSave(editor)) return;
    setSaving(true);
    setError(null);
    try {
      const next = await apiClient.updateUserMemory(buildPatch(editor));
      setMemory(next);
      setEditor(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save memory");
    } finally {
      setSaving(false);
    }
  };

  const removeItem = async (kind: MemoryKind, id: string) => {
    if (!id) return;
    setSaving(true);
    setError(null);
    try {
      const next = await apiClient.updateUserMemory({ [kind]: [{ id, delete: true }] });
      setMemory(next);
      setEditor(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove memory");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>Loading memory…</section>
      </main>
    );
  }

  if (!memory) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>{error || "Unable to load memory."}</section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Workspace</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbActive}>Memory</span>
          </div>
          <h1 className={styles.title}>Memory</h1>
          <p className={styles.subtitle}>
            Everything Hirable knows about you — edit, add, or remove at any time.
          </p>
        </div>
        <span className={styles.status}>
          <span className={styles.statusDot} />
          {total} saved
        </span>
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.sections}>
        {renderJobSection(memory.job_experiences, editor, setEditor, saveEditor, removeItem, saving)}
        {simpleSections.slice(0, 2).map((section) =>
          renderSimpleSection(memory, section, editor, setEditor, saveEditor, removeItem, saving),
        )}
        {renderSkillCategorySection(
          memory.skill_categories,
          editor,
          setEditor,
          saveEditor,
          removeItem,
          saving,
        )}
        {simpleSections.slice(2).map((section) =>
          renderSimpleSection(memory, section, editor, setEditor, saveEditor, removeItem, saving),
        )}
      </div>
    </main>
  );
}

function renderJobSection(
  jobs: JobExperience[],
  editor: Editor | null,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const isAdding = editor?.kind === "job_experiences" && editor.id === NEW_ID;
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
        {isAdding ? renderJobEditor(editor, setEditor, saveEditor, removeItem, saving) : null}
        {jobs.length === 0 && !isAdding ? <p className={styles.empty}>No roles saved yet.</p> : null}
        {jobs.map((job) => {
          const isOpen = editor?.kind === "job_experiences" && editor.id === job.id;
          if (isOpen) return renderJobEditor(editor, setEditor, saveEditor, removeItem, saving);
          return (
            <div key={job.id} className={styles.itemCard}>
              <button
                type="button"
                className={styles.itemCardEdit}
                onClick={() =>
                  setEditor({
                    kind: "job_experiences",
                    id: job.id,
                    draft: jobToDraft(job),
                    removedChildIds: [],
                  })
                }
              >
                <CollapsedItem
                  title={job.job_title}
                  meta={[job.company_name, job.location, dates(job.start_date, job.end_date)]
                    .filter(Boolean)
                    .join(" · ")}
                />
              </button>
              <button
                type="button"
                className={styles.itemCardDelete}
                onClick={() => void removeItem("job_experiences", job.id)}
                disabled={saving}
                aria-label="Delete"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function renderSkillCategorySection(
  categories: SkillCategory[],
  editor: Editor | null,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const isAdding = editor?.kind === "skill_categories" && editor.id === NEW_ID;
  return (
    <section className={styles.section}>
      <SectionHeader
        title="Skill Categories"
        eyebrow="Grouped tools and strengths"
        count={categories.length}
        addLabel="Add category"
        onAdd={() =>
          setEditor({
            kind: "skill_categories",
            id: NEW_ID,
            draft: blankSkillCategory(),
            removedChildIds: [],
          })
        }
      />
      <div className={styles.itemList}>
        {isAdding ? renderSkillCategoryEditor(editor, setEditor, saveEditor, removeItem, saving) : null}
        {categories.length === 0 && !isAdding ? (
          <p className={styles.empty}>No skill categories saved yet.</p>
        ) : null}
        {categories.map((category) => {
          const isOpen = editor?.kind === "skill_categories" && editor.id === category.id;
          if (isOpen) {
            return renderSkillCategoryEditor(editor, setEditor, saveEditor, removeItem, saving);
          }
          return (
            <div key={category.id} className={styles.itemCard}>
              <button
                type="button"
                className={styles.itemCardEdit}
                onClick={() =>
                  setEditor({
                    kind: "skill_categories",
                    id: category.id,
                    draft: skillCategoryToDraft(category),
                    removedChildIds: [],
                  })
                }
              >
                <CollapsedItem
                  title={category.name}
                  meta={
                    category.skills.length
                      ? category.skills.map((skill) => skill.name).join(", ")
                      : "No skills yet"
                  }
                />
              </button>
              <button
                type="button"
                className={styles.itemCardDelete}
                onClick={() => void removeItem("skill_categories", category.id)}
                disabled={saving}
                aria-label="Delete"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function renderSimpleSection(
  memory: UserMemory,
  section: SimpleSectionConfig,
  editor: Editor | null,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const items = memory[section.kind] as SimpleItem[];
  const isAdding = editor?.kind === section.kind && editor.id === NEW_ID;
  return (
    <section className={styles.section} key={section.kind}>
      <SectionHeader
        title={section.title}
        eyebrow={section.eyebrow}
        count={items.length}
        addLabel={section.addLabel}
        onAdd={() =>
          setEditor({
            kind: section.kind,
            id: NEW_ID,
            draft: section.blank(),
            removedChildIds: [],
          })
        }
      />
      <div className={styles.itemList}>
        {isAdding ? renderSimpleEditor(section, editor, setEditor, saveEditor, removeItem, saving) : null}
        {items.length === 0 && !isAdding ? <p className={styles.empty}>{section.empty}</p> : null}
        {items.map((item) => {
          const isOpen = editor?.kind === section.kind && editor.id === item.id;
          if (isOpen) {
            return renderSimpleEditor(section, editor, setEditor, saveEditor, removeItem, saving);
          }
          return (
            <div key={item.id} className={styles.itemCard}>
              <button
                type="button"
                className={styles.itemCardEdit}
                onClick={() =>
                  setEditor({
                    kind: section.kind,
                    id: item.id,
                    draft: simpleToDraft(item, section.fields),
                    removedChildIds: [],
                  })
                }
              >
                <CollapsedItem title={section.summary(item)} meta={section.meta(item)} />
              </button>
              <button
                type="button"
                className={styles.itemCardDelete}
                onClick={() => void removeItem(section.kind, item.id)}
                disabled={saving}
                aria-label="Delete"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function renderSkillCategoryEditor(
  editor: Editor,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const draft = editor.draft as SkillCategoryDraft;
  const setDraft = (next: SkillCategoryDraft) => setEditor({ ...editor, draft: next });
  return (
    <article className={cx(styles.itemCard, styles.itemCardOpen)} key={`skill-category:${editor.id}`}>
      <div className={styles.editorHead}>
        <div>
          <p className={styles.editorEyebrow}>{editor.id === NEW_ID ? "New" : "Editing"}</p>
          <h3 className={styles.editorTitle}>Skill Category</h3>
        </div>
      </div>

      <div className={styles.fieldGrid}>
        <Field
          field={{ name: "name", label: "Category name", required: true }}
          value={draft.name}
          onChange={(value) => setDraft({ ...draft, name: value })}
        />
      </div>

      <div className={styles.bullets}>
        <div className={styles.bulletsHead}>
          <span>Skills</span>
          <button
            type="button"
            className={styles.inlineButton}
            onClick={() =>
              setDraft({
                ...draft,
                skills: [...draft.skills, { id: "", name: "", proficiency: "" }],
              })
            }
          >
            Add skill
          </button>
        </div>
        {draft.skills.length === 0 ? <p className={styles.emptySmall}>No skills yet.</p> : null}
        {draft.skills.map((skill, index) => (
          <div className={styles.skillEditor} key={`${skill.id || "new"}:${index}`}>
            <input
              className={styles.input}
              value={skill.name}
              onChange={(event) => updateSkill(draft, setDraft, index, "name", event.target.value)}
              placeholder="Skill"
            />
            <input
              className={styles.input}
              value={skill.proficiency}
              onChange={(event) => updateSkill(draft, setDraft, index, "proficiency", event.target.value)}
              placeholder="Context"
            />
            <button
              type="button"
              className={styles.inlineDanger}
              onClick={() => {
                setEditor({
                  ...editor,
                  draft: {
                    ...draft,
                    skills: draft.skills.filter((_, i) => i !== index),
                  },
                  removedChildIds: skill.id
                    ? [...editor.removedChildIds, skill.id]
                    : editor.removedChildIds,
                });
              }}
            >
              Remove skill
            </button>
          </div>
        ))}
      </div>

      <EditorActions
        canSave={canSave(editor)}
        saving={saving}
        canRemove={editor.id !== NEW_ID}
        onSave={saveEditor}
        onCancel={() => setEditor(null)}
        onRemove={() => removeItem("skill_categories", editor.id)}
      />
    </article>
  );
}

function renderSimpleEditor(
  section: SimpleSectionConfig,
  editor: Editor,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const draft = editor.draft as Record<string, string>;
  return (
    <article className={cx(styles.itemCard, styles.itemCardOpen)} key={`${section.kind}:${editor.id}`}>
      <div className={styles.editorHead}>
        <div>
          <p className={styles.editorEyebrow}>{editor.id === NEW_ID ? "New" : "Editing"}</p>
          <h3 className={styles.editorTitle}>{section.title}</h3>
        </div>
      </div>

      <div className={styles.fieldGrid}>
        {section.fields.map((field) => (
          <Field
            key={field.name}
            field={field}
            value={draft[field.name] ?? ""}
            onChange={(value) =>
              setEditor({
                ...editor,
                draft: { ...draft, [field.name]: value },
              })
            }
          />
        ))}
      </div>

      <EditorActions
        canSave={canSave(editor)}
        saving={saving}
        canRemove={editor.id !== NEW_ID}
        onSave={saveEditor}
        onCancel={() => setEditor(null)}
        onRemove={() => removeItem(section.kind, editor.id)}
      />
    </article>
  );
}

function renderJobEditor(
  editor: Editor,
  setEditor: (editor: Editor | null) => void,
  saveEditor: () => void,
  removeItem: (kind: MemoryKind, id: string) => void,
  saving: boolean,
) {
  const draft = editor.draft as JobDraft;
  const setDraft = (next: JobDraft) => setEditor({ ...editor, draft: next });
  return (
    <article className={cx(styles.itemCard, styles.itemCardOpen)} key={`job:${editor.id}`}>
      <div className={styles.editorHead}>
        <div>
          <p className={styles.editorEyebrow}>{editor.id === NEW_ID ? "New" : "Editing"}</p>
          <h3 className={styles.editorTitle}>Job Experience</h3>
        </div>
      </div>

      <div className={styles.fieldGrid}>
        {[
          { name: "company_name", label: "Company", required: true },
          { name: "job_title", label: "Job title", required: true },
          { name: "location", label: "Location" },
          { name: "start_date", label: "Start date" },
          { name: "end_date", label: "End date" },
        ].map((field) => (
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
                bullets: [...draft.bullets, { id: "", bullet_points: "", relevant_technologies: "" }],
              })
            }
          >
            Add bullet
          </button>
        </div>
        {draft.bullets.length === 0 ? <p className={styles.emptySmall}>No bullets yet.</p> : null}
        {draft.bullets.map((bullet, index) => (
          <div className={styles.bulletEditor} key={`${bullet.id || "new"}:${index}`}>
            <textarea
              className={styles.textarea}
              value={bullet.bullet_points}
              onChange={(event) => updateBullet(draft, setDraft, index, "bullet_points", event.target.value)}
              rows={2}
              placeholder="Achievement or responsibility"
            />
            <input
              className={styles.input}
              value={bullet.relevant_technologies}
              onChange={(event) =>
                updateBullet(draft, setDraft, index, "relevant_technologies", event.target.value)
              }
              placeholder="Relevant technologies"
            />
            <button
              type="button"
              className={styles.inlineDanger}
              onClick={() => {
                setEditor({
                  ...editor,
                  draft: {
                    ...draft,
                    bullets: draft.bullets.filter((_, i) => i !== index),
                  },
                  removedChildIds: bullet.id
                    ? [...editor.removedChildIds, bullet.id]
                    : editor.removedChildIds,
                });
              }}
            >
              Remove bullet
            </button>
          </div>
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

function SectionHeader({
  title,
  eyebrow,
  count,
  addLabel,
  onAdd,
}: {
  title: string;
  eyebrow: string;
  count: number;
  addLabel: string;
  onAdd: () => void;
}) {
  return (
    <header className={styles.sectionHeader}>
      <div>
        <p className={styles.sectionEyebrow}>{eyebrow}</p>
        <h2 className={styles.sectionTitle}>{title}</h2>
      </div>
      <div className={styles.sectionActions}>
        <span className={styles.count}>{count}</span>
        <button type="button" className={styles.addButton} onClick={onAdd}>
          {addLabel}
        </button>
      </div>
    </header>
  );
}

function CollapsedItem({ title, meta }: { title: string; meta: string }) {
  return (
    <>
      <span className={styles.itemTitle}>{title || "Untitled"}</span>
      {meta ? <span className={styles.itemMeta}>{meta}</span> : null}
    </>
  );
}

function Field({
  field,
  value,
  onChange,
}: {
  field: FieldConfig;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = `memory-${field.name}`;
  return (
    <label className={cx(styles.field, field.multiline && styles.fieldWide)} htmlFor={id}>
      <span className={styles.label}>
        {field.label}
        {field.required ? <span className={styles.required}>Required</span> : null}
      </span>
      {field.multiline ? (
        <textarea
          id={id}
          className={styles.textarea}
          value={value}
          maxLength={field.maxLength}
          onChange={(event) => onChange(event.target.value)}
          rows={field.maxLength ? 4 : 3}
        />
      ) : (
        <input
          id={id}
          className={styles.input}
          value={value}
          maxLength={field.maxLength}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {field.maxLength ? (
        <span className={styles.charCount}>
          {value.length}/{field.maxLength}
        </span>
      ) : null}
    </label>
  );
}

function EditorActions({
  canSave,
  saving,
  canRemove,
  onSave,
  onCancel,
  onRemove,
}: {
  canSave: boolean;
  saving: boolean;
  canRemove: boolean;
  onSave: () => void;
  onCancel: () => void;
  onRemove: () => void;
}) {
  return (
    <footer className={styles.editorActions}>
      <div>
        {canRemove ? (
          <button type="button" className={styles.removeButton} onClick={onRemove} disabled={saving}>
            Remove
          </button>
        ) : null}
      </div>
      <div className={styles.editorActionGroup}>
        <button type="button" className={styles.cancelButton} onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="button" className={styles.saveButton} onClick={onSave} disabled={!canSave || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </footer>
  );
}

function jobToDraft(job: JobExperience): JobDraft {
  return {
    id: job.id,
    company_name: job.company_name,
    job_title: job.job_title,
    start_date: job.start_date ?? "",
    end_date: job.end_date ?? "",
    location: job.location ?? "",
    bullets: job.bullets.map(bulletToDraft),
  };
}

function bulletToDraft(bullet: JobExperienceBullet): BulletDraft {
  return {
    id: bullet.id,
    bullet_points: bullet.bullet_points,
    relevant_technologies: bullet.relevant_technologies ?? "",
  };
}

function skillCategoryToDraft(category: SkillCategory): SkillCategoryDraft {
  return {
    id: category.id,
    name: category.name,
    skills: category.skills.map(skillToDraft),
  };
}

function skillToDraft(skill: Skill): SkillDraft {
  return {
    id: skill.id,
    name: skill.name,
    proficiency: skill.proficiency ?? "",
  };
}

function blankJob(): JobDraft {
  return {
    id: "",
    company_name: "",
    job_title: "",
    start_date: "",
    end_date: "",
    location: "",
    bullets: [],
  };
}

function blankSkillCategory(): SkillCategoryDraft {
  return {
    id: "",
    name: "",
    skills: [],
  };
}

function simpleToDraft(item: SimpleItem, fields: FieldConfig[]): Record<string, string> {
  return {
    id: item.id,
    ...Object.fromEntries(fields.map((field) => [field.name, itemField(item, field.name)])),
  };
}

function itemField(item: SimpleItem, field: string): string {
  const value = (item as unknown as Record<string, string | null>)[field];
  return value ?? "";
}

function updateBullet(
  draft: JobDraft,
  setDraft: (draft: JobDraft) => void,
  index: number,
  field: keyof Omit<BulletDraft, "id">,
  value: string,
) {
  setDraft({
    ...draft,
    bullets: draft.bullets.map((bullet, i) => (i === index ? { ...bullet, [field]: value } : bullet)),
  });
}

function updateSkill(
  draft: SkillCategoryDraft,
  setDraft: (draft: SkillCategoryDraft) => void,
  index: number,
  field: keyof Omit<SkillDraft, "id">,
  value: string,
) {
  setDraft({
    ...draft,
    skills: draft.skills.map((skill, i) => (i === index ? { ...skill, [field]: value } : skill)),
  });
}

function canSave(editor: Editor): boolean {
  if (editor.kind === "job_experiences") {
    const draft = editor.draft as JobDraft;
    return (
      Boolean(draft.company_name.trim()) &&
      Boolean(draft.job_title.trim()) &&
      draft.bullets.every((bullet) => Boolean(bullet.bullet_points.trim()))
    );
  }

  if (editor.kind === "skill_categories") {
    const draft = editor.draft as SkillCategoryDraft;
    return Boolean(draft.name.trim()) && draft.skills.every((skill) => Boolean(skill.name.trim()));
  }

  const section = simpleSections.find((item) => item.kind === editor.kind);
  if (!section) return false;
  const draft = editor.draft as Record<string, string>;
  return section.fields.every((field) => {
    if (field.maxLength && (draft[field.name] ?? "").length > field.maxLength) return false;
    return !field.required || Boolean((draft[field.name] ?? "").trim());
  });
}

function buildPatch(editor: Editor): UserMemoryPatch {
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

  if (editor.kind === "skill_categories") {
    const draft = editor.draft as SkillCategoryDraft;
    return {
      skill_categories: [
        {
          id: draft.id || null,
          name: draft.name.trim(),
          skills: [
            ...draft.skills.map((skill) => ({
              id: skill.id || null,
              name: skill.name.trim(),
              proficiency: nullable(skill.proficiency),
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

function dates(start: string | null, end: string | null): string {
  return [start, end].filter(Boolean).join(" - ");
}
