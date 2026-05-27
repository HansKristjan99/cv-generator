import { useState } from "react";

import type {
  JobApplication,
  JobApplicationUpdate,
  SavedCl,
  SavedCv,
} from "../../../api/job-applications/jobApplications";
import { SUGGESTED_STATUSES, statusLabel } from "../lib/statuses";
import { RequirementsBar } from "./requirementsBar";
import styles from "../jobApplications.module.css";

type Props = {
  application: JobApplication;
  cvs: SavedCv[];
  cls: SavedCl[];
  saving: boolean;
  onSave: (body: JobApplicationUpdate) => Promise<void>;
  onDelete: () => Promise<void>;
  onClose: () => void;
};

export function ApplicationDetailModal({
  application,
  cvs,
  cls,
  saving,
  onSave,
  onDelete,
  onClose,
}: Props) {
  const [jobName, setJobName] = useState(application.job_name);
  const [jobDescription, setJobDescription] = useState(application.job_description ?? "");
  const [status, setStatus] = useState(application.status);
  const [notes, setNotes] = useState(application.notes ?? "");
  const [cvId, setCvId] = useState(application.submitted_cv_id ?? "");
  const [clId, setClId] = useState(application.submitted_cl_id ?? "");

  const statusOptions = SUGGESTED_STATUSES.includes(status as never)
    ? SUGGESTED_STATUSES
    : ([status, ...SUGGESTED_STATUSES] as readonly string[]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave({
      job_name: jobName.trim() || application.job_name,
      job_description: jobDescription.trim() || null,
      status,
      notes: notes.trim() || null,
      submitted_cv_id: cvId || null,
      submitted_cl_id: clId || null,
    });
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this application? This cannot be undone.")) return;
    await onDelete();
  };

  return (
    <div className={styles.modalScrim} onClick={onClose}>
      <form
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSave}
      >
        <h2 className={styles.modalTitle}>{application.job_name}</h2>
        <RequirementsBar analysis={application.job_requirements} />

        <label className={styles.label}>
          Job name
          <input
            className={styles.input}
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
          />
        </label>

        <label className={styles.label}>
          Job description
          <textarea
            className={styles.textarea}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
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
              {statusOptions.map((s) => (
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

        <label className={styles.label}>
          Notes
          <textarea
            className={styles.textarea}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Anything you want to remember about this application."
            rows={3}
          />
        </label>

        <div className={styles.modalActions}>
          <button
            type="button"
            className={styles.dangerBtn}
            onClick={handleDelete}
            disabled={saving}
          >
            Delete
          </button>
          <span className={styles.spacer} />
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button type="submit" className={styles.primaryBtn} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
