import { useCallback } from "react";
import { useSearchParams } from "react-router";

import { isAppTab, type AppTab } from "../tabs";

export type AppLocation = {
  activeTab: AppTab;
  activeSessionId: string | null;
  selectTab: (tab: AppTab) => void;
  openSession: (sessionId: string) => void;
};

export function useAppLocation(initialTab: AppTab = "cv"): AppLocation {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab = isAppTab(tabParam) ? tabParam : initialTab;
  const activeSessionId = searchParams.get("sid");

  const selectTab = useCallback(
    (tab: AppTab) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("tab", tab);
          next.delete("checkout_session_id");
          if (tab !== "session") next.delete("sid");
          return next;
        },
        { replace: false },
      );
    },
    [setSearchParams],
  );

  const openSession = useCallback(
    (sessionId: string) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("tab", "session");
          next.set("sid", sessionId);
          next.delete("checkout_session_id");
          return next;
        },
        { replace: false },
      );
    },
    [setSearchParams],
  );

  return { activeTab, activeSessionId, selectTab, openSession };
}
