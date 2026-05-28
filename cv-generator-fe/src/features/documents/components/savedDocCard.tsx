import styles from "../documents.module.css";

type Props = {
  name: string;
  createdAt: string;
  badge: string;
  busy: boolean;
  onPreview: () => void;
  onDownload: () => void;
  onDelete: () => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

export function SavedDocCard({
  name,
  createdAt,
  badge,
  busy,
  onPreview,
  onDownload,
  onDelete,
}: Props) {
  const handleDelete = () => {
    if (window.confirm(`Delete "${name}"? Applications referencing it will be unlinked.`)) {
      onDelete();
    }
  };
  return (
    <div className={styles.card}>
      <div className={styles.cardHead}>
        <span className={styles.cardBadge}>{badge}</span>
        <span className={styles.cardDate}>{formatDate(createdAt)}</span>
      </div>
      <h3 className={styles.cardTitle}>{name}</h3>
      <div className={styles.cardActions}>
        <button type="button" className={styles.primaryBtn} onClick={onPreview} disabled={busy}>
          👁 Preview
        </button>
        <button type="button" className={styles.primaryBtn} onClick={onDownload} disabled={busy}>
          ↓ Download
        </button>
        <button type="button" className={styles.dangerLink} onClick={handleDelete} disabled={busy}>
          Delete
        </button>
      </div>
    </div>
  );
}
