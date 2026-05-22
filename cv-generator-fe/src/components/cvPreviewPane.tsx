import { useEffect, useState } from "react";

import { cx } from "../utils/cx";
import styles from "./cvPreviewPane.module.css";

type PreviewPaneProps = {
  title: string;
  badge: string;
  mode: "pdf" | "text";
  content: string;
  downloadName?: string;
  onClose: () => void;
};

export const CvPreviewPane = ({
  title,
  badge,
  mode,
  content,
  downloadName = "document.pdf",
  onClose,
}: PreviewPaneProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const dataUrl = mode === "pdf" ? `data:application/pdf;base64,${content}` : null;

  useEffect(() => {
    if (!isFullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isFullscreen]);

  return (
    <aside className={cx(styles.pane, isFullscreen && styles.fullscreen)}>
      <div className={styles.header}>
        <div className={styles.heading}>
          <h2 className={styles.title}>{title}</h2>
          <span className={styles.badge}>{badge}</span>
        </div>
        <div className={styles.controls}>
          <button
            type="button"
            className={styles.control}
            onClick={() => setIsFullscreen((v) => !v)}
            aria-label={isFullscreen ? "Exit full screen" : "Full screen"}
            title={isFullscreen ? "Exit full screen (Esc)" : "Full screen"}
          >
            {isFullscreen ? "⤡" : "⤢"}
          </button>
          <button
            type="button"
            className={styles.control}
            onClick={onClose}
            aria-label="Close preview"
            title="Close preview"
          >
            ✕
          </button>
        </div>
      </div>

      {mode === "pdf" && dataUrl ? (
        <iframe className={styles.frame} src={dataUrl} title={title} />
      ) : (
        <div className={styles.textBody}>
          {content.trim() ? (
            <pre className={styles.text}>{content}</pre>
          ) : (
            <p className={styles.empty}>Nothing to show here.</p>
          )}
        </div>
      )}

      {mode === "pdf" && dataUrl ? (
        <div className={styles.footer}>
          <a className={styles.download} href={dataUrl} download={downloadName}>
            ↓ Download PDF
          </a>
        </div>
      ) : null}
    </aside>
  );
};
