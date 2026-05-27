import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { SessionSummary } from "../../../types/chat";

export const fetchChatSessions = createAsyncThunk<SessionSummary[], void, { extra: ApiClient }>(
  "cvGeneration/fetchChatSessions",
  async (_, { extra }) => extra.getChatSessions(),
);
