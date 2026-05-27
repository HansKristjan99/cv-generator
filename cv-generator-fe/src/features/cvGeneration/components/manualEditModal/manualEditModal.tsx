import { useState } from "react";

import { useAppDispatch, useAppSelector } from "../../../../hooks";
import type { ClStructuredData, CvStructuredData } from "../../../../types/cv";
import { saveManualEdit } from "../../thunks/saveManualEdit";
import { ClForm } from "./clForm";
import { CvForm } from "./cvForm";
import styles from "./manualEditModal.module.css";

type Props = {
  kind: "cv" | "cover_letter";
  initialData: CvStructuredData | ClStructuredData;
  onClose: () => void;
};

export function ManualEditModal({ kind, initialData, onClose }: Props) {
  const dispatch = useAppDispatch();
  const saving = useAppSelector((s) => s.cvGeneration.manualEditStatus === "loading");
  const [draft, setDraft] = useState<CvStructuredData | ClStructuredData>(
    structuredClone(initialData),
  );

  const isCv = kind === "cv";

  const handleSave = async () => {
    const result = await dispatch(saveManualEdit({ kind, data: draft }));
    if (saveManualEdit.fulfilled.match(result)) {
      onClose();
    }
  };

  return (
    <div
      className={styles.backdrop}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={styles.panel} role="dialog" aria-modal="true">
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>{isCv ? "Edit CV" : "Edit Cover Letter"}</span>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className={styles.body}>
          {isCv ? (
            <CvForm
              data={draft as CvStructuredData}
              onChange={(patch) => setDraft((prev) => ({ ...(prev as CvStructuredData), ...patch }))}
            />
          ) : (
            <ClForm
              data={draft as ClStructuredData}
              onChange={(patch) => setDraft((prev) => ({ ...(prev as ClStructuredData), ...patch }))}
            />
          )}
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className={styles.saveBtn} onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save & re-render"}
          </button>
        </div>
      </div>
    </div>
  );
}
