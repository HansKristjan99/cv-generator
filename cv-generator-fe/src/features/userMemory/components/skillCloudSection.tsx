import { useState } from "react";

import type { Skill } from "../../../api/user-memory/userMemory";
import styles from "../userMemory.module.css";
import { SectionHeader } from "./sectionHeader";

type Props = {
  skills: Skill[];
  saving: boolean;
  onAdd: (name: string) => void;
  onDelete: (id: string) => void;
};

export function SkillCloudSection({ skills, saving, onAdd, onDelete }: Props) {
  const [value, setValue] = useState("");
  const existing = new Set(skills.map((skill) => skill.name.toLowerCase()));
  const trimmed = value.trim();
  const canAdd = Boolean(trimmed) && !existing.has(trimmed.toLowerCase()) && !saving;

  const add = () => {
    if (!canAdd) return;
    onAdd(trimmed);
    setValue("");
  };

  return (
    <section className={styles.section}>
      <SectionHeader title="Skills" eyebrow="Keyword cloud" count={skills.length} />
      {skills.length === 0 ? (
        <p className={styles.empty}>No skills saved yet.</p>
      ) : (
        <div className={styles.skillCloud}>
          {skills.map((skill) => (
            <span className={styles.skillChip} key={skill.id}>
              {skill.name}
              <button
                type="button"
                className={styles.skillChipRemove}
                onClick={() => onDelete(skill.id)}
                disabled={saving}
                aria-label={`Remove ${skill.name}`}
                title="Remove"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className={styles.skillAddRow}>
        <input
          className={styles.input}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add();
            }
          }}
          placeholder="Add a skill and press Enter"
        />
        <button type="button" className={styles.addButton} onClick={add} disabled={!canAdd}>
          Add skill
        </button>
      </div>
    </section>
  );
}
