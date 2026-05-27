import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { RootState } from "../../../store/store";
import type { ClStructuredData, CvStructuredData } from "../../../types/cv";

type ManualEditInput = {
  kind: "cv" | "cover_letter";
  data: CvStructuredData | ClStructuredData;
};

type ManualEditResult = {
  kind: "cv" | "cover_letter";
  pdf_base64: string;
  data: CvStructuredData | ClStructuredData;
};

export const saveManualEdit = createAsyncThunk<
  ManualEditResult,
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
