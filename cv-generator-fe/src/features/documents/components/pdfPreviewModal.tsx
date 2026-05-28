import { useEffect } from "react";

import { DownloadButton, IconButton } from "../../../primitives/button";
import { CloseIcon } from "../../../primitives/icons";
import styles from "../documents.module.css";

type Props = {
  title: string;
  pdfBase64: string | null;
  onClose: () => void;
  onDownload: () => void;
};

export function PdfPreviewModal({ title, pdfBase64, onClose, onDownload }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const dataUrl = pdfBase64 ? `data:application/pdf;base64,${pdfBase64}` : null;

  return (
    <div className={styles.previewScrim} onClick={onClose}>
      <div className={styles.previewModal} onClick={(e) => e.stopPropagation()}>
        <header className={styles.previewHead}>
          <h2 className={styles.previewTitle}>{title}</h2>
          <div className={styles.previewControls}>
            <DownloadButton onClick={onDownload} disabled={!dataUrl} />
            <IconButton label="Close preview" onClick={onClose}>
              <CloseIcon size={16} />
            </IconButton>
          </div>
        </header>
        <div className={styles.previewBody}>
          {dataUrl ? (
            <iframe className={styles.previewFrame} src={dataUrl} title={title} />
          ) : (
            <div className={styles.previewLoading}>Loading PDF…</div>
          )}
        </div>
      </div>
    </div>
  );
}
