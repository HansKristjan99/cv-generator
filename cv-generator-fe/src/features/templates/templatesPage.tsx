import { TemplateCard } from "./components/templateCard";
import { TemplatesHeader } from "./components/templatesHeader";
import { useTemplates } from "./hooks/useTemplates";
import styles from "./templates.module.css";

export function TemplatesPage() {
  const { templates, preferredId, loading, saving, error, select } = useTemplates();

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>Loading templates…</section>
      </main>
    );
  }

  const activeTemplate = templates.find((t) => t.id === preferredId) ?? templates[0];

  return (
    <main className={styles.page}>
      <TemplatesHeader activeTemplate={activeTemplate} />
      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.grid}>
        {templates.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            isActive={template.id === preferredId}
            saving={saving}
            onSelect={() => select(template.id)}
          />
        ))}
      </div>
    </main>
  );
}
