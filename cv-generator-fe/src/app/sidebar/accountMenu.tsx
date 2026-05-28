import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";

import { Button } from "../../primitives/button";
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
            <Button variant="primary" className={styles.authButtonFull}>
              Sign in
            </Button>
          </SignInButton>
          <SignUpButton mode="modal">
            <Button className={styles.authButtonFull}>Create account</Button>
          </SignUpButton>
        </div>
      )}
    </div>
  );
}
