import { useEffect, useState } from "react";

import { apiClient } from "../../../api/client";
import type {
  JobApplication,
  JobApplicationCreate,
  JobApplicationUpdate,
  SavedCl,
  SavedCv,
} from "../../../api/job-applications/jobApplications";

export type JobApplicationsStore = {
  applications: JobApplication[];
  cvs: SavedCv[];
  cls: SavedCl[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  create: (body: JobApplicationCreate) => Promise<void>;
  update: (id: string, body: JobApplicationUpdate) => Promise<void>;
  remove: (id: string) => Promise<void>;
  deleteCv: (id: string) => Promise<void>;
  deleteCl: (id: string) => Promise<void>;
};

export function useJobApplications(): JobApplicationsStore {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [cvs, setCvs] = useState<SavedCv[]>([]);
  const [cls, setCls] = useState<SavedCl[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      apiClient.listJobApplications(),
      apiClient.listSavedCvs(),
      apiClient.listSavedCls(),
    ])
      .then(([apps, savedCvs, savedCls]) => {
        if (cancelled) return;
        setApplications(apps);
        setCvs(savedCvs);
        setCls(savedCls);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load applications");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function withSaving<T>(fn: () => Promise<T>, errMsg: string): Promise<T | null> {
    setSaving(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : errMsg);
      return null;
    } finally {
      setSaving(false);
    }
  }

  const create = async (body: JobApplicationCreate) => {
    const created = await withSaving(
      () => apiClient.createJobApplication(body),
      "Unable to create application",
    );
    if (created) setApplications((prev) => [created, ...prev]);
  };

  const update = async (id: string, body: JobApplicationUpdate) => {
    const updated = await withSaving(
      () => apiClient.updateJobApplication(id, body),
      "Unable to update application",
    );
    if (updated) {
      setApplications((prev) => {
        const others = prev.filter((a) => a.id !== updated.id);
        return [updated, ...others];
      });
    }
  };

  const remove = async (id: string) => {
    const ok = await withSaving(
      () => apiClient.deleteJobApplication(id).then(() => true),
      "Unable to delete application",
    );
    if (ok) setApplications((prev) => prev.filter((a) => a.id !== id));
  };

  const deleteCv = async (id: string) => {
    const ok = await withSaving(
      () => apiClient.deleteSavedCv(id).then(() => true),
      "Unable to delete CV",
    );
    if (ok) {
      setCvs((prev) => prev.filter((c) => c.id !== id));
      setApplications((prev) =>
        prev.map((a) => (a.submitted_cv_id === id ? { ...a, submitted_cv_id: null } : a)),
      );
    }
  };

  const deleteCl = async (id: string) => {
    const ok = await withSaving(
      () => apiClient.deleteSavedCl(id).then(() => true),
      "Unable to delete cover letter",
    );
    if (ok) {
      setCls((prev) => prev.filter((c) => c.id !== id));
      setApplications((prev) =>
        prev.map((a) => (a.submitted_cl_id === id ? { ...a, submitted_cl_id: null } : a)),
      );
    }
  };

  return {
    applications,
    cvs,
    cls,
    loading,
    saving,
    error,
    create,
    update,
    remove,
    deleteCv,
    deleteCl,
  };
}
