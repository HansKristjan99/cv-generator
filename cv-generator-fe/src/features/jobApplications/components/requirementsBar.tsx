import type { RequirementsAnalysis } from "../../../api/job-applications/jobApplications";
import { computeRequirementsStats } from "../lib/requirementsStats";
import styles from "../jobApplications.module.css";

type Props = {
  analysis: RequirementsAnalysis | null | undefined;
  compact?: boolean;
};

export function RequirementsBar({ analysis, compact }: Props) {
  const stats = computeRequirementsStats(analysis);
  if (!stats) return null;
  const { mustMet, mustTotal, niceMet, niceTotal } = stats;
  return (
    <div className={compact ? styles.reqBarCompact : styles.reqBar}>
      <span className={styles.reqLabelMust}>
        Must&nbsp;{mustMet}/{mustTotal}
      </span>
      {niceTotal > 0 ? (
        <span className={styles.reqLabelNice}>
          Nice&nbsp;{niceMet}/{niceTotal}
        </span>
      ) : null}
    </div>
  );
}
