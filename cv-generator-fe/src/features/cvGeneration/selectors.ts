import type { RootState } from "../../store/store";

export const selectActiveConversation = (state: RootState) =>
  state.cvGeneration.activeSessionId ? state.cvGeneration : null;
