import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { RootState } from "../../../store/store";
import type { CvQuestion } from "../../../types/chat";

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
