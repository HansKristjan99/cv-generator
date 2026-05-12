import type { ChatMessage } from "../types/chat";

export const CvChatMessage = ({ message }: { message: ChatMessage }) => {
  if (message.type === "cv") {
    return (
      <div className="cv-chat-message assistant cv-chat-message-cv">
        <button
          type="button"
          className="cv-chat-copy"
          onClick={() => void navigator.clipboard.writeText(message.content)}
        >
          Copy
        </button>
        <pre>{message.content}</pre>
      </div>
    );
  }

  if (message.type === "question") {
    const items = message.content.split("\n\n").filter((q) => q.trim());
    return (
      <div className={`cv-chat-message ${message.role}`}>
        <ul className="cv-chat-questions">
          {items.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className={`cv-chat-message ${message.role}`}>
      <p>{message.content}</p>
    </div>
  );
};
