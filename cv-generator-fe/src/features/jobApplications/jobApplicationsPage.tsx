import { useState } from "react";

import type { JobApplication } from "../../api/job-applications/jobApplications";
import { ApplicationCard } from "./components/applicationCard";
import { ApplicationDetailModal } from "./components/applicationDetailModal";
import { ApplicationsHeader } from "./components/applicationsHeader";
import { ManualCreateModal } from "./components/manualCreateModal";
import { useJobApplications } from "./hooks/useJobApplications";
import styles from "./jobApplications.module.css";

export function JobApplicationsPage() {
  const { applications, cvs, cls, loading, saving, error, create, update, remove } =
    useJobApplications();
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  const open: JobApplication | null = openId
    ? applications.find((a) => a.id === openId) ?? null
    : null;

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
        <div className={styles.grid}>
          {applications.map((a) => (
            <ApplicationCard
              key={a.id}
              application={a}
              cvs={cvs}
              cls={cls}
              onOpen={() => setOpenId(a.id)}
            />
          ))}
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
