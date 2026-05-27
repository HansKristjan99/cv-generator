import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";

import styles from "../appShell.module.css";

export function AccountMenu() {
  const { isLoaded, isSignedIn } = useAuth();

  return (
    <div className={styles.account}>
      {!isLoaded ? (
        <p className={styles.status}>Loading…</p>
      ) : isSignedIn ? (
        <UserButton />
      ) : (
        <div className={styles.authBox}>
          <SignInButton mode="modal">
            <button type="button" className={styles.authButton}>
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className={styles.authButtonSecondary}>
              Create account
            </button>
          </SignUpButton>
        </div>
      )}
    </div>
  );
}
