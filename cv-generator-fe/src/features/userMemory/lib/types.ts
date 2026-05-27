import type {
  Award,
  EducationExperience,
  MemoryNote,
  Project,
} from "../../../api/user-memory/userMemory";

export type MemoryKind =
  | "job_experiences"
  | "education_experiences"
  | "projects"
  | "skills"
  | "awards"
  | "notes";

export type SimpleKind = Exclude<MemoryKind, "job_experiences" | "skills">;
export type SimpleItem = EducationExperience | Project | Award | MemoryNote;

export type FieldConfig = {
  name: string;
  label: string;
  required?: boolean;
  multiline?: boolean;
  maxLength?: number;
};

export type SimpleSectionConfig = {
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

export type BulletDraft = {
  id: string;
  bullet_points: string;
  relevant_technologies: string;
};

export type JobDraft = {
  id: string;
  company_name: string;
  job_title: string;
  start_date: string;
  end_date: string;
  location: string;
  bullets: BulletDraft[];
};

export type Editor = {
  kind: MemoryKind;
  id: string;
  draft: Record<string, string> | JobDraft;
  removedChildIds: string[];
};

export const NEW_ID = "__new__";
