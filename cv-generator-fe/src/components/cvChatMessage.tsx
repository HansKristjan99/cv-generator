import type { ChatMessage } from "../types/chat";
import { cx } from "../utils/cx";
import { CvChatEnhanceButton } from "./cvChatEnhanceButton";
import styles from "./cvChatMessage.module.css";

const roleClass = {
  user: styles.user,
  assistant: styles.assistant,
} as const;

export const CvChatMessage = ({ message }: { message: ChatMessage }) => {
  if (message.type === "cv") {
    return (
      <div className={styles.row}>
        <div className={styles.avatar}>H</div>
        <div className={styles.cvCard}>
          <div className={styles.cvBar}>
            <span className={styles.cvName}>cv.tex · LaTeX source</span>
            <button
              type="button"
              className={styles.copy}
              onClick={() => void navigator.clipboard.writeText(message.content)}
            >
              Copy
            </button>
          </div>
          <pre className={styles.cvPre}>{message.content}</pre>
        </div>
      </div>
    );
  }

  if (message.type === "question") {
    const questions = message.questions ?? [];
    return (
      <div className={styles.row}>
        <div className={styles.avatar}>H</div>
        <div className={cx(styles.bubble, styles.assistant, styles.question)}>
          {message.content ? <p>{message.content}</p> : null}
          <ul className={styles.questions}>
            {questions.map((q, i) => (
              <li key={i}>
                {q.question}
                {q.corresponding_requirement ? (
                  <div>
                    <span className={styles.citeChip}>
                      <span className={styles.citeLabel}>cites</span>
                      {q.corresponding_requirement}
                    </span>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
          <CvChatEnhanceButton questions={questions} />
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";
  return (
    <div className={cx(styles.row, isUser && styles.rowUser)}>
      {isUser ? null : <div className={styles.avatar}>H</div>}
      <div className={cx(styles.bubble, roleClass[message.role])}>
        <p>{message.content}</p>
      </div>
    </div>
  );
};
