import styles from "../appShell.module.css";

export function Brand() {
  return (
    <div className={styles.brand}>
      <div className={styles.brandTile}>H</div>
      <div>
        <p className={styles.brandName}>Hireable</p>
        <p className={styles.brandTag}>Fine tune your CV</p>
      </div>
    </div>
  );
}
