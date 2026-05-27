import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { LoadConversationResponse } from "../../../types/chat";

export const loadConversation = createAsyncThunk<
  LoadConversationResponse,
  string,
  { extra: ApiClient; rejectValue: string }
>("cvGeneration/loadConversation", async (sessionId, { extra, rejectWithValue }) => {
  try {
    return await extra.getChatHistory(sessionId);
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Failed to load conversation");
  }
});
