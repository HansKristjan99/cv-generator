import { useMemo } from "react";

import { JobSection } from "./components/jobSection";
import { SimpleSection } from "./components/simpleSection";
import { SkillCloudSection } from "./components/skillCloudSection";
import { UserMemoryHeader } from "./components/userMemoryHeader";
import { useUserMemory } from "./hooks/useUserMemory";
import { simpleSections } from "./lib/sections";
import styles from "./userMemory.module.css";

export function UserMemoryPage() {
  const {
    memory,
    editor,
    loading,
    saving,
    error,
    setEditor,
    saveEditor,
    removeItem,
    addSkill,
  } = useUserMemory();

  const total = useMemo(() => {
    if (!memory) return 0;
    return (
      memory.job_experiences.length +
      memory.education_experiences.length +
      memory.projects.length +
      memory.skills.length +
      memory.awards.length +
      memory.notes.length
    );
  }, [memory]);

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

  const sectionProps = { editor, setEditor, saveEditor, removeItem, saving };

  return (
    <main className={styles.page}>
      <UserMemoryHeader total={total} />
      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.sections}>
        <JobSection jobs={memory.job_experiences} {...sectionProps} />
        {simpleSections.slice(0, 2).map((section) => (
          <SimpleSection key={section.kind} memory={memory} section={section} {...sectionProps} />
        ))}
        <SkillCloudSection
          skills={memory.skills}
          saving={saving}
          onAdd={addSkill}
          onDelete={(id) => removeItem("skills", id)}
        />
        {simpleSections.slice(2).map((section) => (
          <SimpleSection key={section.kind} memory={memory} section={section} {...sectionProps} />
        ))}
      </div>
    </main>
  );
}
