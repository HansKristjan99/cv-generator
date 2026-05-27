import { statusLabel, statusTone } from "../lib/statuses";
import styles from "../jobApplications.module.css";

const PILL_CLASS: Record<string, string> = {
  sky: styles.pillSky,
  mint: styles.pillMint,
  primary: styles.pillPrimary,
  danger: styles.pillDanger,
  neutral: styles.pillNeutral,
};

export function StatusPill({ status }: { status: string }) {
  const className = PILL_CLASS[statusTone(status)] ?? styles.pillNeutral;
  return <span className={className}>{statusLabel(status)}</span>;
}
