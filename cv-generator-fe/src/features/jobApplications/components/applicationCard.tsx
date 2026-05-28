import type {
  JobApplication,
  SavedCl,
  SavedCv,
} from "../../../api/job-applications/jobApplications";
import styles from "../jobApplications.module.css";

type Props = {
  application: JobApplication;
  cvs: SavedCv[];
  cls: SavedCl[];
  onOpen: () => void;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
};

function formatRelative(iso: string): string {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "";
  const diffMs = Date.now() - ts;
  const day = 86400000;
  const days = Math.floor(diffMs / day);
  if (days < 1) return "today";
  if (days < 2) return "1d";
  if (days < 30) return `${days}d`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function companyMark(name: string): string {
  const letter = name.replace(/[^A-Za-z]/g, "")[0];
  return letter ? letter.toUpperCase() : "?";
}

export function ApplicationCard({
  application,
  cvs,
  cls,
  onOpen,
  onDragStart,
  onDragEnd,
}: Props) {
  const cv = cvs.find((c) => c.id === application.submitted_cv_id) ?? null;
  const cl = cls.find((c) => c.id === application.submitted_cl_id) ?? null;
  const docLabel = cv && cl ? "CV + CL" : cv ? "CV" : cl ? "CL" : null;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOpen();
    }
  };

  return (
    <div
      className={styles.kanbanCard}
      role="button"
      tabIndex={0}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart(application.id);
      }}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      onKeyDown={handleKeyDown}
    >
      <div className={styles.kanbanHead}>
        <div className={styles.kanbanIdentity}>
          <span className={styles.kanbanCompany}>{application.job_name}</span>
          {application.job_description ? (
            <span className={styles.kanbanRole}>
              {application.job_description.length > 60
                ? `${application.job_description.slice(0, 60)}…`
                : application.job_description}
            </span>
          ) : null}
        </div>
        <span className={styles.kanbanMark}>{companyMark(application.job_name)}</span>
      </div>
      <div className={styles.kanbanFoot}>
        {docLabel ? <span className={styles.tagMint}>{docLabel}</span> : null}
        <span className={styles.kanbanDate}>{formatRelative(application.updated_at)}</span>
      </div>
    </div>
  );
}
