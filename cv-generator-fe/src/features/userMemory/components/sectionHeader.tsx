import styles from "../userMemory.module.css";

type Props = {
  title: string;
  eyebrow: string;
  count: number;
  addLabel?: string;
  onAdd?: () => void;
};

export function SectionHeader({ title, eyebrow, count, addLabel, onAdd }: Props) {
  return (
    <header className={styles.sectionHeader}>
      <div>
        <p className={styles.sectionEyebrow}>{eyebrow}</p>
        <h2 className={styles.sectionTitle}>{title}</h2>
      </div>
      <div className={styles.sectionActions}>
        <span className={styles.count}>{count}</span>
        {onAdd && addLabel ? (
          <button type="button" className={styles.addButton} onClick={onAdd}>
            {addLabel}
          </button>
        ) : null}
      </div>
    </header>
  );
}
