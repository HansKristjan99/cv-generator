import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { apiClient } from "../../api/client";
import { useAppLocation } from "../../app/hooks/useAppLocation";
import { useAppDispatch, useAppSelector } from "../../hooks";
import { PromptDialog } from "../../primitives/promptDialog";
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
  const [, setSearchParams] = useSearchParams();
  const conv = useAppSelector(selectActiveConversation);
  const { chatSessions, activeSessionId, latestCvStructured, latestClStructured } =
    useAppSelector((s) => s.cvGeneration);
  const [editingKind, setEditingKind] = useState<"generated_cv" | "cover_letter" | null>(null);
  const [namePrompt, setNamePrompt] = useState<{
    title: string;
    defaultValue: string;
    confirmLabel?: string;
    resolve: (value: string | null) => void;
  } | null>(null);

  const askName = (
    title: string,
    defaultValue: string,
    confirmLabel?: string,
  ): Promise<string | null> =>
    new Promise((resolve) => {
      setNamePrompt({ title, defaultValue, confirmLabel, resolve });
    });

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
    const name = await askName(
      kind === "generated_cv" ? "Name this CV" : "Name this cover letter",
      kind === "generated_cv" ? `${defaultName} — CV` : `${defaultName} — Cover letter`,
      "Save",
    );
    if (!name) return;
    try {
      if (kind === "generated_cv") {
        await apiClient.saveCvFromSession(name, sessionId);
      } else {
        await apiClient.saveClFromSession(name, sessionId);
      }
      window.alert("Saved.");
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Save failed.");
    }
  };

  const handleAddApplication = async () => {
    const name = await askName(
      "Name this application",
      title === "Conversation" ? "" : title,
      "Create",
    );
    if (!name) return;
    try {
      const app = await apiClient.startApplicationFromSession(sessionId, name);
      setSearchParams((p) => {
        const n = new URLSearchParams(p);
        n.set("tab", "applications");
        n.set("open", app.id);
        n.delete("sid");
        return n;
      });
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
      {namePrompt ? (
        <PromptDialog
          title={namePrompt.title}
          defaultValue={namePrompt.defaultValue}
          confirmLabel={namePrompt.confirmLabel}
          onSubmit={(value) => {
            namePrompt.resolve(value);
            setNamePrompt(null);
          }}
          onCancel={() => {
            namePrompt.resolve(null);
            setNamePrompt(null);
          }}
        />
      ) : null}
    </section>
  );
}
