import { cx } from "../../../utils/cx";
import styles from "../documents.module.css";

export type DocsTab = "all" | "cv" | "cl";

type Props = {
  cvCount: number;
  clCount: number;
  tab: DocsTab;
  onTabChange: (tab: DocsTab) => void;
};

const TAB_DEFS: Array<{ id: DocsTab; label: string; tone: string }> = [
  { id: "all", label: "All", tone: "neutral" },
  { id: "cv", label: "CVs", tone: "mint" },
  { id: "cl", label: "Cover letters", tone: "sky" },
];

export function DocumentsHeader({ cvCount, clCount, tab, onTabChange }: Props) {
  const total = cvCount + clCount;
  const counts: Record<DocsTab, number> = {
    all: total,
    cv: cvCount,
    cl: clCount,
  };
  return (
    <header className={styles.header}>
      <div className={styles.headerTop}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Workspace</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbActive}>Documents</span>
          </div>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Documents</h1>
            <span className={styles.tagline}>
              a library of every CV and cover letter Hireable has helped you write.
            </span>
          </div>
        </div>
      </div>
      <div className={styles.tabsRow} role="tablist" aria-label="Document type">
        {TAB_DEFS.map((def) => {
          const isActive = def.id === tab;
          return (
            <button
              key={def.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={cx(styles.tab, isActive && styles.tabActive)}
              onClick={() => onTabChange(def.id)}
            >
              <span className={styles.tabLabel}>{def.label}</span>
              <span
                className={cx(
                  styles.tabCount,
                  isActive && def.tone === "mint" && styles.tabCountMint,
                  isActive && def.tone === "sky" && styles.tabCountSky,
                )}
              >
                {counts[def.id]}
              </span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
