import { cx } from "../../../utils/cx";
import { FREE_FEATURES } from "../lib/planContent";
import styles from "../subscription.module.css";
import { CheckIcon } from "./checkIcon";

export function FreePlanCard({ isActive }: { isActive: boolean }) {
  return (
    <article className={styles.plan}>
      <div className={styles.planHead}>
        <div className={styles.planTopRow}>
          <h2 className={styles.planName}>Standard</h2>
          {!isActive ? <span className={styles.planBadgeNeutral}>Current plan</span> : null}
        </div>
        <div className={styles.priceRow}>
          <span className={styles.price}>Free</span>
        </div>
        <p className={styles.planDesc}>
          Everything you need to try Hireable and ship a polished CV.
        </p>
      </div>
      <ul className={styles.features}>
        {FREE_FEATURES.map((feature) => (
          <li key={feature} className={styles.feature}>
            <CheckIcon className={cx(styles.featureIcon, styles.featureIconMuted)} />
            {feature}
          </li>
        ))}
      </ul>
      <div className={styles.planFoot}>
        {!isActive ? <span className={styles.currentTag}>Your current plan</span> : null}
      </div>
    </article>
  );
}
