import styles from "../jobApplications.module.css";

type Props = {
  total: number;
  onNew: () => void;
};

export function ApplicationsHeader({ total, onNew }: Props) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.breadcrumb}>
          <span>Workspace</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbActive}>Applications</span>
        </div>
        <h1 className={styles.title}>Applications</h1>
        <p className={styles.subtitle}>
          {total === 0
            ? "No applications yet — add one or start tracking from a CV chat."
            : `${total} ${total === 1 ? "application" : "applications"} tracked.`}
        </p>
      </div>
      <div className={styles.headerActions}>
        <button type="button" className={styles.primaryBtn} onClick={onNew}>
          + New application
        </button>
      </div>
    </header>
  );
}
