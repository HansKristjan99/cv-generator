import { useEffect } from "react";

import { CvChatSetup } from "../components/cvChatSetup";
import { fetchQuota } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch } from "../hooks";
import styles from "./cvGeneratorPage.module.css";

export function CvGeneratorPage() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    void dispatch(fetchQuota());
  }, [dispatch]);

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.breadcrumb}>
            <span>Tailor</span>
            <span className={styles.breadcrumbSep}>›</span>
            <span className={styles.breadcrumbActive}>New draft</span>
          </div>
          <h1 className={styles.title}>Tailor your CV</h1>
          <p className={styles.subtitle}>
            Chat with Hirable to refine your CV for a specific job.
          </p>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.status}>
            <span className={styles.statusDot} />
            Hirable is ready
          </span>
        </div>
      </header>

      <CvChatSetup />
    </section>
  );
}
