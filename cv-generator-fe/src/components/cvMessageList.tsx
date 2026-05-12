import { useEffect, useRef } from "react";

import { useAppSelector } from "../hooks";
import { CvChatMessage } from "./cvChatMessage";

export const CvChatMessageList = () => {
  const { messageHistory, status, error } = useAppSelector((s) => s.cvGeneration);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messageHistory.length, status]);

  return (
    <div ref={containerRef} className="cv-chat-message-list">
      <ul className="message-history">
        {messageHistory.map((message, index) => (
          <li key={index}>
            <CvChatMessage message={message} />
          </li>
        ))}
        {status === "loading" ? (
          <li>
            <div className="cv-chat-message assistant cv-chat-thinking">
              <span />
              <span />
              <span />
            </div>
          </li>
        ) : null}
        {status === "failed" && error ? (
          <li>
            <div className="cv-chat-message assistant cv-chat-error">{error}</div>
          </li>
        ) : null}
      </ul>
    </div>
  );
};
