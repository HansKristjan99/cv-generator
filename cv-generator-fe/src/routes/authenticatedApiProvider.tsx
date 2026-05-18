import { type ReactNode, useEffect, useState } from "react";
import { useAuth } from "@clerk/react";

import { apiClient } from "../api/client";
import { setAuthTokenProvider } from "../api/auth-utils/authFetch";
import { LoadingPage } from "../components/loadingPage";
import styles from "./authenticatedApiProvider.module.css";

type RegistrationState = "idle" | "loading" | "ready" | "failed";

export function AuthenticatedApiProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
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
        if (!cancelled) setStatus("ready");
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
  }, [getToken, isLoaded, isSignedIn]);

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
