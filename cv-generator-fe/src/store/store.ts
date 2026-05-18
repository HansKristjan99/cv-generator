import { configureStore } from "@reduxjs/toolkit";

import { apiClient } from "../api/client";
import cvGenerationReducer from "../features/cvGeneration/cvGenerationSlice";

export const store = configureStore({
  reducer: {
    cvGeneration: cvGenerationReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: {
        extraArgument: apiClient,
      },
      serializableCheck: {
        ignoredActionPaths: ["meta.arg"],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
