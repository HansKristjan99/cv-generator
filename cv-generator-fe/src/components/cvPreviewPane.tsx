import { useEffect, useState } from "react";

import type { PreviewKind } from "../types/chat";
import { cx } from "../utils/cx";
import styles from "./cvPreviewPane.module.css";

type TabDescriptor = {
  kind: PreviewKind;
  label: string;
  badge: string;
  mode: "pdf" | "text";
  content: string | null;
  downloadName?: string;
};

type CvPreviewPaneProps = {
  descriptors: TabDescriptor[];
  selection: PreviewKind | null;
  onSelect: (kind: PreviewKind) => void;
  onEdit?: (kind: "generated_cv" | "cover_letter") => void;
};

export const CvPreviewPane = ({ descriptors, selection, onSelect, onEdit }: CvPreviewPaneProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const active = descriptors.find((d) => d.kind === selection && d.content)
    ?? descriptors.find((d) => d.content)
    ?? null;

  const dataUrl =
    active?.mode === "pdf" && active.content
      ? `data:application/pdf;base64,${active.content}`
      : null;

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
        <div className={styles.tabs}>
          {descriptors.map((d) => (
            <button
              key={d.kind}
              type="button"
              className={cx(styles.tab, active?.kind === d.kind && styles.tabActive)}
              onClick={() => onSelect(d.kind)}
              disabled={!d.content}
              title={d.content ? `View ${d.label.toLowerCase()}` : `No ${d.label.toLowerCase()} yet`}
            >
              {d.label}
            </button>
          ))}
        </div>
        <div className={styles.controls}>
          {active &&
            onEdit &&
            (active.kind === "generated_cv" || active.kind === "cover_letter") &&
            active.mode === "pdf" && (
              <button
                type="button"
                className={styles.editBtn}
                onClick={() => onEdit(active.kind as "generated_cv" | "cover_letter")}
                title="Edit fields manually"
              >
                Edit
              </button>
            )}
          {active && (
            <button
              type="button"
              className={styles.control}
              onClick={() => setIsFullscreen((v) => !v)}
              aria-label={isFullscreen ? "Exit full screen" : "Full screen"}
              title={isFullscreen ? "Exit full screen (Esc)" : "Full screen"}
            >
              {isFullscreen ? "⤡" : "⤢"}
            </button>
          )}
        </div>
      </div>

      {active ? (
        <>
          {active.mode === "pdf" && dataUrl ? (
            <iframe className={styles.frame} src={dataUrl} title={active.label} />
          ) : (
            <div className={styles.textBody}>
              {active.content?.trim() ? (
                <pre className={styles.text}>{active.content}</pre>
              ) : (
                <p className={styles.empty}>Nothing to show here.</p>
              )}
            </div>
          )}

          {active.mode === "pdf" && dataUrl ? (
            <div className={styles.footer}>
              <a className={styles.download} href={dataUrl} download={active.downloadName ?? "document.pdf"}>
                ↓ Download PDF
              </a>
            </div>
          ) : null}
        </>
      ) : (
        <div className={styles.textBody}>
          <p className={styles.empty}>Nothing to preview yet.</p>
        </div>
      )}
    </aside>
  );
};
