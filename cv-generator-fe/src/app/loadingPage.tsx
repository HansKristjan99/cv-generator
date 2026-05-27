import styles from "./loadingPage.module.css";

export function LoadingPage() {
  return (
    <main className={styles.page}>
      <div className={styles.mark}>H</div>
      <p className={styles.text}>One moment…</p>
    </main>
  );
}
