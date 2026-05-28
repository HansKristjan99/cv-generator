import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "../../../api/client";
import type { SavedCl, SavedCv } from "../../../api/job-applications/jobApplications";

export type SavedDocsStore = {
  cvs: SavedCv[];
  cls: SavedCl[];
  loading: boolean;
  busy: boolean;
  error: string | null;
  getCvPdf: (id: string) => Promise<string | null>;
  getClPdf: (id: string) => Promise<string | null>;
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

  // Per-id PDF cache. We dedupe concurrent fetches by stashing the in-flight
  // promise; resolved bytes stay in the map so re-opening a preview is instant.
  const cvPdfCache = useRef(new Map<string, Promise<string | null>>());
  const clPdfCache = useRef(new Map<string, Promise<string | null>>());

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

  const cachedFetch = useCallback(
    (
      cache: React.MutableRefObject<Map<string, Promise<string | null>>>,
      id: string,
      fetcher: () => Promise<string>,
      errMsg: string,
    ): Promise<string | null> => {
      const existing = cache.current.get(id);
      if (existing) return existing;
      const promise = fetcher().catch((err) => {
        cache.current.delete(id);
        setError(err instanceof Error ? err.message : errMsg);
        return null as string | null;
      });
      cache.current.set(id, promise);
      return promise;
    },
    [],
  );

  const getCvPdf = useCallback(
    (id: string) =>
      cachedFetch(cvPdfCache, id, () => apiClient.renderSavedCvPdf(id), "Unable to render CV"),
    [cachedFetch],
  );

  const getClPdf = useCallback(
    (id: string) =>
      cachedFetch(clPdfCache, id, () => apiClient.renderSavedClPdf(id), "Unable to render cover letter"),
    [cachedFetch],
  );

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
    const pdf = await getCvPdf(cv.id);
    if (pdf) triggerDownload(`${cv.name}.pdf`, pdf);
  };

  const downloadCl = async (cl: SavedCl) => {
    const pdf = await getClPdf(cl.id);
    if (pdf) triggerDownload(`${cl.name}.pdf`, pdf);
  };

  const deleteCv = async (id: string) => {
    const ok = await withBusy(() => apiClient.deleteSavedCv(id).then(() => true), "Unable to delete CV");
    if (ok) {
      cvPdfCache.current.delete(id);
      setCvs((prev) => prev.filter((c) => c.id !== id));
    }
  };

  const deleteCl = async (id: string) => {
    const ok = await withBusy(() => apiClient.deleteSavedCl(id).then(() => true), "Unable to delete cover letter");
    if (ok) {
      clPdfCache.current.delete(id);
      setCls((prev) => prev.filter((c) => c.id !== id));
    }
  };

  return {
    cvs,
    cls,
    loading,
    busy,
    error,
    getCvPdf,
    getClPdf,
    downloadCv,
    downloadCl,
    deleteCv,
    deleteCl,
  };
}
