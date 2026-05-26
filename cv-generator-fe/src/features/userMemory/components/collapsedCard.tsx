import styles from "../userMemory.module.css";

type Props = {
  title: string;
  meta: string;
  saving: boolean;
  onOpen: () => void;
  onDelete: () => void;
};

export function CollapsedCard({ title, meta, saving, onOpen, onDelete }: Props) {
  return (
    <div className={styles.itemCard}>
      <button type="button" className={styles.itemCardBody} onClick={onOpen}>
        <span className={styles.itemTitle}>{title || "Untitled"}</span>
        {meta ? <span className={styles.itemMeta}>{meta}</span> : null}
      </button>
      <button
        type="button"
        className={styles.deleteButton}
        onClick={onDelete}
        disabled={saving}
        aria-label={`Delete ${title || "item"}`}
        title="Delete"
      >
        ×
      </button>
    </div>
  );
}
