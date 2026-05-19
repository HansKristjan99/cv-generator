import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { CvQuota } from "../../api/cv-chat/quota";
import type { ApiClient } from "../../api/client";
import type { RootState } from "../../store/store";
import type {
  ChatMessage,
  CvQuestion,
  GenerateCvResponse,
  SendChatMessageInput,
} from "../../types/chat";

type Status = "idle" | "loading" | "succeeded" | "failed";

type CvGenerationState = {
  conversationId: string | null;
  jobDescription: string;
  messageHistory: ChatMessage[];
  draftMessage: string;
  status: Status;
  error: string | null;
  latestPdfBase64: string | null;
  monthlySessionsUsed: number | null;
  monthlyInventsUsed: number | null;
  isUnlimited: boolean;
};

const initialState: CvGenerationState = {
  conversationId: null,
  jobDescription: "",
  messageHistory: [],
  draftMessage: "",
  status: "idle",
  error: null,
  latestPdfBase64: null,
  monthlySessionsUsed: null,
  monthlyInventsUsed: null,
  isUnlimited: false,
};

export const fetchQuota = createAsyncThunk<CvQuota, void, { extra: ApiClient }>(
  "cvGeneration/fetchQuota",
  async (_, { extra }) => extra.getCvQuota(),
);

export const sendMessage = createAsyncThunk<
  GenerateCvResponse,
  SendChatMessageInput,
  { extra: ApiClient; rejectValue: string }
>("cvGeneration/sendMessage", async (input, { extra, rejectWithValue }) => {
  try {
    return await extra.sendChatMessage(input);
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to send message");
  }
});

export const enhanceAnswers = createAsyncThunk<
  string,
  CvQuestion[],
  { extra: ApiClient; state: RootState; rejectValue: string }
>("cvGeneration/enhanceAnswers", async (questions, { extra, getState, rejectWithValue }) => {
  const { conversationId, jobDescription } = getState().cvGeneration;
  if (!conversationId) {
    return rejectWithValue("No active conversation to enhance.");
  }
  try {
    const { invented_answers } = await extra.inventCvAnswers({
      conversation_id: conversationId,
      job_description: jobDescription,
      questions,
    });
    return invented_answers;
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to enhance answers");
  }
});

const appendAssistantMessage = (state: CvGenerationState, payload: GenerateCvResponse) => {
  if ("questions" in payload.content) {
    state.messageHistory.push({
      role: "assistant",
      type: "question",
      content: payload.content.questions.map((q) => q.question).join("\n\n"),
      questions: payload.content.questions,
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
    resetChat(state) {
      return {
        ...initialState,
        monthlySessionsUsed: state.monthlySessionsUsed,
        monthlyInventsUsed: state.monthlyInventsUsed,
        isUnlimited: state.isUnlimited,
      };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchQuota.fulfilled, (state, action) => {
        state.monthlySessionsUsed = action.payload.sessions_used;
        state.monthlyInventsUsed = action.payload.invents_used;
        state.isUnlimited = action.payload.is_unlimited;
      })
      .addCase(sendMessage.pending, (state, action) => {
        state.status = "loading";
        state.error = null;
        if (action.meta.arg.jobDescription) {
          state.jobDescription = action.meta.arg.jobDescription;
        }
        state.messageHistory.push({
          role: "user",
          type: "text",
          content: action.meta.arg.userMessage,
        });
        state.draftMessage = "";
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "succeeded";
        const isNewSession = action.meta.arg.conversationId === null;
        state.conversationId = action.payload.conversation_id;
        if (isNewSession && state.monthlySessionsUsed !== null) {
          state.monthlySessionsUsed += 1;
        }
        appendAssistantMessage(state, action.payload);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload ?? action.error.message ?? "Unable to send message";
      })
      .addCase(enhanceAnswers.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(enhanceAnswers.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.draftMessage = action.payload;
        if (state.monthlyInventsUsed !== null) {
          state.monthlyInventsUsed += 1;
        }
      })
      .addCase(enhanceAnswers.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload ?? action.error.message ?? "Unable to enhance answers";
      });
  },
});

export const { setDraftMessage, resetChat } = cvGenerationSlice.actions;
export default cvGenerationSlice.reducer;
