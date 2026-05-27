import styles from "../userMemory.module.css";

export function UserMemoryHeader({ total }: { total: number }) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.breadcrumb}>
          <span>Workspace</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbActive}>Memory</span>
        </div>
        <h1 className={styles.title}>Memory</h1>
        <p className={styles.subtitle}>
          Edit the facts Hireable can reuse when tailoring your CV.
        </p>
      </div>
      <span className={styles.status}>
        <span className={styles.statusDot} />
        {total} saved
      </span>
    </header>
  );
}
