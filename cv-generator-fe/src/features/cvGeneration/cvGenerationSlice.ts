import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { CvQuota } from "../../api/cv-chat/quota";
import type { ApiClient } from "../../api/client";
import type { AppDispatch, RootState } from "../../store/store";
import {
  type ChatMessage,
  type CvQuestion,
  type LoadConversationResponse,
  type PreviewKind,
  type SendChatMessageInput,
  type SessionStatus,
  type SessionSummary,
} from "../../types/chat";
import type { ClStructuredData, CvStructuredData } from "../../types/cv";

type Status = "idle" | "loading" | "succeeded" | "failed";

type CvGenerationState = {
  activeSessionId: string | null;
  messageHistory: ChatMessage[];
  draftMessage: string;
  setupStatus: Status;
  generationStatus: Status;
  historyStatus: Status;
  enhanceStatus: Status;
  manualEditStatus: Status;
  error: string | null;
  jobDescription: string | null;
  sourceCvText: string | null;
  sourceCvPdfBase64: string | null;
  latestCvPdfBase64: string | null;
  latestCoverLetterPdfBase64: string | null;
  latestCvStructured: CvStructuredData | null;
  latestClStructured: ClStructuredData | null;
  previewSelection: PreviewKind | null;
  monthlySessionsUsed: number | null;
  monthlyInventsUsed: number | null;
  isUnlimited: boolean;
  chatSessions: SessionSummary[];
};

const initialState: CvGenerationState = {
  activeSessionId: null,
  messageHistory: [],
  draftMessage: "",
  setupStatus: "idle",
  generationStatus: "idle",
  historyStatus: "idle",
  enhanceStatus: "idle",
  manualEditStatus: "idle",
  error: null,
  jobDescription: null,
  sourceCvText: null,
  sourceCvPdfBase64: null,
  latestCvPdfBase64: null,
  latestCoverLetterPdfBase64: null,
  latestCvStructured: null,
  latestClStructured: null,
  previewSelection: null,
  monthlySessionsUsed: null,
  monthlyInventsUsed: null,
  isUnlimited: false,
  chatSessions: [],
};

const PREVIEW_RESET = {
  jobDescription: null,
  sourceCvText: null,
  sourceCvPdfBase64: null,
  latestCvPdfBase64: null,
  latestCoverLetterPdfBase64: null,
  latestCvStructured: null,
  latestClStructured: null,
  previewSelection: null,
} as const;

export const isGeneratingSession = (status: SessionStatus) =>
  status === "pending" || status === "running";

const toGenerationStatus = (status: SessionStatus): Status => {
  if (isGeneratingSession(status)) return "loading";
  if (status === "failed") return "failed";
  return "idle";
};

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
  { sessionId: string; isNewSession: boolean },
  SendChatMessageInput,
  { extra: ApiClient; rejectValue: string; dispatch: AppDispatch }
>("cvGeneration/sendMessage", async (input, { extra, rejectWithValue, dispatch }) => {
  try {
    const start = await extra.sendChatMessage(input);
    dispatch(setActiveSession(start.session_id));
    void dispatch(fetchChatSessions());
    void dispatch(loadConversation(start.session_id));
    return { sessionId: start.session_id, isNewSession: input.sessionId === null };
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to send message");
  }
});

export const enhanceAnswers = createAsyncThunk<
  string,
  CvQuestion[],
  { extra: ApiClient; state: RootState; rejectValue: string }
>("cvGeneration/enhanceAnswers", async (questions, { extra, getState, rejectWithValue }) => {
  const { activeSessionId } = getState().cvGeneration;
  if (!activeSessionId) {
    return rejectWithValue("No active conversation to enhance.");
  }
  try {
    const { invented_answers } = await extra.inventCvAnswers({
      session_id: activeSessionId,
      questions,
    });
    return invented_answers;
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Unable to enhance answers");
  }
});

type ManualEditInput = {
  kind: "cv" | "cover_letter";
  data: CvStructuredData | ClStructuredData;
};

export const saveManualEdit = createAsyncThunk<
  { kind: "cv" | "cover_letter"; pdf_base64: string; data: CvStructuredData | ClStructuredData },
  ManualEditInput,
  { extra: ApiClient; state: RootState; rejectValue: string }
>("cvGeneration/saveManualEdit", async ({ kind, data }, { extra, getState, rejectWithValue }) => {
  const { activeSessionId } = getState().cvGeneration;
  if (!activeSessionId) return rejectWithValue("No active session.");
  try {
    const { pdf_base64 } = await extra.manualEditCv(activeSessionId, kind, data);
    return { kind, pdf_base64, data };
  } catch (error) {
    return rejectWithValue(error instanceof Error ? error.message : "Failed to save edits.");
  }
});

