import type { SavedCl, SavedCv } from "../../../api/job-applications/jobApplications";
import styles from "../jobApplications.module.css";

type Props = {
  cvs: SavedCv[];
  cls: SavedCl[];
  saving: boolean;
  onDeleteCv: (id: string) => Promise<void>;
  onDeleteCl: (id: string) => Promise<void>;
  onClose: () => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

export function SavedDocsModal({ cvs, cls, saving, onDeleteCv, onDeleteCl, onClose }: Props) {
  return (
    <div className={styles.modalScrim} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h2 className={styles.modalTitle}>Saved documents</h2>
        <p className={styles.modalHint}>
          CVs and cover letters are saved when you click <b>Save</b> in a chat or start
          tracking an application. They&apos;re available to attach to manual applications.
        </p>

        <section className={styles.docSection}>
          <h3 className={styles.docHeading}>CVs ({cvs.length})</h3>
          {cvs.length === 0 ? (
            <p className={styles.docEmpty}>No saved CVs yet.</p>
          ) : (
            <ul className={styles.docList}>
              {cvs.map((c) => (
                <li key={c.id} className={styles.docRow}>
                  <span className={styles.docName}>{c.name}</span>
                  <span className={styles.docDate}>{formatDate(c.created_at)}</span>
                  <button
                    type="button"
                    className={styles.linkDanger}
                    onClick={() => onDeleteCv(c.id)}
                    disabled={saving}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={styles.docSection}>
          <h3 className={styles.docHeading}>Cover letters ({cls.length})</h3>
          {cls.length === 0 ? (
            <p className={styles.docEmpty}>No saved cover letters yet.</p>
          ) : (
            <ul className={styles.docList}>
              {cls.map((c) => (
                <li key={c.id} className={styles.docRow}>
                  <span className={styles.docName}>{c.name}</span>
                  <span className={styles.docDate}>{formatDate(c.created_at)}</span>
                  <button
                    type="button"
                    className={styles.linkDanger}
                    onClick={() => onDeleteCl(c.id)}
                    disabled={saving}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className={styles.modalActions}>
          <span className={styles.spacer} />
          <button type="button" className={styles.secondaryBtn} onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
