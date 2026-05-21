import { type ReactNode, useEffect, useState } from "react";
import { useAuth } from "@clerk/react";

import { apiClient } from "../api/client";
import { setAuthTokenProvider } from "../api/auth-utils/authFetch";
import { LoadingPage } from "../components/loadingPage";
import {
  fetchChatSessions,
  isGeneratingSession,
  loadConversation,
  selectActiveConversation,
} from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import styles from "./authenticatedApiProvider.module.css";

type RegistrationState = "idle" | "loading" | "ready" | "failed";

export function AuthenticatedApiProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const dispatch = useAppDispatch();
  const chatSessions = useAppSelector((s) => s.cvGeneration.chatSessions);
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);
  const activeConversation = useAppSelector(selectActiveConversation);
  const hasGeneratingSession = chatSessions.some((session) => isGeneratingSession(session.status));
  const [status, setStatus] = useState<RegistrationState>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log("Loading authentication state:", { isLoaded, isSignedIn });
    if (!isLoaded || !isSignedIn) {
      setAuthTokenProvider(null);
      setStatus("idle");
      return;
    }

    console.log("User is signed in and loaded");

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

  useEffect(() => {
    if (status !== "ready") return;
    void dispatch(fetchChatSessions());
    const intervalId = window.setInterval(() => {
      void dispatch(fetchChatSessions());
    }, 60_000);
    return () => window.clearInterval(intervalId);
  }, [dispatch, status]);

  useEffect(() => {
    if (status !== "ready" || !hasGeneratingSession) return;
    const intervalId = window.setInterval(() => {
      void dispatch(fetchChatSessions());
    }, 2_000);
    return () => window.clearInterval(intervalId);
  }, [dispatch, hasGeneratingSession, status]);

  useEffect(() => {
    if (status !== "ready" || !activeSessionId || activeConversation?.generationStatus !== "loading") {
      return;
    }
    void dispatch(loadConversation(activeSessionId));
    const intervalId = window.setInterval(() => {
      void dispatch(loadConversation(activeSessionId));
    }, 2_000);
    return () => window.clearInterval(intervalId);
  }, [activeConversation?.generationStatus, activeSessionId, dispatch, status]);

  if (status === "ready") {
    return children;
  }

  if (status === "failed") {
    return (
      <main className={styles.page}>
        <section className={styles.panel}>
          <h1 className={styles.title}>Authentication failed</h1>
          <p className={styles.message}>{error}</p>
        </section>
      </main>
    );
  }

  return <LoadingPage />;
}
