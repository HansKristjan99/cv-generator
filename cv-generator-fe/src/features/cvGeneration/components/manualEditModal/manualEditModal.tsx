import { useState } from "react";

import { useAppDispatch, useAppSelector } from "../../../../hooks";
import { Button, IconButton } from "../../../../primitives/button";
import { CloseIcon } from "../../../../primitives/icons";
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
          <IconButton label="Close" onClick={onClose}>
            <CloseIcon size={16} />
          </IconButton>
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
          <Button onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save & re-render"}
          </Button>
        </div>
      </div>
    </div>
  );
}
