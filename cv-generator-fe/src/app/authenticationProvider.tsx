import { type ReactNode } from "react";
import { SignInButton, SignUpButton } from "@clerk/react";

import { Button } from "../primitives/button";
import { LoadingPage } from "./loadingPage";
import styles from "./appShell.module.css";
import authStyles from "./authenticationProvider.module.css";
import { useApiRegistration } from "./hooks/useApiRegistration";
import { useSessionPolling } from "./hooks/useSessionPolling";

export function AuthenticationProvider({ children }: { children: ReactNode }) {
  const { status, error, isLoaded, isSignedIn } = useApiRegistration();
  useSessionPolling(status);

  if (!isLoaded) return <LoadingPage />;
  if (!isSignedIn) return <SignInPrompt />;
  if (status === "ready") return <>{children}</>;
  if (status === "failed") return <RegistrationError message={error} />;
  return <LoadingPage />;
}

function SignInPrompt() {
  return (
    <section className={styles.placeholder}>
      <p className={styles.placeholderEyebrow}>Hireable</p>
      <h2 className={styles.placeholderTitle}>Sign in to continue</h2>
      <div className={styles.signInActions}>
        <SignInButton mode="modal">
          <Button variant="primary" className={styles.authButtonFull}>
            Sign in
          </Button>
        </SignInButton>
        <SignUpButton mode="modal">
          <Button className={styles.authButtonFull}>Create account</Button>
        </SignUpButton>
      </div>
    </section>
  );
}

function RegistrationError({ message }: { message: string | null }) {
  return (
    <main className={authStyles.page}>
      <section className={authStyles.panel}>
        <h1 className={authStyles.title}>Authentication failed</h1>
        <p className={authStyles.message}>{message}</p>
      </section>
    </main>
  );
}
