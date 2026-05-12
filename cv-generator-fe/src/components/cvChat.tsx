import { useAppSelector } from "../hooks";
import { CvChatHeader } from "./cvChatHeader";
import { CvChatMessageComposer } from "./cvChatMessageComposer";
import { CvChatSetup } from "./cvChatSetup";
import { CvChatMessageList } from "./cvMessageList";

export const CvChat = () => {
  const { conversationId, messageHistory } = useAppSelector((s) => s.cvGeneration);
  const started = Boolean(conversationId) || messageHistory.length > 0;

  if (!started) {
    return <CvChatSetup />;
  }

  return (
    <div className="cv-chat">
      <CvChatHeader />
      <CvChatMessageList />
      <CvChatMessageComposer />
    </div>
  );
};
