import { loadConversation } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import { cx } from "../utils/cx";
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
  const dispatch = useAppDispatch();
  const sessions = useAppSelector((s) => s.cvGeneration.chatSessions);
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);
  const status = useAppSelector((s) => s.cvGeneration.status);
  const activeIsPending = status === "loading";

  if (!sessions.length) return null;

  return (
    <div className={styles.root}>
      <p className={styles.heading}>Recent chats</p>
      <ul className={styles.list}>
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          const showPending = isActive && activeIsPending;
          return (
            <li key={session.id}>
              <button
                type="button"
                className={cx(
                  styles.item,
                  isActive && styles.itemActive,
                  showPending && styles.itemPending,
                )}
                onClick={() => {
                  if (session.id === activeSessionId) return;
                  void dispatch(loadConversation(session.id));
                }}
              >
                <span className={styles.titleRow}>
                  {showPending ? <span className={styles.pendingDot} aria-hidden /> : null}
                  <span className={styles.title}>{session.title ?? "Untitled"}</span>
                </span>
                <span className={styles.date}>
                  {showPending ? "Generating…" : formatRelativeDate(session.created_at)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
