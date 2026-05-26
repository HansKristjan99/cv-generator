import { useEffect } from "react";

import {
  fetchChatSessions,
  isGeneratingSession,
  loadConversation,
  selectActiveConversation,
} from "../../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../../hooks";
import type { RegistrationStatus } from "./useApiRegistration";

const REFRESH_MS = 60_000;
const POLL_MS = 2_000;

export function useSessionPolling(status: RegistrationStatus) {
  const dispatch = useAppDispatch();
  const chatSessions = useAppSelector((s) => s.cvGeneration.chatSessions);
  const activeSessionId = useAppSelector((s) => s.cvGeneration.activeSessionId);
  const activeConversation = useAppSelector(selectActiveConversation);
  const hasGeneratingSession = chatSessions.some((s) => isGeneratingSession(s.status));

  useEffect(() => {
    if (status !== "ready") return;
    void dispatch(fetchChatSessions());
    const id = window.setInterval(() => {
      void dispatch(fetchChatSessions());
    }, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [dispatch, status]);

  useEffect(() => {
    if (status !== "ready" || !hasGeneratingSession) return;
    const id = window.setInterval(() => {
      void dispatch(fetchChatSessions());
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [dispatch, hasGeneratingSession, status]);

  useEffect(() => {
    if (
      status !== "ready" ||
      !activeSessionId ||
      activeConversation?.generationStatus !== "loading"
    ) {
      return;
    }
    void dispatch(loadConversation(activeSessionId));
    const id = window.setInterval(() => {
      void dispatch(loadConversation(activeSessionId));
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [activeConversation?.generationStatus, activeSessionId, dispatch, status]);
}
