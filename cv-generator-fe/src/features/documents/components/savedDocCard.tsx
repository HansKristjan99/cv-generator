import { useEffect, useState } from "react";

import { Button, IconButton } from "../../../primitives/button";
import { DownloadIcon, TrashIcon } from "../../../primitives/icons";
import { cx } from "../../../utils/cx";
import styles from "../documents.module.css";

type Props = {
  name: string;
  createdAt: string;
  kind: "cv" | "cl";
  busy: boolean;
  getPdf: () => Promise<string | null>;
  onPreview: () => void;
  onDownload: () => void;
  onDelete: () => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function SavedDocCard({
  name,
  createdAt,
  kind,
  busy,
  getPdf,
  onPreview,
  onDownload,
  onDelete,
}: Props) {
  return (
    <div className={styles.card}>
      <button
        type="button"
        className={styles.thumb}
        onClick={onPreview}
        disabled={busy}
        aria-label={`Preview ${name}`}
      >
        <MiniPdfPreview getPdf={getPdf} title={name} />
        <span
          className={cx(
            styles.thumbBadge,
            kind === "cv" ? styles.thumbBadgeMint : styles.thumbBadgeSky,
          )}
        >
          {kind === "cv" ? "CV" : "COVER"}
        </span>
      </button>
      <div className={styles.cardMeta}>
        <h3 className={styles.cardTitle}>{name}</h3>
        <div className={styles.cardSub}>
          <span>{formatDate(createdAt)}</span>
        </div>
      </div>
      <div className={styles.cardActions}>
        <Button
          variant="secondary"
          size="sm"
          onClick={onDownload}
          disabled={busy}
          iconBefore={<DownloadIcon size={14} />}
        >
          Download
        </Button>
        <IconButton
          tone="danger"
          size="sm"
          label={`Delete ${name}`}
          onClick={onDelete}
          disabled={busy}
          className={styles.cardDeleteBtn}
        >
          <TrashIcon size={16} />
        </IconButton>
      </div>
    </div>
  );
}

function MiniPdfPreview({
  getPdf,
  title,
}: {
  getPdf: () => Promise<string | null>;
  title: string;
}) {
  const [pdf, setPdf] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getPdf().then((b64) => {
      if (!cancelled && b64) setPdf(b64);
    });
    return () => {
      cancelled = true;
    };
  }, [getPdf]);

  if (!pdf) return <div className={styles.miniSkeleton} aria-hidden />;

  // First-page-only PDF, hide the chrome (toolbar, sidebar, scrollbar).
  // The iframe renders A4 at 595×842pt then we scale it to fit the thumb.
  const src = `data:application/pdf;base64,${pdf}#toolbar=0&navpanes=0&scrollbar=0&view=Fit&page=1`;
  return (
    <div className={styles.miniPdfWrap} aria-hidden>
      <iframe className={styles.miniPdfFrame} src={src} title={title} />
    </div>
  );
}
