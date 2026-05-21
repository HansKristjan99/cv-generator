import { registerCurrentUser } from "./user-management/addUser";
import { sendChatMessage, getChatSessions, getChatHistory } from "./cv-chat/cvChat";
import { inventCvAnswers } from "./cv-chat/inventAnswers";
import { getCvQuota } from "./cv-chat/quota";
import { getUserMemory, updateUserMemory } from "./user-memory/userMemory";
import { getTemplates } from "./templates/getTemplates";
import { getUserSettings, updateUserSettings } from "./user-settings/userSettings";

export const apiClient = {
  registerCurrentUser,
  sendChatMessage,
  inventCvAnswers,
  getCvQuota,
  getChatSessions,
  getChatHistory,
  getUserMemory,
  updateUserMemory,
  getTemplates,
  getUserSettings,
  updateUserSettings,
};

export type ApiClient = typeof apiClient;
