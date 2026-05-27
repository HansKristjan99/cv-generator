import type { ReactNode } from "react";

import styles from "./appShell.module.css";
import { Sidebar } from "./sidebar/sidebar";
import type { AppTab } from "./tabs";

type Props = {
  activeTab: AppTab;
  onSelectTab: (tab: AppTab) => void;
  onOpenSession: () => void;
  children: ReactNode;
};

export function AppScaffold({ activeTab, onSelectTab, onOpenSession, children }: Props) {
  return (
    <div className={styles.shell}>
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        onOpenSession={onOpenSession}
      />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
