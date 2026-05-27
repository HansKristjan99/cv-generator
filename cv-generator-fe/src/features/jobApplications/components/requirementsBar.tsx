import { useState } from "react";

import type { RequirementsAnalysis } from "../../../api/job-applications/jobApplications";
import { computeRequirementsStats } from "../lib/requirementsStats";
import styles from "../jobApplications.module.css";
import { RequirementsReviewModal } from "./requirementsReviewModal";

type Props = {
  analysis: RequirementsAnalysis | null | undefined;
  compact?: boolean;
};

export function RequirementsBar({ analysis, compact }: Props) {
  const [focus, setFocus] = useState<"must_have" | "nice_to_have" | null>(null);
  const stats = computeRequirementsStats(analysis);
  if (!stats || !analysis) return null;
  const { mustMet, mustTotal, niceMet, niceTotal } = stats;

  const open = (which: "must_have" | "nice_to_have") => (e: React.MouseEvent) => {
    e.stopPropagation();
    setFocus(which);
  };

  return (
    <>
      <div className={compact ? styles.reqBarCompact : styles.reqBar}>
        <button
          type="button"
          className={styles.reqLabelMustBtn}
          onClick={open("must_have")}
          title="Review must-have requirements"
        >
          Must&nbsp;{mustMet}/{mustTotal}
        </button>
        {niceTotal > 0 ? (
          <button
            type="button"
            className={styles.reqLabelNiceBtn}
            onClick={open("nice_to_have")}
            title="Review nice-to-have requirements"
          >
            Nice&nbsp;{niceMet}/{niceTotal}
          </button>
        ) : null}
      </div>
      {focus ? (
        <RequirementsReviewModal
          analysis={analysis}
          focus={focus}
          onClose={() => setFocus(null)}
        />
      ) : null}
    </>
  );
}
