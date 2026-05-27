import { cx } from "../../utils/cx";
import styles from "../appShell.module.css";
import { SIDEBAR_TABS, type AppTab } from "../tabs";

type Props = {
  activeTab: AppTab;
  onSelect: (tab: AppTab) => void;
};

export function TabNav({ activeTab, onSelect }: Props) {
  return (
    <nav className={styles.tabs} aria-label="Workspace tabs">
      {SIDEBAR_TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            className={cx(styles.tab, isActive && styles.tabActive)}
            aria-current={isActive ? "page" : undefined}
            onClick={() => onSelect(tab.id)}
          >
            <span className={styles.tabText}>
              <span className={styles.tabLabel}>{tab.label}</span>
            </span>
            {isActive ? <span className={styles.tabDot} /> : null}
          </button>
        );
      })}
    </nav>
  );
}
