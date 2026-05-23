import { SignInButton, SignUpButton, useAuth } from "@clerk/react";
import { Navigate } from "react-router";

import { LoadingPage } from "../components/loadingPage";
import styles from "./homePage.module.css";

export function HomePage() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return <LoadingPage />;
  }

  if (isSignedIn) {
    return <Navigate to="/app" replace />;
  }

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <div className={styles.brand}>
          <div className={styles.brandTile}>H</div>
          <p className={styles.brandName}>Hireable</p>
        </div>
        <h1 className={styles.title}>Fine tune your CV.</h1>
        <p className={styles.message}>
          Sign in to tailor a CV from your current resume and a job description.
        </p>
        <div className={styles.actions}>
          <SignInButton mode="modal">
            <button type="button" className={styles.button}>
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className={styles.buttonSecondary}>
              Create account
            </button>
          </SignUpButton>
        </div>
      </section>
    </main>
  );
}
