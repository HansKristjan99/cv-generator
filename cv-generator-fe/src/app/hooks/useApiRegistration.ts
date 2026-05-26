import { useEffect, useState } from "react";
import { useAuth } from "@clerk/react";

import { apiClient } from "../../api/client";
import { setAuthTokenProvider } from "../../api/auth-utils/authFetch";
import { fetchChatSessions } from "../../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch } from "../../hooks";

export type RegistrationStatus = "idle" | "loading" | "ready" | "failed";

export function useApiRegistration() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const dispatch = useAppDispatch();
  const [status, setStatus] = useState<RegistrationStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setAuthTokenProvider(null);
      setStatus("idle");
      return;
    }

    let cancelled = false;
    setAuthTokenProvider(getToken);
    setStatus("loading");
    setError(null);

    void apiClient
      .registerCurrentUser()
      .then(() => {
        if (cancelled) return;
        setStatus("ready");
        void dispatch(fetchChatSessions());
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to register user");
          setStatus("failed");
        }
      });

    return () => {
      cancelled = true;
      setAuthTokenProvider(null);
    };
  }, [dispatch, getToken, isLoaded, isSignedIn]);

  return { status, error, isLoaded, isSignedIn };
}
