import type { LoadState } from "../hooks/useSubscription";
import styles from "../subscription.module.css";

type Props = {
  loadState: LoadState;
  isActive: boolean;
};

export function SubscriptionHeader({ loadState, isActive }: Props) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.breadcrumb}>
          <span>Workspace</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbActive}>Subscription</span>
        </div>
        <h1 className={styles.title}>Subscription</h1>
        <p className={styles.subtitle}>
          Upgrade to Pro for unlimited CV generation, refinements, and AI suggestions.
        </p>
      </div>
      {loadState === "ready" ? (
        isActive ? (
          <span className={styles.statusActive}>
            <span className={styles.statusDot} />
            Pro · Active
          </span>
        ) : (
          <span className={styles.statusFree}>Free plan</span>
        )
      ) : null}
    </header>
  );
}
