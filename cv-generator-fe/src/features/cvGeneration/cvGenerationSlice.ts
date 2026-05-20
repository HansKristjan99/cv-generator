import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { CvQuota } from "../../api/cv-chat/quota";
import type { ApiClient } from "../../api/client";
import type { AppDispatch, RootState } from "../../store/store";
import type {
  ChatMessage,
  CvQuestion,
  GenerateCvResponse,
  LoadConversationResponse,
  SendChatMessageInput,
  SessionSummary,
} from "../../types/chat";

type Status = "idle" | "loading" | "succeeded" | "failed";

type CvGenerationState = {
  activeSessionId: string | null;
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
  chatSessions: SessionSummary[];
};

const initialState: CvGenerationState = {
  activeSessionId: null,
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
  chatSessions: [],
};

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

async function pollJobUntilDone(
  extra: ApiClient,
  jobId: string,
): Promise<GenerateCvResponse> {
  const start = Date.now();
  while (true) {
    if (Date.now() - start > POLL_TIMEOUT_MS) {
      throw new Error("Generation timed out. Please try again.");
    }
    await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    const job = await extra.getJobStatus(jobId);
    if (job.status === "succeeded" && job.result) return job.result;
    if (job.status === "failed") throw new Error(job.error ?? "Generation failed.");
  }
}

export const fetchQuota = createAsyncThunk<CvQuota, void, { extra: ApiClient }>(
  "cvGeneration/fetchQuota",
  async (_, { extra }) => extra.getCvQuota(),
);

export const fetchChatSessions = createAsyncThunk<SessionSummary[], void, { extra: ApiClient }>(
  "cvGeneration/fetchChatSessions",
  async (_, { extra }) => extra.getChatSessions(),
);

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

export const sendMessage = createAsyncThunk<
  { result: GenerateCvResponse; sessionId: string },
  SendChatMessageInput,
  { extra: ApiClient; rejectValue: string; dispatch: AppDispatch }
>("cvGeneration/sendMessage", async (input, { extra, rejectWithValue, dispatch }) => {
  try {
    const start = await extra.sendChatMessage(input);
    if (input.conversationId === null) {
      dispatch(
        setActiveSession({
          sessionId: start.session_id,
          conversationId: start.conversation_id,
        }),
      );
      dispatch(fetchChatSessions());
    }
    const result = await pollJobUntilDone(extra, start.job_id);
    if (input.conversationId === null) {
      dispatch(fetchChatSessions());
    }
    return { result, sessionId: start.session_id };
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
      content: "",
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
    setActiveSession(
      state,
      action: PayloadAction<{ sessionId: string; conversationId: string }>,
    ) {
      state.activeSessionId = action.payload.sessionId;
      state.conversationId = action.payload.conversationId;
    },
    resetChat(state) {
      return {
        ...initialState,
        monthlySessionsUsed: state.monthlySessionsUsed,
        monthlyInventsUsed: state.monthlyInventsUsed,
        isUnlimited: state.isUnlimited,
        chatSessions: state.chatSessions,
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
      .addCase(fetchChatSessions.fulfilled, (state, action) => {
        state.chatSessions = action.payload;
      })
      .addCase(loadConversation.pending, (state, action) => {
        state.activeSessionId = action.meta.arg;
        state.messageHistory = [];
        state.latestPdfBase64 = null;
        state.draftMessage = "";
        state.error = null;
        state.status = "loading";
      })
      .addCase(loadConversation.fulfilled, (state, action) => {
        // Drop result if user clicked a different chat while this one was loading.
        if (state.activeSessionId !== action.meta.arg) return;
        state.conversationId = action.payload.conversation_id;
        state.messageHistory = action.payload.messages;
        state.latestPdfBase64 = action.payload.latest_pdf_base64;
        state.status = "idle";
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
        // Drop result if user navigated to a different session while polling.
        if (state.activeSessionId !== action.payload.sessionId) return;
        state.status = "succeeded";
        const isNewSession = action.meta.arg.conversationId === null;
        state.conversationId = action.payload.result.conversation_id;
        if (isNewSession && state.monthlySessionsUsed !== null) {
          state.monthlySessionsUsed += 1;
        }
        appendAssistantMessage(state, action.payload.result);
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

export const { setDraftMessage, setActiveSession, resetChat } = cvGenerationSlice.actions;
export default cvGenerationSlice.reducer;
