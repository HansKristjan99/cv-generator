import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { CvQuota } from "../../api/cv-chat/quota";
import type { ApiClient } from "../../api/client";
import type { AppDispatch, RootState } from "../../store/store";
import {
  type ChatMessage,
  type CvQuestion,
  type JobStatusResponse,
  type LoadConversationResponse,
  type SendChatMessageInput,
  type SessionSummary,
} from "../../types/chat";

type Status = "idle" | "loading" | "succeeded" | "failed";

type ConversationState = {
  conversationId: string | null;
  jobDescription: string;
  messageHistory: ChatMessage[];
  draftMessage: string;
  generationStatus: Status;
  historyStatus: Status;
  enhanceStatus: Status;
  error: string | null;
  latestPdfBase64: string | null;
  activeJobId: string | null;
};

type CvGenerationState = {
  activeSessionId: string | null;
  setupStatus: Status;
  setupError: string | null;
  monthlySessionsUsed: number | null;
  monthlyInventsUsed: number | null;
  isUnlimited: boolean;
  chatSessions: SessionSummary[];
  conversationsById: Record<string, ConversationState>;
  pollingJobIds: Record<string, true>;
};

const createConversationState = (conversationId: string | null = null): ConversationState => ({
  conversationId,
  jobDescription: "",
  messageHistory: [],
  draftMessage: "",
  generationStatus: "idle",
  historyStatus: "idle",
  enhanceStatus: "idle",
  error: null,
  latestPdfBase64: null,
  activeJobId: null,
});

const initialState: CvGenerationState = {
  activeSessionId: null,
  setupStatus: "idle",
  setupError: null,
  monthlySessionsUsed: null,
  monthlyInventsUsed: null,
  isUnlimited: false,
  chatSessions: [],
  conversationsById: {},
  pollingJobIds: {},
};

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

const isPendingJobStatus = (status: SessionSummary["latest_job_status"]) =>
  status === "pending" || status === "running";

function getConversation(
  state: CvGenerationState,
  sessionId: string,
  conversationId?: string | null,
): ConversationState {
  state.conversationsById[sessionId] ??= createConversationState(conversationId ?? null);
  const conversation = state.conversationsById[sessionId];
  if (conversationId !== undefined) {
    conversation.conversationId = conversationId;
  }
  return conversation;
}

function getActiveConversation(state: CvGenerationState): ConversationState | null {
  return state.activeSessionId ? state.conversationsById[state.activeSessionId] ?? null : null;
}

function findSessionIdByConversationId(
  state: CvGenerationState,
  conversationId: string | null,
): string | null {
  if (!conversationId) return null;
  for (const [sessionId, conversation] of Object.entries(state.conversationsById)) {
    if (conversation.conversationId === conversationId) return sessionId;
  }
  return state.chatSessions.find((session) => session.conversation_id === conversationId)?.id ?? null;
}

