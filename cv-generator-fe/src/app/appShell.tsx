import { AppScaffold } from "./appScaffold";
import { AuthenticationProvider } from "./authenticationProvider";
import { TabSwitcher } from "./tabSwitcher";
import { useActiveTab } from "./hooks/useActiveTab";
import type { AppTab } from "./tabs";

export function AppShell({ initialTab = "cv" }: { initialTab?: AppTab }) {
  const { activeTab, selectTab, openSession } = useActiveTab(initialTab);

  return (
    <AppScaffold activeTab={activeTab} onSelectTab={selectTab} onOpenSession={openSession}>
      <AuthenticationProvider>
        <TabSwitcher activeTab={activeTab} />
      </AuthenticationProvider>
    </AppScaffold>
  );
}
