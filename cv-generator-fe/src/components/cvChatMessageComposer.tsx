import { sendMessage, setDraftMessage } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";

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
    <div className="cv-chat-message-composer">
      <input
        type="text"
        value={draftMessage}
        onChange={(e) => dispatch(setDraftMessage(e.target.value))}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder="Type your message..."
        disabled={status === "loading"}
      />
      <button type="button" onClick={onSend} disabled={disabled}>
        Send
      </button>
    </div>
  );
};
