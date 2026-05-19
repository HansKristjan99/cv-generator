import { useEffect } from "react";

import { CvChat } from "../components/cvChat";
import { CvPdfPane } from "../components/cvPdfPane";
import { fetchQuota, resetChat } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { cx } from "../utils/cx";
import styles from "./cvGeneratorPage.module.css";

export function CvGeneratorPage() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    void dispatch(fetchQuota());
  }, [dispatch]);

  const { conversationId, messageHistory, latestPdfBase64 } = useAppSelector(
    (s) => s.cvGeneration,
  );
  const started = Boolean(conversationId) || messageHistory.length > 0;
  const showPdf = Boolean(latestPdfBase64);

  return (
    <section className={cx(styles.page, showPdf && styles.pageWide)}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Tailor</span>
            <span className={styles.breadcrumbSep}>›</span>
            <span className={styles.breadcrumbActive}>
              {started ? "Conversation" : "New draft"}
            </span>
          </div>
          <h1 className={styles.title}>Tailor your CV</h1>
          <p className={styles.subtitle}>
            Match your CV to the role — Hirable reads both and sharpens what lands.
          </p>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.status}>
            <span className={styles.statusDot} />
            Hirable is ready
          </span>
          {started ? (
            <button
              type="button"
              className={styles.reset}
              onClick={() => dispatch(resetChat())}
            >
              New chat
            </button>
          ) : null}
        </div>
      </header>

      <section className={cx(showPdf && styles.panelGrid)}>
        <CvChat />
        {showPdf ? <CvPdfPane base64={latestPdfBase64!} /> : null}
      </section>
    </section>
  );
}
