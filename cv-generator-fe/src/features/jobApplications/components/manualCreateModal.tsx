import { useState } from "react";

import type {
  JobApplicationCreate,
  SavedCl,
  SavedCv,
} from "../../../api/job-applications/jobApplications";
import { SUGGESTED_STATUSES, statusLabel } from "../lib/statuses";
import styles from "../jobApplications.module.css";

type Props = {
  cvs: SavedCv[];
  cls: SavedCl[];
  saving: boolean;
  onSubmit: (body: JobApplicationCreate) => Promise<void>;
  onClose: () => void;
};

export function ManualCreateModal({ cvs, cls, saving, onSubmit, onClose }: Props) {
  const [jobName, setJobName] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [status, setStatus] = useState<string>("initial");
  const [cvId, setCvId] = useState<string>("");
  const [clId, setClId] = useState<string>("");

  const canSubmit = jobName.trim().length > 0 && !saving;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    await onSubmit({
      job_name: jobName.trim(),
      job_description: jobDescription.trim() || null,
      submitted_cv_id: cvId || null,
      submitted_cl_id: clId || null,
      status,
    });
  };

  return (
    <div className={styles.modalScrim} onClick={onClose}>
      <form
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 className={styles.modalTitle}>New application</h2>

        <label className={styles.label}>
          Job name
          <input
            className={styles.input}
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            placeholder="Software Engineer @ Proton"
            autoFocus
          />
        </label>

        <label className={styles.label}>
          Job description
          <textarea
            className={styles.textarea}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the JD or a short summary."
            rows={4}
          />
        </label>

        <div className={styles.row}>
          <label className={styles.label}>
            Status
            <select
              className={styles.input}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {SUGGESTED_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.label}>
            Submitted CV
            <select
              className={styles.input}
              value={cvId}
              onChange={(e) => setCvId(e.target.value)}
            >
              <option value="">— None —</option>
              {cvs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.label}>
            Submitted cover letter
            <select
              className={styles.input}
              value={clId}
              onChange={(e) => setClId(e.target.value)}
            >
              <option value="">— None —</option>
              {cls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className={styles.modalActions}>
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button type="submit" className={styles.primaryBtn} disabled={!canSubmit}>
            {saving ? "Saving…" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
