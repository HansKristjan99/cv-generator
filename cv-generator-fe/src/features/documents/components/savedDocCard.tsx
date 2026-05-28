import { cx } from "../../../utils/cx";
import styles from "../documents.module.css";

type Props = {
  name: string;
  createdAt: string;
  kind: "cv" | "cl";
  busy: boolean;
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
  onPreview,
  onDownload,
  onDelete,
}: Props) {
  const handleDelete = () => {
    if (window.confirm(`Delete "${name}"? Applications referencing it will be unlinked.`)) {
      onDelete();
    }
  };
  return (
    <div className={styles.card}>
      <button
        type="button"
        className={styles.thumb}
        onClick={onPreview}
        disabled={busy}
        aria-label={`Preview ${name}`}
      >
        <MiniDoc kind={kind} />
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
        <button type="button" className={styles.primaryBtn} onClick={onDownload} disabled={busy}>
          ↓ Download
        </button>
        <button type="button" className={styles.dangerLink} onClick={handleDelete} disabled={busy}>
          Delete
        </button>
      </div>
    </div>
  );
}

function MiniDoc({ kind }: { kind: "cv" | "cl" }) {
  if (kind === "cv") {
    return (
      <div className={styles.miniDoc}>
        <div className={styles.miniDocBanner}>
          <div className={styles.miniDocName}>HANS K. VERI</div>
          <div className={styles.miniDocRole}>Full-Stack Engineer</div>
        </div>
        <div className={styles.miniDocSection}>SUMMARY</div>
        <div className={styles.miniDocLine} />
        <div className={styles.miniDocLine} style={{ width: "82%" }} />
        <div className={styles.miniDocSection}>EXPERIENCE</div>
        <div className={styles.miniDocRow}>
          <span className={styles.miniDocBold}>Intonate</span>
          <span className={styles.miniDocDim}>2022–pres</span>
        </div>
        <div className={styles.miniDocLine} />
        <div className={styles.miniDocLine} style={{ width: "70%" }} />
        <div className={styles.miniDocRow}>
          <span className={styles.miniDocBold}>Twilio</span>
          <span className={styles.miniDocDim}>2019–22</span>
        </div>
        <div className={styles.miniDocLine} />
        <div className={styles.miniDocSection}>SKILLS</div>
        <div className={styles.miniDocLine} style={{ width: "60%" }} />
      </div>
    );
  }
  return (
    <div className={styles.miniDoc}>
      <div className={styles.miniDocBanner}>
        <div className={styles.miniDocName}>HANS K. VERI</div>
      </div>
      <div className={styles.miniDocDim} style={{ marginTop: 4 }}>
        Dear Hiring Team,
      </div>
      <div className={styles.miniDocLine} style={{ marginTop: 5 }} />
      <div className={styles.miniDocLine} />
      <div className={styles.miniDocLine} style={{ width: "85%" }} />
      <div className={styles.miniDocLine} style={{ marginTop: 4 }} />
      <div className={styles.miniDocLine} />
      <div className={styles.miniDocLine} style={{ width: "70%" }} />
      <div className={styles.miniDocDim} style={{ marginTop: 5 }}>
        Sincerely,
      </div>
      <div className={styles.miniDocBold} style={{ marginTop: 2 }}>
        Hans K. Veri
      </div>
    </div>
  );
}
