import { useEffect, type ReactNode } from "react";

import { cx } from "../utils/cx";
import { Button } from "./button";
import { TrashIcon } from "./icons";
import styles from "./confirmDialog.module.css";

type Props = {
  title: string;
  body?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "neutral";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  title,
  body,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  tone = "danger",
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter" && !busy) onConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel, onConfirm, busy]);

  return (
    <div className={styles.scrim} onClick={onCancel}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.head}>
          <div
            className={cx(
              styles.icon,
              tone === "danger" ? styles.iconDanger : styles.iconNeutral,
            )}
          >
            <TrashIcon size={18} />
          </div>
          <div className={styles.copy}>
            <h2 className={styles.title}>{title}</h2>
            {body ? <p className={styles.body}>{body}</p> : null}
          </div>
        </div>
        <div className={styles.actions}>
          <Button variant="secondary" size="sm" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "dangerSolid" : "primary"}
            size="sm"
            onClick={onConfirm}
            disabled={busy}
            autoFocus
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
