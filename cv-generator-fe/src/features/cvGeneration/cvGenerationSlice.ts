import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import { sendChatMessage } from "../../api/cvChat";
import type { ChatMessage, GenerateCvResponse, SendChatMessageInput } from "../../types/chat";

type Status = "idle" | "loading" | "succeeded" | "failed";

type CvGenerationState = {
  conversationId: string | null;
  messageHistory: ChatMessage[];
  draftMessage: string;
  status: Status;
  error: string | null;
  latestPdfBase64: string | null;
};

const initialState: CvGenerationState = {
  conversationId: null,
  messageHistory: [],
  draftMessage: "",
  status: "idle",
  error: null,
  latestPdfBase64: null,
};

export const sendMessage = createAsyncThunk<
  GenerateCvResponse,
  SendChatMessageInput,
  { rejectValue: string }
>("cvGeneration/sendMessage", async (input, { rejectWithValue }) => {
  try {
    return await sendChatMessage(input);
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to send message");
  }
});

const appendAssistantMessage = (state: CvGenerationState, payload: GenerateCvResponse) => {
  if ("questions" in payload.content) {
    state.messageHistory.push({
      role: "assistant",
      type: "question",
      content: payload.content.questions.join("\n\n"),
    });
    return;
  }
  state.messageHistory.push({
    role: "assistant",
    type: "cv",
    content: payload.content.latex,
  });
  state.latestPdfBase64 = payload.content.pdf_base64 || null;
};

const cvGenerationSlice = createSlice({
  name: "cvGeneration",
  initialState,
  reducers: {
    setDraftMessage(state, action: PayloadAction<string>) {
      state.draftMessage = action.payload;
    },
    resetChat() {
      return initialState;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = "loading";
        state.error = null;
        state.messageHistory.push({
          role: "user",
          type: "text",
          content: action.meta.arg.userMessage,
        });
        state.draftMessage = "";
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.conversationId = action.payload.conversation_id;
        appendAssistantMessage(state, action.payload);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload ?? action.error.message ?? "Unable to send message";
      });
  },
});

export const { setDraftMessage, resetChat } = cvGenerationSlice.actions;
export default cvGenerationSlice.reducer;
