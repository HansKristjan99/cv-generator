import { useEffect, useRef } from "react";

import { selectActiveConversation } from "../cvGenerationSlice";
import { useAppSelector } from "../../../hooks";
import { cx } from "../../../utils/cx";
import { CvChatMessage } from "./cvChatMessage";
import { CvGeneratingCard } from "./cvGeneratingCard";
import styles from "./cvMessageList.module.css";
import msg from "./cvChatMessage.module.css";

export const CvChatMessageList = () => {
  const activeConversation = useAppSelector(selectActiveConversation);
  const messageHistory = activeConversation?.messageHistory ?? [];
  const status = activeConversation?.generationStatus ?? "idle";
  const error = activeConversation?.error ?? null;
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messageHistory.length, status]);

  return (
    <div ref={containerRef} className={styles.list}>
      <ul className={styles.history}>
        {messageHistory.map((message, index) => (
          <li key={index}>
            <CvChatMessage message={message} />
          </li>
        ))}
        {status === "loading" ? (
          <li>
            <CvGeneratingCard />
          </li>
        ) : null}
        {status === "failed" && error ? (
          <li>
            <div className={cx(msg.bubble, msg.assistant, msg.error)}>{error}</div>
          </li>
        ) : null}
      </ul>
    </div>
  );
};
