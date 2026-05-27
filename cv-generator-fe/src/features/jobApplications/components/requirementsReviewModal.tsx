import type {
  JobRequirement,
  RequirementsAnalysis,
} from "../../../api/job-applications/jobApplications";
import styles from "../jobApplications.module.css";

type Props = {
  analysis: RequirementsAnalysis;
  focus: "must_have" | "nice_to_have";
  onClose: () => void;
};

export function RequirementsReviewModal({ analysis, focus, onClose }: Props) {
  const must = analysis.requirements.filter((r) => r.importance === "must_have");
  const nice = analysis.requirements.filter((r) => r.importance === "nice_to_have");
  const ordered = focus === "must_have" ? [...must, ...nice] : [...nice, ...must];

  return (
    <div className={styles.modalScrim} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h2 className={styles.modalTitle}>Requirements review</h2>
        <p className={styles.modalHint}>
          Read-only view of how this job&apos;s requirements were extracted and whether
          your profile covers each one.
        </p>

        <ul className={styles.reqList}>
          {ordered.map((req, idx) => (
            <RequirementRow key={`${req.requirement}-${idx}`} req={req} />
          ))}
        </ul>

        <div className={styles.modalActions}>
          <span className={styles.spacer} />
          <button type="button" className={styles.secondaryBtn} onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function RequirementRow({ req }: { req: JobRequirement }) {
  const importancePill =
    req.importance === "must_have" ? styles.reqLabelMust : styles.reqLabelNice;
  const importanceLabel = req.importance === "must_have" ? "Must" : "Nice";
  return (
    <li className={req.met ? styles.reqRowMet : styles.reqRowUnmet}>
      <div className={styles.reqRowHead}>
        <span className={importancePill}>{importanceLabel}</span>
        <span className={req.met ? styles.reqStatusMet : styles.reqStatusUnmet}>
          {req.met ? "✓ Met" : "✗ Not met"}
        </span>
      </div>
      <p className={styles.reqText}>{req.requirement}</p>
      {req.met ? (
        <p className={styles.reqEvidence}>
          <span className={styles.reqEvidenceLabel}>Your evidence:</span> {req.evidence}
        </p>
      ) : req.question ? (
        <p className={styles.reqQuestion}>
          <span className={styles.reqEvidenceLabel}>Question to fill the gap:</span> {req.question}
        </p>
      ) : null}
    </li>
  );
}
