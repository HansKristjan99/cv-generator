import { CvChatHeader } from "../components/cvChatHeader";
import { CvChatMessageComposer } from "../components/cvChatMessageComposer";
import { CvChatMessageList } from "../components/cvMessageList";
import { CvPdfPane } from "../components/cvPdfPane";
import { resetChat, selectActiveConversation } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { cx } from "../utils/cx";
import chatStyles from "../components/cvChat.module.css";
import styles from "./cvGeneratorPage.module.css";

export function ConversationPage() {
  const dispatch = useAppDispatch();
  const activeConversation = useAppSelector(selectActiveConversation);
  const { chatSessions, activeSessionId } = useAppSelector((s) => s.cvGeneration);
  const latestPdfBase64 = activeConversation?.latestPdfBase64 ?? null;
  const showPdf = Boolean(latestPdfBase64);
  const activeSession = chatSessions.find((s) => s.id === activeSessionId);
  const title = activeSession?.title ?? "Conversation";
  const pageCount = activeSession?.page_count;

  return (
    <section className={cx(styles.page, showPdf && styles.pageWide)}>
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
          {pageCount ? (
            <span className={styles.lengthBadge}>
              {pageCount} {pageCount === 1 ? "page" : "pages"}
            </span>
          ) : null}
          <button
            type="button"
            className={styles.reset}
            onClick={() => dispatch(resetChat())}
          >
            New chat
          </button>
        </div>
      </header>

      <section className={cx(showPdf && styles.panelGrid)}>
        <div className={chatStyles.chat}>
          <CvChatHeader />
          <CvChatMessageList />
          <CvChatMessageComposer />
        </div>
        {showPdf ? <CvPdfPane base64={latestPdfBase64!} /> : null}
      </section>
    </section>
  );
}