async function pollJobUntilDone(
  extra: ApiClient,
  jobId: string,
): Promise<JobStatusResponse> {
  const start = Date.now();
  while (true) {
    if (Date.now() - start > POLL_TIMEOUT_MS) {
      throw new Error("Generation timed out. Please try again.");
    }
    await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    const job = await extra.getJobStatus(jobId);
    if (job.status === "succeeded" || job.status === "failed") return job;
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
  { extra: ApiClient; rejectValue: { sessionId: string; error: string } }
>("cvGeneration/loadConversation", async (sessionId, { extra, rejectWithValue }) => {
  try {
    return await extra.getChatHistory(sessionId);
  } catch (error) {
    return rejectWithValue({
      sessionId,
      error: error instanceof Error ? error.message : "Failed to load conversation",
    });
  }
});

export const pollJob = createAsyncThunk<
  { sessionId: string; jobId: string; status: JobStatusResponse["status"]; error: string | null },
  { sessionId: string; jobId: string },
  {
    extra: ApiClient;
    rejectValue: { sessionId: string; jobId: string; error: string };
    dispatch: AppDispatch;
  }
>("cvGeneration/pollJob", async ({ sessionId, jobId }, { extra, rejectWithValue, dispatch }) => {
  try {
    const job = await pollJobUntilDone(extra, jobId);
    void dispatch(fetchChatSessions());
    if (job.status === "succeeded") {
      void dispatch(loadConversation(sessionId));
    }
    return { sessionId, jobId, status: job.status, error: job.error };
  } catch (error) {
    return rejectWithValue({
      sessionId,
      jobId,
      error: error instanceof Error ? error.message : "Unable to poll generation status",
    });
  }
});

export const sendMessage = createAsyncThunk<
  {
    sessionId: string;
    conversationId: string;
    jobId: string;
    isNewSession: boolean;
    jobDescription?: string;
  },
  SendChatMessageInput,
  {
    extra: ApiClient;
    state: RootState;
    rejectValue: { sessionId: string | null; error: string };
    dispatch: AppDispatch;
  }
>("cvGeneration/sendMessage", async (input, { extra, getState, rejectWithValue, dispatch }) => {
  const existingSessionId = findSessionIdByConversationId(
    getState().cvGeneration,
    input.conversationId,
  );

  try {
    const start = await extra.sendChatMessage(input);
    void dispatch(fetchChatSessions());
    void dispatch(loadConversation(start.session_id));
    void dispatch(pollJob({ sessionId: start.session_id, jobId: start.job_id }));
    return {
      sessionId: start.session_id,
      conversationId: start.conversation_id,
      jobId: start.job_id,
      isNewSession: input.conversationId === null,
      jobDescription: input.jobDescription,
    };
  } catch (error) {
    return rejectWithValue({
      sessionId: existingSessionId,
      error: error instanceof Error ? error.message : "Unable to send message",
    });
  }
});

export const enhanceAnswers = createAsyncThunk<
  string,
  CvQuestion[],
  { extra: ApiClient; state: RootState; rejectValue: string }
>("cvGeneration/enhanceAnswers", async (questions, { extra, getState, rejectWithValue }) => {
  const { activeSessionId, conversationsById } = getState().cvGeneration;
  const conversation = activeSessionId ? conversationsById[activeSessionId] : null;
  if (!conversation?.conversationId) {
    return rejectWithValue("No active conversation to enhance.");
  }
  try {
    const { invented_answers } = await extra.inventCvAnswers({
      conversation_id: conversation.conversationId,
      job_description: conversation.jobDescription,
      questions,
    });
    return invented_answers;
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to enhance answers");
  }
});

const cvGenerationSlice = createSlice({
  name: "cvGeneration",
  initialState,
  reducers: {
    setDraftMessage(state, action: PayloadAction<string>) {
      const conversation = getActiveConversation(state);
      if (conversation) {
        conversation.draftMessage = action.payload;
      }
    },
    setActiveSession(
      state,
      action: PayloadAction<{ sessionId: string; conversationId?: string | null }>,
    ) {
      state.activeSessionId = action.payload.sessionId;
      getConversation(state, action.payload.sessionId, action.payload.conversationId);
    },
    resetChat(state) {
      state.activeSessionId = null;
      state.setupStatus = "idle";
      state.setupError = null;
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
        for (const session of action.payload) {
          const conversation = getConversation(state, session.id, session.conversation_id);
          if (session.latest_job_id && isPendingJobStatus(session.latest_job_status)) {
            conversation.activeJobId = session.latest_job_id;
            conversation.generationStatus = "loading";
            conversation.error = null;
          } else if (session.latest_job_status === "failed") {
            if (conversation.activeJobId === session.latest_job_id) {
              conversation.activeJobId = null;
            }
            conversation.generationStatus = "failed";
            conversation.error = session.latest_job_error ?? "Generation failed.";
          } else if (session.latest_job_id && conversation.activeJobId === session.latest_job_id) {
            conversation.activeJobId = null;
            conversation.generationStatus = "succeeded";
          }
        }
      })
      .addCase(loadConversation.pending, (state, action) => {
        const conversation = getConversation(state, action.meta.arg);
        conversation.historyStatus = "loading";
        conversation.error = null;
      })
      .addCase(loadConversation.fulfilled, (state, action) => {
        const conversation = getConversation(
          state,
          action.meta.arg,
          action.payload.conversation_id,
        );
        conversation.messageHistory = action.payload.messages;
        conversation.latestPdfBase64 = action.payload.latest_pdf_base64;
        conversation.historyStatus = "idle";
        if (!conversation.activeJobId && conversation.generationStatus !== "failed") {
          conversation.generationStatus = "idle";
        }
      })
      .addCase(loadConversation.rejected, (state, action) => {
        const sessionId = action.payload?.sessionId ?? action.meta.arg;
        const conversation = getConversation(state, sessionId);
        conversation.historyStatus = "failed";
        conversation.error =
          action.payload?.error ?? action.error.message ?? "Failed to load conversation";
      })
      .addCase(sendMessage.pending, (state, action) => {
        state.setupError = null;
        if (action.meta.arg.conversationId === null) {
          state.setupStatus = "loading";
          return;
        }

        const sessionId = findSessionIdByConversationId(state, action.meta.arg.conversationId);
        if (!sessionId) return;
        const conversation = getConversation(state, sessionId, action.meta.arg.conversationId);
        conversation.generationStatus = "loading";
        conversation.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.setupStatus = "idle";
        state.setupError = null;

        const conversation = getConversation(
          state,
          action.payload.sessionId,
          action.payload.conversationId,
        );
        conversation.activeJobId = action.payload.jobId;
        conversation.generationStatus = "loading";
        conversation.error = null;
        conversation.draftMessage = "";
        if (action.payload.jobDescription) {
          conversation.jobDescription = action.payload.jobDescription;
        }
        if (action.payload.isNewSession && state.monthlySessionsUsed !== null) {
          state.monthlySessionsUsed += 1;
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        const error = action.payload?.error ?? action.error.message ?? "Unable to send message";
        if (action.payload?.sessionId) {
          const conversation = getConversation(state, action.payload.sessionId);
          conversation.generationStatus = "failed";
          conversation.error = error;
          return;
        }
        state.setupStatus = "failed";
        state.setupError = error;
      })
      .addCase(pollJob.pending, (state, action) => {
        state.pollingJobIds[action.meta.arg.jobId] = true;
        const conversation = getConversation(state, action.meta.arg.sessionId);
        conversation.activeJobId = action.meta.arg.jobId;
        conversation.generationStatus = "loading";
        conversation.error = null;
      })
      .addCase(pollJob.fulfilled, (state, action) => {
        delete state.pollingJobIds[action.payload.jobId];
        const conversation = getConversation(state, action.payload.sessionId);
        if (conversation.activeJobId === action.payload.jobId) {
          conversation.activeJobId = null;
        }
        if (action.payload.status === "failed") {
          conversation.generationStatus = "failed";
          conversation.error = action.payload.error ?? "Generation failed.";
        } else {
          conversation.generationStatus = "succeeded";
          conversation.error = null;
        }
      })
      .addCase(pollJob.rejected, (state, action) => {
        const { sessionId, jobId } = action.payload ?? action.meta.arg;
        delete state.pollingJobIds[jobId];
        const conversation = getConversation(state, sessionId);
        if (conversation.activeJobId === jobId) {
          conversation.activeJobId = null;
        }
        conversation.generationStatus = "failed";
        conversation.error =
          action.payload?.error ?? action.error.message ?? "Unable to poll generation status";
      })
      .addCase(enhanceAnswers.pending, (state) => {
        const conversation = getActiveConversation(state);
        if (!conversation) return;
        conversation.enhanceStatus = "loading";
        conversation.error = null;
      })
      .addCase(enhanceAnswers.fulfilled, (state, action) => {
        const conversation = getActiveConversation(state);
        if (!conversation) return;
        conversation.enhanceStatus = "succeeded";
        conversation.draftMessage = action.payload;
        if (state.monthlyInventsUsed !== null) {
          state.monthlyInventsUsed += 1;
        }
      })
      .addCase(enhanceAnswers.rejected, (state, action) => {
        const conversation = getActiveConversation(state);
        if (!conversation) return;
        conversation.enhanceStatus = "failed";
        conversation.error = action.payload ?? action.error.message ?? "Unable to enhance answers";
      });
  },
});

export const selectActiveConversation = (state: RootState) => {
  const sessionId = state.cvGeneration.activeSessionId;
  return sessionId ? state.cvGeneration.conversationsById[sessionId] ?? null : null;
};

export const { setDraftMessage, setActiveSession, resetChat } = cvGenerationSlice.actions;
export default cvGenerationSlice.reducer;
