import { useAppSelector } from "../hooks";
import { ConversationPage } from "../features/conversation/conversationPage";
import { CvGeneratorPage } from "../features/cvGeneration/cvGeneratorPage";
import { SubscriptionPage } from "../features/subscription/subscriptionPage";
import { TemplatesPage } from "../features/templates/templatesPage";
import { UserMemoryPage } from "../features/userMemory/userMemoryPage";
import type { AppTab } from "./tabs";

export function TabSwitcher({ activeTab }: { activeTab: AppTab }) {
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);

  switch (activeTab) {
    case "templates":
      return <TemplatesPage />;
    case "user memory":
      return <UserMemoryPage />;
    case "subscription":
      return <SubscriptionPage />;
    case "session":
      return activeSessionId ? <ConversationPage /> : <CvGeneratorPage />;
    case "cv":
    default:
      return <CvGeneratorPage />;
  }
}
