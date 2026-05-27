import type { ReactNode } from "react";

import styles from "./appShell.module.css";
import { Sidebar } from "./sidebar/sidebar";
import type { AppTab } from "./tabs";

type Props = {
  activeTab: AppTab;
  onSelectTab: (tab: AppTab) => void;
  children: ReactNode;
};

export function AppScaffold({ activeTab, onSelectTab, children }: Props) {
  return (
    <div className={styles.shell}>
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
