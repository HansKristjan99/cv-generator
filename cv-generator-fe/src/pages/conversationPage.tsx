import { useState } from "react";
import { CvChatHeader } from "../components/cvChatHeader";
import { CvChatMessageComposer } from "../components/cvChatMessageComposer";
import { CvChatMessageList } from "../components/cvMessageList";
import { CvPreviewPane } from "../components/cvPreviewPane";
import { ManualEditModal } from "../components/manualEditModal";
import {
  selectActiveConversation,
  setPreviewSelection,
} from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import type { PreviewKind } from "../types/chat";
import chatStyles from "../components/cvChat.module.css";
import styles from "./cvGeneratorPage.module.css";

type PreviewDescriptor = {
  kind: PreviewKind;
  label: string;
  badge: string;
  mode: "pdf" | "text";
  content: string | null;
  downloadName?: string;
};

export function ConversationPage() {
  const dispatch = useAppDispatch();
  const conv = useAppSelector(selectActiveConversation);
  const { chatSessions, activeSessionId, latestCvStructured, latestClStructured } =
    useAppSelector((s) => s.cvGeneration);
  const activeSession = chatSessions.find((s) => s.id === activeSessionId);
  const title = activeSession?.title ?? "Conversation";
  const previewSelection = conv?.previewSelection ?? null;
  const [editingKind, setEditingKind] = useState<"generated_cv" | "cover_letter" | null>(null);

  const sourceCvPdf = conv?.sourceCvPdfBase64 ?? null;
  const sourceCvText = conv?.sourceCvText ?? null;

  const descriptors: PreviewDescriptor[] = [
    {
      kind: "jd",
      label: "Job description",
      badge: "JD",
      mode: "text",
      content: conv?.jobDescription ?? null,
    },
    {
      kind: "source_cv",
      label: "Submitted CV",
      badge: sourceCvPdf ? "PDF · A4" : "Text",
      mode: sourceCvPdf ? "pdf" : "text",
      content: sourceCvPdf ?? sourceCvText,
      downloadName: "submitted-cv.pdf",
    },
    {
      kind: "generated_cv",
      label: "Generated CV",
      badge: "CV · PDF",
      mode: "pdf",
      content: conv?.latestCvPdfBase64 ?? null,
      downloadName: "cv.pdf",
    },
    {
      kind: "cover_letter",
      label: "Cover letter",
      badge: "Letter · PDF",
      mode: "pdf",
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

      <section className={styles.panelGrid}>
        <div className={chatStyles.chat}>
          <CvChatHeader />
          <CvChatMessageList />
          <CvChatMessageComposer />
        </div>
        <CvPreviewPane
          descriptors={descriptors}
          selection={previewSelection}
          onSelect={(kind: PreviewKind) => dispatch(setPreviewSelection(kind))}
          onEdit={(kind) => setEditingKind(kind)}
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
