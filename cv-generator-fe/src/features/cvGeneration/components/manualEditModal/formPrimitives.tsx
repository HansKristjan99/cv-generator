import type { ReactNode } from "react";

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
      <button type="button" className={styles.addBtn} onClick={() => onChange([...items, newItem()])}>
        + Add
      </button>
    </div>
  );
}

export function ItemCard({ onRemove, children }: { onRemove: () => void; children: ReactNode }) {
  return (
    <div className={styles.itemCard}>
      <div className={styles.itemCardContent}>{children}</div>
      <button type="button" className={styles.removeBtn} onClick={onRemove} aria-label="Remove">
        Remove
      </button>
    </div>
  );
}
