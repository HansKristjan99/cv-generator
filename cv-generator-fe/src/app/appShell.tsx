import { AppScaffold } from "./appScaffold";
import { AuthenticationProvider } from "./authenticationProvider";
import { TabSwitcher } from "./tabSwitcher";
import { useAppLocation } from "./hooks/useAppLocation";
import type { AppTab } from "./tabs";

export function AppShell({ initialTab = "cv" }: { initialTab?: AppTab }) {
  const { activeTab, activeSessionId, selectTab } = useAppLocation(initialTab);

  return (
    <AppScaffold activeTab={activeTab} onSelectTab={selectTab}>
      <AuthenticationProvider>
        <TabSwitcher activeTab={activeTab} activeSessionId={activeSessionId} />
      </AuthenticationProvider>
    </AppScaffold>
  );
}
