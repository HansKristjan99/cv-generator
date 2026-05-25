import { registerCurrentUser } from "./user-management/addUser";
import { sendChatMessage, getChatSessions, getChatHistory } from "./cv-chat/cvChat";
import { manualEditCv } from "./cv-chat/cvEdit";
import { inventCvAnswers } from "./cv-chat/inventAnswers";
import { getCvQuota } from "./cv-chat/quota";
import { getUserMemory, updateUserMemory } from "./user-memory/userMemory";
import { getTemplates } from "./templates/getTemplates";
import { getUserSettings, updateUserSettings } from "./user-settings/userSettings";
import {
  createBillingPortalSession,
  createCheckoutSession,
  getCheckoutSessionStatus,
  getSubscription,
} from "./billing/billing";

export const apiClient = {
  registerCurrentUser,
  sendChatMessage,
  manualEditCv,
  inventCvAnswers,
  getCvQuota,
  getChatSessions,
  getChatHistory,
  getUserMemory,
  updateUserMemory,
  getTemplates,
  getUserSettings,
  updateUserSettings,
  createBillingPortalSession,
  createCheckoutSession,
  getCheckoutSessionStatus,
  getSubscription,
};

export type ApiClient = typeof apiClient;
