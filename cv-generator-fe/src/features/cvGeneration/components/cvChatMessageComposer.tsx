import { MAX_MESSAGES_PER_SESSION, MAX_USER_MESSAGE_CHARS } from "../../../config/limits";
import {
  selectActiveConversation,
  sendMessage,
  setDraftMessage,
} from "../cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../../../hooks";
import styles from "./cvChatMessageComposer.module.css";

const PROMPT_CHIPS = [
  { label: "Make it more concise", message: "Make it more concise" },
  { label: "Quantify my impact", message: "Quantify my impact" },
  { label: "Match the job's tone", message: "Match the job's tone" },
  { label: "Improve ATS keyword coverage", message: "Improve ATS keyword coverage" },
  { label: "/cover", message: "/cover" },
];

export const CvChatMessageComposer = () => {
  const dispatch = useAppDispatch();
  const activeConversation = useAppSelector(selectActiveConversation);
  const draftMessage = activeConversation?.draftMessage ?? "";
  const sessionId = activeConversation?.activeSessionId ?? null;
  const messageHistory = activeConversation?.messageHistory ?? [];
  const isBusy =
    activeConversation?.generationStatus === "loading" ||
    activeConversation?.enhanceStatus === "loading";

  const trimmed = draftMessage.trim();
  const messagesUsed = messageHistory.length;
  const messagesRemaining = MAX_MESSAGES_PER_SESSION - messagesUsed;
  const atLimit = messagesRemaining <= 0;
  const disabled = isBusy || !trimmed || atLimit || !sessionId;

  const onSend = () => {
    if (disabled) return;
    if (trimmed.match(/^\/cover(-letter)?\b/i)) {
      const body = trimmed.replace(/^\/cover(-letter)?\s*/i, "").trim();
      void dispatch(
        sendMessage({
          sessionId,
          userMessage: body || "Write a cover letter tailored to this job.",
          kind: "cover_letter",
        }),
      );
    } else {
      void dispatch(sendMessage({ sessionId, userMessage: trimmed, kind: "cv" }));
    }
  };

  return (
    <div className={styles.composer}>
      {atLimit ? (
        <p className={styles.limitReached}>
          Message limit reached for this session ({MAX_MESSAGES_PER_SESSION} messages).
        </p>
      ) : (
        <div className={styles.chips}>
          {PROMPT_CHIPS.map((chip) => (
            <button
              key={chip.label}
              type="button"
              className={styles.chip}
              onClick={() => dispatch(setDraftMessage(chip.message))}
            >
              <span aria-hidden="true">↳</span>
              {chip.label}
            </button>
          ))}
        </div>
      )}
      <div className={styles.inputRow}>
        <textarea
          className={styles.input}
          rows={2}
          value={draftMessage}
          onChange={(e) => dispatch(setDraftMessage(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder={atLimit ? "Session limit reached." : "Refine your CV, or /cover to generate a cover letter (Ctrl/⌘+Enter)"}
          maxLength={MAX_USER_MESSAGE_CHARS}
          disabled={atLimit}
        />
        <button type="button" className={styles.send} onClick={onSend} disabled={disabled}>
          Send
        </button>
      </div>
      {!atLimit && messagesRemaining <= 3 ? (
        <p className={styles.limitNote}>
          {messagesRemaining} message{messagesRemaining === 1 ? "" : "s"} remaining in this session
        </p>
      ) : null}
    </div>
  );
};
