import { CvChatHeader } from "../components/cvChatHeader";
import { CvChatMessageComposer } from "../components/cvChatMessageComposer";
import { CvChatMessageList } from "../components/cvMessageList";
import { CvPreviewPane } from "../components/cvPreviewPane";
import {
  resetChat,
  selectActiveConversation,
  setPreviewSelection,
} from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import type { PreviewKind } from "../types/chat";
import { cx } from "../utils/cx";
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
  const { chatSessions, activeSessionId } = useAppSelector((s) => s.cvGeneration);
  const activeSession = chatSessions.find((s) => s.id === activeSessionId);
  const title = activeSession?.title ?? "Conversation";
  const previewSelection = conv?.previewSelection ?? null;

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

  const active = descriptors.find((d) => d.kind === previewSelection && d.content);
  const showPreview = Boolean(active);
  const pageCount = activeSession?.page_count;

  const toggle = (kind: PreviewKind) => {
    dispatch(setPreviewSelection(previewSelection === kind ? null : kind));
  };

  return (
    <section className={cx(styles.page, showPreview && styles.pageWide)}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Tailor</span>
            <span className={styles.breadcrumbSep}>›</span>
            <span className={styles.breadcrumbActive}>{title}</span>
          </div>
          <h1 className={styles.title}>{title}</h1>
        </div>
        <div className={styles.headerActions}>
          <div className={styles.previewBar}>
            {descriptors.map((d) => (
              <button
                key={d.kind}
                type="button"
                className={cx(
                  styles.previewBtn,
                  previewSelection === d.kind && d.content && styles.previewBtnActive,
                )}
                onClick={() => toggle(d.kind)}
                disabled={!d.content}
                title={d.content ? `Preview ${d.label.toLowerCase()}` : `No ${d.label.toLowerCase()} yet`}
              >
                {d.label}
              </button>
            ))}
            {pageCount ? (
              <span className={styles.previewTag}>
                {pageCount} {pageCount === 1 ? "page" : "pages"}
              </span>
            ) : null}
          </div>
          <button type="button" className={styles.reset} onClick={() => dispatch(resetChat())}>
            New chat
          </button>
        </div>
      </header>

      <section className={cx(showPreview && styles.panelGrid)}>
        <div className={chatStyles.chat}>
          <CvChatHeader />
          <CvChatMessageList />
          <CvChatMessageComposer />
        </div>
        {active ? (
          <CvPreviewPane
            title={active.label}
            badge={active.badge}
            mode={active.mode}
            content={active.content!}
            downloadName={active.downloadName}
            onClose={() => dispatch(setPreviewSelection(null))}
          />
        ) : null}
      </section>
    </section>
  );
}
