import { cx } from "../../../utils/cx";
import type { FieldConfig } from "../lib/types";
import styles from "../userMemory.module.css";

type Props = {
  field: FieldConfig;
  value: string;
  onChange: (value: string) => void;
};

export function Field({ field, value, onChange }: Props) {
  const id = `memory-${field.name}`;
  return (
    <label className={cx(styles.field, field.multiline && styles.fieldWide)} htmlFor={id}>
      <span className={styles.label}>
        {field.label}
        {field.required ? <span className={styles.required}>Required</span> : null}
      </span>
      {field.multiline ? (
        <textarea
          id={id}
          className={styles.textarea}
          value={value}
          maxLength={field.maxLength}
          onChange={(event) => onChange(event.target.value)}
          rows={field.maxLength ? 4 : 3}
        />
      ) : (
        <input
          id={id}
          className={styles.input}
          value={value}
          maxLength={field.maxLength}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {field.maxLength ? (
        <span className={styles.charCount}>
          {value.length}/{field.maxLength}
        </span>
      ) : null}
    </label>
  );
}
