import styles from "./cvGeneratingCard.module.css";

export function CvGeneratingCard() {
  return (
    <div className={styles.card} aria-live="polite" aria-busy="true">
      <div className={styles.orbit} aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <span className={styles.label}>Generating CV</span>
    </div>
  );
}
