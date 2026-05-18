import { enhanceAnswers } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import type { CvQuestion } from "../types/chat";
import styles from "./cvChatEnhanceButton.module.css";

export const CvChatEnhanceButton = ({ questions }: { questions: CvQuestion[] }) => {
  const dispatch = useAppDispatch();
  const status = useAppSelector((s) => s.cvGeneration.status);

  const loading = status === "loading";
  const disabled = loading || questions.length === 0;

  return (
    <button
      type="button"
      className={styles.enhance}
      disabled={disabled}
      onClick={() => void dispatch(enhanceAnswers(questions))}
    >
      <span aria-hidden="true">✨</span>
      {loading ? "Enhancing…" : "Enhance"}
    </button>
  );
};
