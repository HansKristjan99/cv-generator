import { cx } from "../../../utils/cx";
import styles from "../templates.module.css";

export function TemplatePlaceholder({ slug }: { slug: string }) {
  if (slug === "harvard_classic") return <HarvardPreview />;
  if (slug === "rover") return <RoverPreview />;
  return <DefaultPreview />;
}

function DefaultPreview() {
  return (
    <div className={styles.mockCv}>
      <div className={cx(styles.mockLine, styles.mockLineName)} />
      <div className={cx(styles.mockLine, styles.mockLineContact)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineSummaryShort)} />
      <div className={styles.mockRule} />
      <div className={cx(styles.mockLine, styles.mockLineHeading)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={styles.mockRule} />
      <div className={cx(styles.mockLine, styles.mockLineHeading)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
    </div>
  );
}

function HarvardPreview() {
  return (
    <div className={styles.mockCv}>
      <div className={cx(styles.mockLine, styles.mockLineNameCenter)} />
      <div className={styles.mockRuleFull} />
      <div className={cx(styles.mockLine, styles.mockLineContactCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
    </div>
  );
}

function RoverPreview() {
  return (
    <div className={cx(styles.mockCv, styles.mockCvRover)}>
      <div className={cx(styles.mockLine, styles.mockLineNameLarge)} />
      <div className={cx(styles.mockLine, styles.mockLineContactCenter)} />
      <div className={cx(styles.mockLine, styles.mockLineSummary)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingRover)} />
      <div className={styles.mockRuleSepia} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineBullet)} />
      <div className={cx(styles.mockLine, styles.mockLineHeadingRover)} />
      <div className={styles.mockRuleSepia} />
      <div className={cx(styles.mockLine, styles.mockLineBodyBold)} />
      <div className={cx(styles.mockLine, styles.mockLineBody)} />
    </div>
  );
}
