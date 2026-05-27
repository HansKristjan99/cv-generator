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
          <button type="button" className={styles.removeButton} onClick={onRemove} disabled={saving}>
            Remove
          </button>
        ) : null}
      </div>
      <div className={styles.editorActionGroup}>
        <button type="button" className={styles.cancelButton} onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="button" className={styles.saveButton} onClick={onSave} disabled={!canSave || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </footer>
  );
}
