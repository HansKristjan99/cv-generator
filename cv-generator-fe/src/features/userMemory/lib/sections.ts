import type {
  Award,
  EducationExperience,
  MemoryNote,
  Project,
} from "../../../api/user-memory/userMemory";
import { itemField } from "./itemField";
import type { SimpleSectionConfig } from "./types";

export const simpleSections: SimpleSectionConfig[] = [
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
    meta: (item) =>
      [itemField(item, "institution"), itemField(item, "field_of_study")]
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
    meta: (item) =>
      [itemField(item, "issuer"), itemField(item, "date")].filter(Boolean).join(" · "),
    blank: () => ({ id: "", title: "", issuer: "", date: "", description: "", link: "" }),
  },
  {
    kind: "notes",
    title: "What else should we know about you?",
    eyebrow: "Additional notes",
    addLabel: "Add note",
    empty: "No additional notes saved yet.",
    fields: [
      { name: "content", label: "Note", required: true, multiline: true, maxLength: 600 },
    ],
    summary: (item) => (item as MemoryNote).content,
    meta: (item) => `${(item as MemoryNote).content.length}/600 characters`,
    blank: () => ({ id: "", content: "" }),
  },
];
