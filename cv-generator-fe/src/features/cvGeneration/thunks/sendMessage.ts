import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { AppDispatch } from "../../../store/store";
import type { SendChatMessageInput } from "../../../types/chat";
import { fetchChatSessions } from "./fetchChatSessions";
import { loadConversation } from "./loadConversation";

export const sendMessage = createAsyncThunk<
  { sessionId: string; isNewSession: boolean },
  SendChatMessageInput,
  { extra: ApiClient; rejectValue: string; dispatch: AppDispatch }
>("cvGeneration/sendMessage", async (input, { extra, rejectWithValue, dispatch }) => {
  try {
    const start = await extra.sendChatMessage(input);
    dispatch({ type: "cvGeneration/setActiveSession", payload: start.session_id });
    void dispatch(fetchChatSessions());
    void dispatch(loadConversation(start.session_id));
    return { sessionId: start.session_id, isNewSession: input.sessionId === null };
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to send message");
  }
});
