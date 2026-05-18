import { registerCurrentUser } from "./user-management/addUser";
import { sendChatMessage } from "./cv-chat/cvChat";
import { inventCvAnswers } from "./cv-chat/inventAnswers";
import { getCvQuota } from "./cv-chat/quota";
import { getUserMemory, updateUserMemory } from "./user-memory/userMemory";

export const apiClient = {
  registerCurrentUser,
  sendChatMessage,
  inventCvAnswers,
  getCvQuota,
  getUserMemory,
  updateUserMemory,
};

export type ApiClient = typeof apiClient;
