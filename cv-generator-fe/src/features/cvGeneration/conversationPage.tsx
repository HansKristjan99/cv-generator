import { useEffect, useState } from "react";

import { apiClient } from "../../api/client";
import { useAppLocation } from "../../app/hooks/useAppLocation";
import { useAppDispatch, useAppSelector } from "../../hooks";
import type { PreviewKind } from "../../types/chat";
import { CvChatHeader } from "./components/cvChatHeader";
import { CvChatMessageComposer } from "./components/cvChatMessageComposer";
import { CvChatMessageList } from "./components/cvMessageList";
import { CvPreviewPane } from "./components/cvPreviewPane";
import { ManualEditModal } from "./components/manualEditModal/manualEditModal";
import {
  loadConversation,
  selectActiveConversation,
  setPreviewSelection,
} from "./cvGenerationSlice";
import styles from "./cvGeneratorPage.module.css";

export function ConversationPage({ sessionId }: { sessionId: string }) {
  const dispatch = useAppDispatch();
  const { selectTab } = useAppLocation();
  const conv = useAppSelector(selectActiveConversation);
  const { chatSessions, activeSessionId, latestCvStructured, latestClStructured } =
    useAppSelector((s) => s.cvGeneration);
  const [editingKind, setEditingKind] = useState<"generated_cv" | "cover_letter" | null>(null);

  useEffect(() => {
    if (activeSessionId !== sessionId) {
      void dispatch(loadConversation(sessionId));
    }
  }, [activeSessionId, dispatch, sessionId]);

  const activeSession = chatSessions.find((s) => s.id === sessionId);
  const title = activeSession?.title ?? "Conversation";
  const previewSelection = conv?.previewSelection ?? null;
  const sourceCvPdf = conv?.sourceCvPdfBase64 ?? null;
  const sourceCvText = conv?.sourceCvText ?? null;
  const hasGeneratedCv = Boolean(conv?.latestCvPdfBase64 ?? conv?.latestCvStructured);
  const hasCoverLetter = Boolean(
    conv?.latestCoverLetterPdfBase64 ?? conv?.latestClStructured,
  );
  const canAddApplication = hasGeneratedCv || hasCoverLetter || Boolean(conv?.jobDescription);

  const handleSaveCurrent = async (kind: "generated_cv" | "cover_letter") => {
    const defaultName = title === "Conversation" ? "Untitled" : title;
    const name = window.prompt(
      kind === "generated_cv" ? "Name this CV" : "Name this cover letter",
      kind === "generated_cv" ? `${defaultName} — CV` : `${defaultName} — Cover letter`,
    );
    if (!name?.trim()) return;
    try {
      if (kind === "generated_cv") {
        await apiClient.saveCvFromSession(name.trim(), sessionId);
      } else {
        await apiClient.saveClFromSession(name.trim(), sessionId);
      }
      window.alert("Saved.");
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Save failed.");
    }
  };

  const handleAddApplication = async () => {
    const name = window.prompt("Name this application", title === "Conversation" ? "" : title);
    if (!name?.trim()) return;
    try {
      await apiClient.startApplicationFromSession(sessionId, name.trim());
      selectTab("applications");
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Could not create application.");
    }
  };

  const descriptors = [
    {
      kind: "jd" as const,
      label: "Job description",
      badge: "JD",
      mode: "text" as const,
      content: conv?.jobDescription ?? null,
    },
    {
      kind: "source_cv" as const,
      label: "Submitted CV",
      badge: sourceCvPdf ? "PDF · A4" : "Text",
      mode: (sourceCvPdf ? "pdf" : "text") as "pdf" | "text",
      content: sourceCvPdf ?? sourceCvText,
      downloadName: "submitted-cv.pdf",
    },
    {
      kind: "generated_cv" as const,
      label: "Generated CV",
      badge: "CV · PDF",
      mode: "pdf" as const,
      content: conv?.latestCvPdfBase64 ?? null,
      downloadName: "cv.pdf",
    },
    {
      kind: "cover_letter" as const,
      label: "Cover letter",
      badge: "Letter · PDF",
      mode: "pdf" as const,
      content: conv?.latestCoverLetterPdfBase64 ?? null,
      downloadName: "cover-letter.pdf",
    },
  ];

  return (
    <section className={`${styles.page} ${styles.pageWide}`}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>New CV</span>
            <span className={styles.breadcrumbSep}>›</span>
            <span className={styles.breadcrumbActive}>{title}</span>
          </div>
          <h1 className={styles.title}>{title}</h1>
        </div>
      </header>

      <section className={styles.sessionStack}>
        <CvPreviewPane
          descriptors={descriptors}
          selection={previewSelection}
          onSelect={(kind: PreviewKind | null) => dispatch(setPreviewSelection(kind))}
          onEdit={(kind) => setEditingKind(kind)}
          onSaveCurrent={handleSaveCurrent}
          onAddApplication={canAddApplication ? handleAddApplication : undefined}
          chatContent={
            <>
              <CvChatHeader />
              <CvChatMessageList />
            </>
          }
          composer={<CvChatMessageComposer />}
        />
      </section>

      {editingKind === "generated_cv" && latestCvStructured && (
        <ManualEditModal
          kind="cv"
          initialData={latestCvStructured}
          onClose={() => setEditingKind(null)}
        />
      )}
      {editingKind === "cover_letter" && latestClStructured && (
        <ManualEditModal
          kind="cover_letter"
          initialData={latestClStructured}
          onClose={() => setEditingKind(null)}
        />
      )}
    </section>
  );
}
