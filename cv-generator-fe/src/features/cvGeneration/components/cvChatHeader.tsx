import styles from "./cvChatHeader.module.css";

export const CvChatHeader = () => {
  return (
    <header className={styles.header}>
      <div className={styles.avatar}>H</div>
      <div>
        <p className={styles.title}>Hireable</p>
        <p className={styles.subtitle}>opinionated, evidence-traced</p>
      </div>
    </header>
  );
};