const cvGenerationSlice = createSlice({
  name: "cvGeneration",
  initialState,
  reducers: {
    setDraftMessage(state, action: PayloadAction<string>) {
      state.draftMessage = action.payload;
    },
    setPreviewSelection(state, action: PayloadAction<PreviewKind | null>) {
      state.previewSelection = action.payload;
    },
    setActiveSession(state, action: PayloadAction<string>) {
      if (state.activeSessionId === action.payload) return;
      state.activeSessionId = action.payload;
      state.messageHistory = [];
      state.draftMessage = "";
      state.error = null;
      Object.assign(state, PREVIEW_RESET);
      state.historyStatus = "idle";
      state.generationStatus = "idle";
      state.enhanceStatus = "idle";
    },
    resetChat(state) {
      state.activeSessionId = null;
      state.messageHistory = [];
      state.draftMessage = "";
      state.setupStatus = "idle";
      state.generationStatus = "idle";
      state.historyStatus = "idle";
      state.enhanceStatus = "idle";
      state.error = null;
      Object.assign(state, PREVIEW_RESET);
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
        const activeSession = action.payload.find((session) => session.id === state.activeSessionId);
        if (!activeSession) return;

        if (isGeneratingSession(activeSession.status)) {
          state.generationStatus = "loading";
          state.error = null;
        } else if (activeSession.status === "failed") {
          state.generationStatus = "failed";
          state.error = activeSession.error ?? "Generation failed.";
        } else if (state.generationStatus !== "loading") {
          state.generationStatus = "idle";
          state.error = null;
        }
      })
      .addCase(loadConversation.pending, (state, action) => {
        if (state.activeSessionId !== action.meta.arg) {
          state.activeSessionId = action.meta.arg;
          state.messageHistory = [];
          state.draftMessage = "";
          Object.assign(state, PREVIEW_RESET);
        }
        state.historyStatus = "loading";
        state.error = null;
      })
      .addCase(loadConversation.fulfilled, (state, action) => {
        if (state.activeSessionId !== action.meta.arg) return;
        state.messageHistory = action.payload.messages;
        state.jobDescription = action.payload.job_description;
        state.sourceCvText = action.payload.source_cv_text;
        state.sourceCvPdfBase64 = action.payload.source_cv_pdf_base64;
        state.latestCvPdfBase64 = action.payload.latest_cv_pdf_base64;
        state.latestCoverLetterPdfBase64 = action.payload.latest_cover_letter_pdf_base64;
        state.latestCvStructured = action.payload.latest_cv_structured ?? null;
        state.latestClStructured = action.payload.latest_cover_letter_structured ?? null;
        state.generationStatus = toGenerationStatus(action.payload.status);
        state.error =
          action.payload.status === "failed"
            ? action.payload.error ?? "Generation failed."
            : action.payload.error;
        state.historyStatus = "idle";
      })
      .addCase(loadConversation.rejected, (state, action) => {
        if (state.activeSessionId !== action.meta.arg) return;
        state.historyStatus = "failed";
        state.error = action.payload ?? action.error.message ?? "Failed to load conversation";
      })
      .addCase(sendMessage.pending, (state, action) => {
        state.error = null;
        if (action.meta.arg.sessionId === null) {
          state.setupStatus = "loading";
        } else {
          state.generationStatus = "loading";
        }
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.activeSessionId = action.payload.sessionId;
        state.setupStatus = "idle";
        state.generationStatus = "loading";
        state.error = null;
        state.draftMessage = "";
        if (action.payload.isNewSession && state.monthlySessionsUsed !== null) {
          state.monthlySessionsUsed += 1;
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        const error = action.payload ?? action.error.message ?? "Unable to send message";
        if (action.meta.arg.sessionId === null) {
          state.setupStatus = "failed";
        } else {
          state.generationStatus = "failed";
        }
        state.error = error;
      })
      .addCase(enhanceAnswers.pending, (state) => {
        state.enhanceStatus = "loading";
        state.error = null;
      })
      .addCase(enhanceAnswers.fulfilled, (state, action) => {
        state.enhanceStatus = "succeeded";
        state.draftMessage = action.payload;
        if (state.monthlyInventsUsed !== null) {
          state.monthlyInventsUsed += 1;
        }
      })
      .addCase(enhanceAnswers.rejected, (state, action) => {
        state.enhanceStatus = "failed";
        state.error = action.payload ?? action.error.message ?? "Unable to enhance answers";
      })
      .addCase(saveManualEdit.pending, (state) => {
        state.manualEditStatus = "loading";
        state.error = null;
      })
      .addCase(saveManualEdit.fulfilled, (state, action) => {
        state.manualEditStatus = "idle";
        if (action.payload.kind === "cv") {
          state.latestCvPdfBase64 = action.payload.pdf_base64;
          state.latestCvStructured = action.payload.data as CvStructuredData;
        } else {
          state.latestCoverLetterPdfBase64 = action.payload.pdf_base64;
          state.latestClStructured = action.payload.data as ClStructuredData;
        }
      })
      .addCase(saveManualEdit.rejected, (state, action) => {
        state.manualEditStatus = "failed";
        state.error = action.payload ?? action.error.message ?? "Failed to save edits.";
      });
  },
});

export const selectActiveConversation = (state: RootState) =>
  state.cvGeneration.activeSessionId ? state.cvGeneration : null;

export const { setDraftMessage, setPreviewSelection, setActiveSession, resetChat } =
  cvGenerationSlice.actions;
export default cvGenerationSlice.reducer;
