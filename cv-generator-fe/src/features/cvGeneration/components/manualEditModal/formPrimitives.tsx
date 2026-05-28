import type { ReactNode } from "react";

import { Button, IconButton } from "../../../../primitives/button";
import { TrashIcon } from "../../../../primitives/icons";
import styles from "./manualEditModal.module.css";

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}

export function FieldRow({ children }: { children: ReactNode }) {
  return <div className={styles.fieldRow}>{children}</div>;
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  rows?: number;
};

export function Field({ label, value, onChange, multiline = false, rows = 3 }: FieldProps) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      {multiline ? (
        <textarea
          className={styles.input}
          value={value}
          rows={rows}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          type="text"
          className={styles.input}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

type ListEditorProps<T> = {
  items: T[];
  onChange: (items: T[]) => void;
  newItem: () => T;
  renderItem: (
    item: T,
    idx: number,
    onItemChange: (updated: T) => void,
    onRemove: () => void,
  ) => ReactNode;
};

export function ListEditor<T>({ items, onChange, newItem, renderItem }: ListEditorProps<T>) {
  return (
    <div className={styles.listEditor}>
      {items.map((item, idx) =>
        renderItem(
          item,
          idx,
          (updated) => {
            const next = [...items];
            next[idx] = updated;
            onChange(next);
          },
          () => onChange(items.filter((_, i) => i !== idx)),
        ),
      )}
      <Button
        size="sm"
        className={styles.listEditorAdd}
        onClick={() => onChange([...items, newItem()])}
      >
        + Add
      </Button>
    </div>
  );
}

export function ItemCard({ onRemove, children }: { onRemove: () => void; children: ReactNode }) {
  return (
    <div className={styles.itemCard}>
      <div className={styles.itemCardContent}>{children}</div>
      <IconButton
        tone="danger"
        size="sm"
        label="Remove"
        onClick={onRemove}
        className={styles.itemCardRemove}
      >
        <TrashIcon size={14} />
      </IconButton>
    </div>
  );
}
