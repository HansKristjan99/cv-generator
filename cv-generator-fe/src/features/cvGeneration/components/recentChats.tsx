import { useAppLocation } from "../../../app/hooks/useAppLocation";
import { useAppSelector } from "../../../hooks";
import { cx } from "../../../utils/cx";
import styles from "./recentChats.module.css";

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const diffMs = Date.now() - date.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function RecentChats() {
  const { activeSessionId, openSession } = useAppLocation();
  const sessions = useAppSelector((s) => s.cvGeneration.chatSessions);

  if (!sessions.length) return null;

  return (
    <div className={styles.root}>
      <p className={styles.heading}>Recent chats</p>
      <ul className={styles.list}>
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          const showPending = session.status === "pending" || session.status === "running";
          const showFailed = session.status === "failed";
          return (
            <li key={session.id}>
              <button
                type="button"
                className={cx(
                  styles.item,
                  isActive && styles.itemActive,
                  showPending && styles.itemPending,
                )}
                onClick={() => openSession(session.id)}
              >
                <span className={styles.titleRow}>
                  {showPending ? <span className={styles.pendingDot} aria-hidden /> : null}
                  <span className={styles.title}>{session.title ?? "Untitled"}</span>
                </span>
                <span className={styles.date}>
                  {showPending
                    ? "Generating…"
                    : showFailed
                      ? "Failed"
                      : formatRelativeDate(session.created_at)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
