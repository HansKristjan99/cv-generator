import { ConversationPage } from "../features/cvGeneration/conversationPage";
import { CvGeneratorPage } from "../features/cvGeneration/cvGeneratorPage";
import { JobApplicationsPage } from "../features/jobApplications/jobApplicationsPage";
import { SubscriptionPage } from "../features/subscription/subscriptionPage";
import { TemplatesPage } from "../features/templates/templatesPage";
import { UserMemoryPage } from "../features/userMemory/userMemoryPage";
import type { AppTab } from "./tabs";

type Props = {
  activeTab: AppTab;
  activeSessionId: string | null;
};

export function TabSwitcher({ activeTab, activeSessionId }: Props) {
  switch (activeTab) {
    case "templates":
      return <TemplatesPage />;
    case "user memory":
      return <UserMemoryPage />;
    case "applications":
      return <JobApplicationsPage />;
    case "subscription":
      return <SubscriptionPage />;
    case "session":
      return activeSessionId ? <ConversationPage sessionId={activeSessionId} /> : <CvGeneratorPage />;
    case "cv":
    default:
      return <CvGeneratorPage />;
  }
}
