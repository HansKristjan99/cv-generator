import { useMemo, useState } from "react";

import type { JobApplication } from "../../api/job-applications/jobApplications";
import { ApplicationCard } from "./components/applicationCard";
import { ApplicationDetailModal } from "./components/applicationDetailModal";
import { ApplicationsHeader } from "./components/applicationsHeader";
import { ManualCreateModal } from "./components/manualCreateModal";
import { useJobApplications } from "./hooks/useJobApplications";
import { STAGES, type Stage, stageForStatus } from "./lib/statuses";
import { cx } from "../../utils/cx";
import styles from "./jobApplications.module.css";

export function JobApplicationsPage() {
  const { applications, cvs, cls, loading, saving, error, create, update, remove } =
    useJobApplications();
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [hoverStage, setHoverStage] = useState<Stage | null>(null);

  const grouped = useMemo(() => {
    const map: Record<Stage, JobApplication[]> = {
      saved: [],
      applied: [],
      interviewing: [],
      offer: [],
      closed: [],
    };
    for (const a of applications) {
      map[stageForStatus(a.status)].push(a);
    }
    return map;
  }, [applications]);

  const open: JobApplication | null = openId
    ? applications.find((a) => a.id === openId) ?? null
    : null;

  const handleDrop = (stage: Stage) => {
    setHoverStage(null);
    if (!dragId) return;
    const dragged = applications.find((a) => a.id === dragId);
    setDragId(null);
    if (!dragged) return;
    if (stageForStatus(dragged.status) === stage) return;
    const def = STAGES.find((s) => s.id === stage);
    if (!def) return;
    void update(dragged.id, { status: def.defaultStatus });
  };

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>Loading applications…</section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <ApplicationsHeader total={applications.length} onNew={() => setCreating(true)} />
      {error ? <p className={styles.error}>{error}</p> : null}

      {applications.length === 0 ? (
        <section className={styles.emptyPanel}>
          <p>You haven&apos;t tracked any applications yet.</p>
          <p className={styles.emptyHint}>
            Tip: open a CV chat and click <b>Add application</b> to start one from a generated CV.
          </p>
        </section>
      ) : (
        <div className={styles.board}>
          {STAGES.map((def) => {
            const items = grouped[def.id];
            const isHover = hoverStage === def.id;
            return (
              <div
                key={def.id}
                className={cx(styles.column, isHover && styles.columnDropHover)}
                onDragOver={(e) => {
                  if (!dragId) return;
                  e.preventDefault();
                  e.dataTransfer.dropEffect = "move";
                  if (hoverStage !== def.id) setHoverStage(def.id);
                }}
                onDragLeave={(e) => {
                  if (e.currentTarget.contains(e.relatedTarget as Node)) return;
                  if (hoverStage === def.id) setHoverStage(null);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  handleDrop(def.id);
                }}
              >
                <div className={styles.columnHead}>
                  <span className={cx(styles.columnLabel, styles[`columnLabel_${def.tone}`])}>
                    {def.label.toUpperCase()}
                  </span>
                  <span className={styles.columnCount}>{items.length}</span>
                </div>
                <div className={styles.columnSub}>{def.subtitle}</div>
                <div className={styles.columnBody}>
                  {items.length === 0 ? (
                    <div className={styles.columnEmpty}>
                      Drag cards here.
                    </div>
                  ) : (
                    items.map((a) => (
                      <ApplicationCard
                        key={a.id}
                        application={a}
                        cvs={cvs}
                        cls={cls}
                        onOpen={() => setOpenId(a.id)}
                        onDragStart={(id) => setDragId(id)}
                        onDragEnd={() => {
                          setDragId(null);
                          setHoverStage(null);
                        }}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {creating ? (
        <ManualCreateModal
          cvs={cvs}
          cls={cls}
          saving={saving}
          onSubmit={async (body) => {
            await create(body);
            setCreating(false);
          }}
          onClose={() => setCreating(false)}
        />
      ) : null}

      {open ? (
        <ApplicationDetailModal
          application={open}
          cvs={cvs}
          cls={cls}
          saving={saving}
          onSave={async (body) => {
            await update(open.id, body);
            setOpenId(null);
          }}
          onDelete={async () => {
            await remove(open.id);
            setOpenId(null);
          }}
          onClose={() => setOpenId(null)}
        />
      ) : null}
    </main>
  );
}
