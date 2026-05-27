import { createAsyncThunk } from "@reduxjs/toolkit";

import type { ApiClient } from "../../../api/client";
import type { CvQuota } from "../../../api/cv-chat/quota";

export const fetchQuota = createAsyncThunk<CvQuota, void, { extra: ApiClient }>(
  "cvGeneration/fetchQuota",
  async (_, { extra }) => extra.getCvQuota(),
);
