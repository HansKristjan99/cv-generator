import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { ClStructuredData, CvStructuredData } from "../../types/cv";
import type { PreviewKind } from "../../types/chat";
import { initialState, PREVIEW_RESET } from "./state/initialState";
import { isGeneratingSession, toGenerationStatus } from "./state/statusUtils";
import { enhanceAnswers } from "./thunks/enhanceAnswers";
import { fetchChatSessions } from "./thunks/fetchChatSessions";
import { fetchQuota } from "./thunks/fetchQuota";
import { loadConversation } from "./thunks/loadConversation";
import { saveManualEdit } from "./thunks/saveManualEdit";
import { sendMessage } from "./thunks/sendMessage";

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

export const { setDraftMessage, setPreviewSelection, setActiveSession, resetChat } =
  cvGenerationSlice.actions;

export default cvGenerationSlice.reducer;
