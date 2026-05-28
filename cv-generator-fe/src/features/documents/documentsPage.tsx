import { useState } from "react";

import { DocumentsHeader, type DocsTab } from "./components/documentsHeader";
import { PdfPreviewModal } from "./components/pdfPreviewModal";
import { SavedDocCard } from "./components/savedDocCard";
import { useSavedDocs } from "./hooks/useSavedDocs";
import styles from "./documents.module.css";

type PreviewState = {
  kind: "cv" | "cl";
  id: string;
  name: string;
  pdf: string | null;
};

export function DocumentsPage() {
  const {
    cvs,
    cls,
    loading,
    busy,
    error,
    loadCvPdf,
    loadClPdf,
    downloadCv,
    downloadCl,
    deleteCv,
    deleteCl,
  } = useSavedDocs();
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [tab, setTab] = useState<DocsTab>("all");

  const openPreview = async (kind: "cv" | "cl", id: string, name: string) => {
    setPreview({ kind, id, name, pdf: null });
    const pdf = kind === "cv" ? await loadCvPdf(id) : await loadClPdf(id);
    if (!pdf) {
      setPreview(null);
      return;
    }
    setPreview((prev) => (prev && prev.id === id ? { ...prev, pdf } : prev));
  };

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.loadingPanel}>Loading documents…</section>
      </main>
    );
  }

  const isEmpty = cvs.length === 0 && cls.length === 0;
  const showCvs = tab === "all" || tab === "cv";
  const showCls = tab === "all" || tab === "cl";

  return (
    <main className={styles.page}>
      <DocumentsHeader
        cvCount={cvs.length}
        clCount={cls.length}
        tab={tab}
        onTabChange={setTab}
      />
      {error ? <p className={styles.error}>{error}</p> : null}

      {isEmpty ? (
        <section className={styles.emptyPanel}>
          <p>You haven&apos;t saved any documents yet.</p>
          <p className={styles.emptyHint}>
            Tip: open a CV chat, generate a CV or cover letter, and click <b>Save</b> in the
            preview pane to keep a snapshot here.
          </p>
        </section>
      ) : null}

      {showCvs && cvs.length > 0 ? (
        <section className={styles.section}>
          {tab === "all" ? <h2 className={styles.sectionTitle}>CVs</h2> : null}
          <div className={styles.grid}>
            {cvs.map((cv) => (
              <SavedDocCard
                key={cv.id}
                name={cv.name}
                createdAt={cv.created_at}
                kind="cv"
                busy={busy}
                onPreview={() => openPreview("cv", cv.id, cv.name)}
                onDownload={() => downloadCv(cv)}
                onDelete={() => deleteCv(cv.id)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {showCls && cls.length > 0 ? (
        <section className={styles.section}>
          {tab === "all" ? <h2 className={styles.sectionTitle}>Cover letters</h2> : null}
          <div className={styles.grid}>
            {cls.map((cl) => (
              <SavedDocCard
                key={cl.id}
                name={cl.name}
                createdAt={cl.created_at}
                kind="cl"
                busy={busy}
                onPreview={() => openPreview("cl", cl.id, cl.name)}
                onDownload={() => downloadCl(cl)}
                onDelete={() => deleteCl(cl.id)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {preview ? (
        <PdfPreviewModal
          title={preview.name}
          pdfBase64={preview.pdf}
          onClose={() => setPreview(null)}
          onDownload={() => {
            if (preview.kind === "cv") {
              const cv = cvs.find((c) => c.id === preview.id);
              if (cv) void downloadCv(cv);
            } else {
              const cl = cls.find((c) => c.id === preview.id);
              if (cl) void downloadCl(cl);
            }
          }}
        />
      ) : null}
    </main>
  );
}
