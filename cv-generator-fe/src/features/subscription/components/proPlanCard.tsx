import { cx } from "../../../utils/cx";
import { PRO_FEATURES, PRO_PRICE_LABEL } from "../lib/planContent";
import styles from "../subscription.module.css";
import { CheckIcon } from "./checkIcon";

type Props = {
  isActive: boolean;
  renewalDate: string | null;
  isStartingCheckout: boolean;
  isOpeningPortal: boolean;
  canSubscribe: boolean;
  onSubscribe: () => void;
  onManageBilling: () => void;
};

export function ProPlanCard({
  isActive,
  renewalDate,
  isStartingCheckout,
  isOpeningPortal,
  canSubscribe,
  onSubscribe,
  onManageBilling,
}: Props) {
  return (
    <article className={cx(styles.plan, styles.planFeatured)}>
      <div className={styles.planHead}>
        <div className={styles.planTopRow}>
          <h2 className={styles.planName}>Pro</h2>
          <span className={styles.planBadge}>{isActive ? "Current plan" : "Recommended"}</span>
        </div>
        {PRO_PRICE_LABEL ? (
          <div className={styles.priceRow}>
            <span className={styles.price}>{PRO_PRICE_LABEL}</span>
          </div>
        ) : (
          <p className={styles.planDesc}>Pricing shown securely at checkout.</p>
        )}
        <p className={styles.planDesc}>
          Remove every limit and generate as much as your job hunt needs.
        </p>
      </div>
      <ul className={styles.features}>
        {PRO_FEATURES.map((feature) => (
          <li key={feature} className={styles.feature}>
            <CheckIcon className={styles.featureIcon} />
            {feature}
          </li>
        ))}
      </ul>
      <div className={styles.planFoot}>
        {isActive ? (
          <>
            <button
              type="button"
              className={styles.planButtonSecondary}
              disabled={isOpeningPortal}
              onClick={onManageBilling}
            >
              {isOpeningPortal ? "Opening…" : "Manage billing"}
            </button>
            {renewalDate ? <p className={styles.renewal}>Renews on {renewalDate}</p> : null}
          </>
        ) : (
          <button
            type="button"
            className={styles.planButton}
            disabled={isStartingCheckout || !canSubscribe}
            onClick={onSubscribe}
          >
            {isStartingCheckout ? "Starting…" : "Subscribe to Pro"}
          </button>
        )}
      </div>
    </article>
  );
}
