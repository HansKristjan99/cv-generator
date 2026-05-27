import { useEffect, useState } from "react";

import { apiClient } from "../../../api/client";
import type { SavedCl, SavedCv } from "../../../api/job-applications/jobApplications";

export type SavedDocsStore = {
  cvs: SavedCv[];
  cls: SavedCl[];
  loading: boolean;
  busy: boolean;
  error: string | null;
  downloadCv: (cv: SavedCv) => Promise<void>;
  downloadCl: (cl: SavedCl) => Promise<void>;
  deleteCv: (id: string) => Promise<void>;
  deleteCl: (id: string) => Promise<void>;
};

function triggerDownload(filename: string, base64: string) {
  const dataUrl = `data:application/pdf;base64,${base64}`;
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

export function useSavedDocs(): SavedDocsStore {
  const [cvs, setCvs] = useState<SavedCv[]>([]);
  const [cls, setCls] = useState<SavedCl[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([apiClient.listSavedCvs(), apiClient.listSavedCls()])
      .then(([savedCvs, savedCls]) => {
        if (cancelled) return;
        setCvs(savedCvs);
        setCls(savedCls);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load documents");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function withBusy<T>(fn: () => Promise<T>, errMsg: string): Promise<T | null> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : errMsg);
      return null;
    } finally {
      setBusy(false);
    }
  }

  const downloadCv = async (cv: SavedCv) => {
    const pdf = await withBusy(() => apiClient.renderSavedCvPdf(cv.id), "Unable to render CV");
    if (pdf) triggerDownload(`${cv.name}.pdf`, pdf);
  };

  const downloadCl = async (cl: SavedCl) => {
    const pdf = await withBusy(() => apiClient.renderSavedClPdf(cl.id), "Unable to render cover letter");
    if (pdf) triggerDownload(`${cl.name}.pdf`, pdf);
  };

  const deleteCv = async (id: string) => {
    const ok = await withBusy(() => apiClient.deleteSavedCv(id).then(() => true), "Unable to delete CV");
    if (ok) setCvs((prev) => prev.filter((c) => c.id !== id));
  };

  const deleteCl = async (id: string) => {
    const ok = await withBusy(() => apiClient.deleteSavedCl(id).then(() => true), "Unable to delete cover letter");
    if (ok) setCls((prev) => prev.filter((c) => c.id !== id));
  };

  return { cvs, cls, loading, busy, error, downloadCv, downloadCl, deleteCv, deleteCl };
}
