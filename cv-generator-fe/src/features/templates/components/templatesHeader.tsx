import type { Template } from "../../../api/templates/getTemplates";
import styles from "../templates.module.css";

export function TemplatesHeader({ activeTemplate }: { activeTemplate: Template | undefined }) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.breadcrumb}>
          <span>Workspace</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbActive}>Templates</span>
        </div>
        <h1 className={styles.title}>Templates</h1>
        <p className={styles.subtitle}>
          Choose a default CV layout. Your selection is applied on every new generation.
        </p>
      </div>
      {activeTemplate ? (
        <span className={styles.status}>
          <span className={styles.statusDot} />
          {activeTemplate.name}
        </span>
      ) : null}
    </header>
  );
}
