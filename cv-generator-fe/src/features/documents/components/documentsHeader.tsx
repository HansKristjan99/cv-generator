import styles from "../documents.module.css";

export function DocumentsHeader({ cvCount, clCount }: { cvCount: number; clCount: number }) {
  const total = cvCount + clCount;
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.breadcrumb}>
          <span>Workspace</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbActive}>Documents</span>
        </div>
        <h1 className={styles.title}>Documents</h1>
        <p className={styles.subtitle}>
          {total === 0
            ? "No saved documents yet — use Save in a CV chat to keep one around."
            : `${cvCount} CV${cvCount === 1 ? "" : "s"} · ${clCount} cover letter${clCount === 1 ? "" : "s"}.`}
        </p>
      </div>
    </header>
  );
}
