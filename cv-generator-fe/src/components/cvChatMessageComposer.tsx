import { MAX_MESSAGES_PER_SESSION, MAX_USER_MESSAGE_CHARS } from "../config/limits";
import {
  selectActiveConversation,
  sendMessage,
  setDraftMessage,
} from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import styles from "./cvChatMessageComposer.module.css";

const PROMPT_CHIPS = [
  "Make it more concise",
  "Quantify my impact",
  "Match the job's tone",
  "Improve ATS keyword coverage",
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
    void dispatch(sendMessage({ sessionId, userMessage: trimmed }));
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
              key={chip}
              type="button"
              className={styles.chip}
              onClick={() => dispatch(setDraftMessage(chip))}
            >
              <span aria-hidden="true">↳</span>
              {chip}
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
          placeholder={atLimit ? "Session limit reached." : "Ask Hirable to refine further…  (Ctrl/⌘+Enter to send)"}
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
