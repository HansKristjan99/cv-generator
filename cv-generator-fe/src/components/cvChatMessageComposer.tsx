import { sendMessage, setDraftMessage } from "../features/cvGeneration/cvGenerationSlice";
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
  const { draftMessage, conversationId, status } = useAppSelector((s) => s.cvGeneration);

  const trimmed = draftMessage.trim();
  const disabled = status === "loading" || !trimmed;

  const onSend = () => {
    if (disabled) return;
    void dispatch(sendMessage({ conversationId, userMessage: trimmed }));
  };

  return (
    <div className={styles.composer}>
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
          placeholder="Ask Hirable to refine further…  (Ctrl/⌘+Enter to send)"
        />
        <button type="button" className={styles.send} onClick={onSend} disabled={disabled}>
          Send
        </button>
      </div>
    </div>
  );
};
