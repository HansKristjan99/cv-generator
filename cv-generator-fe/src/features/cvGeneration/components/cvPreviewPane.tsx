import { type ReactNode, useEffect, useState } from "react";

import { Button, DownloadButton, IconButton } from "../../../primitives/button";
import type { PreviewKind } from "../../../types/chat";
import { cx } from "../../../utils/cx";
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
  onSelect: (kind: PreviewKind | null) => void;
  onEdit?: (kind: "generated_cv" | "cover_letter") => void;
  onSaveCurrent?: (kind: "generated_cv" | "cover_letter") => void;
  onAddApplication?: () => void;
  chatContent: ReactNode;
  composer: ReactNode;
};

export const CvPreviewPane = ({
  descriptors,
  selection,
  onSelect,
  onEdit,
  onSaveCurrent,
  onAddApplication,
  chatContent,
  composer,
}: CvPreviewPaneProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const selected = selection ? descriptors.find((d) => d.kind === selection) ?? null : null;
  const active = selected?.content ? selected : null;
  const isChatActive = !active;

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
          <button
            type="button"
            className={cx(styles.tab, isChatActive && styles.tabActive)}
            onClick={() => onSelect(null)}
            title="View chat"
          >
            Chat
          </button>
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
          {active?.mode === "pdf" && dataUrl ? (
            <DownloadButton href={dataUrl} downloadName={active.downloadName ?? "document.pdf"} />
          ) : null}
          {active &&
            onEdit &&
            (active.kind === "generated_cv" || active.kind === "cover_letter") &&
            active.mode === "pdf" && (
              <Button
                size="sm"
                onClick={() => onEdit(active.kind as "generated_cv" | "cover_letter")}
                title="Edit fields manually"
              >
                ✎ Edit
              </Button>
            )}
          {active &&
            onSaveCurrent &&
            (active.kind === "generated_cv" || active.kind === "cover_letter") &&
            active.mode === "pdf" && (
              <Button
                size="sm"
                onClick={() => onSaveCurrent(active.kind as "generated_cv" | "cover_letter")}
                title="Save with a custom name for later use"
              >
                ☆ Save
              </Button>
            )}
          {onAddApplication ? (
            <Button size="sm" onClick={onAddApplication} title="Add to your tracked applications">
              + Add application
            </Button>
          ) : null}
          {active && (
            <IconButton
              size="sm"
              label={isFullscreen ? "Exit full screen (Esc)" : "Full screen"}
              onClick={() => setIsFullscreen((v) => !v)}
            >
              {isFullscreen ? "⤡" : "⤢"}
            </IconButton>
          )}
        </div>
      </div>

      <div className={styles.body}>
        {isChatActive ? (
          <div className={styles.chatView}>{chatContent}</div>
        ) : active ? (
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
          </>
        ) : (
          <div className={styles.textBody}>
            <p className={styles.empty}>Nothing to preview yet.</p>
          </div>
        )}
      </div>
      <div className={styles.composerSlot}>
        {composer}
      </div>
    </aside>
  );
};
