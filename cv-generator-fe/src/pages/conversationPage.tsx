import { CvChatHeader } from "../components/cvChatHeader";
import { CvChatMessageComposer } from "../components/cvChatMessageComposer";
import { CvChatMessageList } from "../components/cvMessageList";
import { CvPdfPane } from "../components/cvPdfPane";
import { resetChat } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { cx } from "../utils/cx";
import chatStyles from "../components/cvChat.module.css";
import styles from "./cvGeneratorPage.module.css";

export function ConversationPage() {
  const dispatch = useAppDispatch();
  const { latestPdfBase64, chatSessions, activeSessionId } = useAppSelector(
    (s) => s.cvGeneration,
  );
  const showPdf = Boolean(latestPdfBase64);
  const activeSession = chatSessions.find((s) => s.id === activeSessionId);
  const title = activeSession?.title ?? "Conversation";

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
