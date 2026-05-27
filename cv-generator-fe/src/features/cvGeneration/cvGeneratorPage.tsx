import { useEffect } from "react";

import { CvChatSetup } from "./components/cvChatSetup";
import { fetchQuota } from "./cvGenerationSlice";
import { useAppDispatch } from "../../hooks";
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
            <span className={styles.breadcrumbActive}>New CV</span>
          </div>
          <h1 className={styles.title}>Tailor your CV</h1>
          <p className={styles.subtitle}>
            Chat with Hireable to refine your CV for a specific job.
          </p>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.status}>
            <span className={styles.statusDot} />
            Hireable is ready
          </span>
        </div>
      </header>

      <CvChatSetup />
    </section>
  );
}
