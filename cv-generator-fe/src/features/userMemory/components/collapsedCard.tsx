import { IconButton } from "../../../primitives/button";
import { TrashIcon } from "../../../primitives/icons";
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
      <IconButton
        tone="danger"
        size="sm"
        label={`Delete ${title || "item"}`}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        disabled={saving}
        className={styles.itemDeleteBtn}
      >
        <TrashIcon size={14} />
      </IconButton>
    </div>
  );
}
