import styles from "./cvPdfPane.module.css";

export const CvPdfPane = ({ base64 }: { base64: string }) => {
  const dataUrl = `data:application/pdf;base64,${base64}`;
  return (
    <aside className={styles.pane}>
      <div className={styles.header}>
        <div className={styles.heading}>
          <h2 className={styles.title}>Preview</h2>
          <span className={styles.badge}>PDF · A4</span>
        </div>
      </div>
      <iframe className={styles.frame} src={dataUrl} title="Rendered CV" />
      <div className={styles.footer}>
        <a className={styles.download} href={dataUrl} download="cv.pdf">
          ↓ Download PDF
        </a>
      </div>
    </aside>
  );
};
