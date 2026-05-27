import type {
  JobApplication,
  SavedCl,
  SavedCv,
} from "../../../api/job-applications/jobApplications";
import styles from "../jobApplications.module.css";
import { RequirementsBar } from "./requirementsBar";
import { StatusPill } from "./statusPill";

type Props = {
  application: JobApplication;
  cvs: SavedCv[];
  cls: SavedCl[];
  onOpen: () => void;
};

function formatRelative(iso: string): string {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "";
  const diffMs = Date.now() - ts;
  const day = 86400000;
  if (diffMs < day) return "today";
  if (diffMs < 2 * day) return "yesterday";
  if (diffMs < 30 * day) return `${Math.floor(diffMs / day)} days ago`;
  return new Date(iso).toLocaleDateString();
}

export function ApplicationCard({ application, cvs, cls, onOpen }: Props) {
  const cv = cvs.find((c) => c.id === application.submitted_cv_id) ?? null;
  const cl = cls.find((c) => c.id === application.submitted_cl_id) ?? null;

  return (
    <button type="button" className={styles.card} onClick={onOpen}>
      <div className={styles.cardHead}>
        <h2 className={styles.cardTitle}>{application.job_name}</h2>
        <StatusPill status={application.status} />
      </div>
      {application.job_description ? (
        <p className={styles.cardDescription}>
          {application.job_description.length > 180
            ? `${application.job_description.slice(0, 180)}…`
            : application.job_description}
        </p>
      ) : null}
      <div className={styles.cardTags}>
        {cv ? <span className={styles.tag}>CV · {cv.name}</span> : null}
        {cl ? <span className={styles.tag}>CL · {cl.name}</span> : null}
        <RequirementsBar analysis={application.job_requirements} compact />
      </div>
      <p className={styles.cardFooter}>Updated {formatRelative(application.updated_at)}</p>
    </button>
  );
}
