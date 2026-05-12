import { configureStore } from "@reduxjs/toolkit";

import cvGenerationReducer from "../features/cvGeneration/cvGenerationSlice";

export const store = configureStore({
  reducer: {
    cvGeneration: cvGenerationReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActionPaths: ["meta.arg"],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
