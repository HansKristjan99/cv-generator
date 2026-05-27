import { useAuth } from "@clerk/react";

import { RecentChats } from "../../features/cvGeneration/components/recentChats";
import styles from "../appShell.module.css";
import type { AppTab } from "../tabs";
import { AccountMenu } from "./accountMenu";
import { Brand } from "./brand";
import { TabNav } from "./tabNav";

type Props = {
  activeTab: AppTab;
  onSelectTab: (tab: AppTab) => void;
};

export function Sidebar({ activeTab, onSelectTab }: Props) {
  const { isSignedIn } = useAuth();

  return (
    <aside className={styles.sidebar} aria-label="Workspace navigation">
      <Brand />
      <TabNav activeTab={activeTab} onSelect={onSelectTab} />
      {isSignedIn ? (
        <div className={styles.recentChats}>
          <RecentChats />
        </div>
      ) : null}
      <div className={styles.footerArea}>
        <AccountMenu />
      </div>
    </aside>
  );
}
