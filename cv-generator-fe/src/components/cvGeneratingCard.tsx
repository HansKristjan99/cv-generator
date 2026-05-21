import { useEffect, useState } from "react";

import styles from "./cvGeneratingCard.module.css";

const STAGES = [
  "Reading your CV and the job description…",
  "Picking the bullets that match this role…",
  "Tightening the wording…",
  "Fitting the layout to the page…",
  "Almost there — final compile…",
] as const;

const STAGE_INTERVAL_MS = 2800;

export function CvGeneratingCard() {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStage((s) => (s + 1 < STAGES.length ? s + 1 : s));
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={styles.card} aria-live="polite" aria-busy="true">
      <div className={styles.shimmer} />
      <div className={styles.body}>
        <div className={styles.title}>
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.label}>Generating your CV</span>
        </div>
        <ol className={styles.stages}>
          {STAGES.map((label, i) => (
            <li
              key={label}
              className={
                i < stage
                  ? styles.stageDone
                  : i === stage
                    ? styles.stageActive
                    : styles.stagePending
              }
            >
              {label}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
