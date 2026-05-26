import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";

import { useAppSelector } from "../../hooks";
import { isAppTab, type AppTab } from "../tabs";

export function useActiveTab(initialTab: AppTab) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<AppTab>(
    isAppTab(tabParam) ? tabParam : initialTab,
  );

  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);
  const setupStatus = useAppSelector((s) => s.cvGeneration.setupStatus);
  const prevSetupStatus = useRef(setupStatus);

  useEffect(() => {
    if (prevSetupStatus.current === "loading" && setupStatus === "idle" && activeSessionId) {
      setActiveTab("session");
    }
    prevSetupStatus.current = setupStatus;
  }, [setupStatus, activeSessionId]);

  const selectTab = useCallback(
    (tabId: AppTab) => {
      setActiveTab(tabId);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set("tab", tabId);
      nextParams.delete("checkout_session_id");
      setSearchParams(nextParams);
    },
    [searchParams, setSearchParams],
  );

  return { activeTab, selectTab, openSession: () => setActiveTab("session") };
}
