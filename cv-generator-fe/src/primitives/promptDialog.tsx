import { useEffect, useRef, useState } from "react";

import styles from "./promptDialog.module.css";

type Props = {
  title: string;
  defaultValue?: string;
  placeholder?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onSubmit: (value: string) => void;
  onCancel: () => void;
};

export function PromptDialog({
  title,
  defaultValue = "",
  placeholder,
  confirmLabel = "OK",
  cancelLabel = "Cancel",
  onSubmit,
  onCancel,
}: Props) {
  const [value, setValue] = useState(defaultValue);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  return (
    <div className={styles.scrim} onClick={onCancel}>
      <form
        className={styles.dialog}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 className={styles.title}>{title}</h2>
        <input
          ref={inputRef}
          type="text"
          className={styles.input}
          value={value}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
        />
        <div className={styles.actions}>
          <button type="button" className={styles.cancel} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="submit" className={styles.confirm} disabled={!value.trim()}>
            {confirmLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
