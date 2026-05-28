import { Button } from "../../../primitives/button";
import { TrashIcon } from "../../../primitives/icons";
import styles from "../userMemory.module.css";

type Props = {
  canSave: boolean;
  saving: boolean;
  canRemove: boolean;
  onSave: () => void;
  onCancel: () => void;
  onRemove: () => void;
};

export function EditorActions({
  canSave,
  saving,
  canRemove,
  onSave,
  onCancel,
  onRemove,
}: Props) {
  return (
    <footer className={styles.editorActions}>
      <div>
        {canRemove ? (
          <Button
            variant="danger"
            size="md"
            onClick={onRemove}
            disabled={saving}
            iconBefore={<TrashIcon size={14} />}
          >
            Remove
          </Button>
        ) : null}
      </div>
      <div className={styles.editorActionGroup}>
        <Button variant="secondary" size="md" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button variant="primary" size="md" onClick={onSave} disabled={!canSave || saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </footer>
  );
}
