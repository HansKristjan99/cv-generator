import { MAX_INVENTS_PER_MONTH } from "../config/limits";
import { enhanceAnswers } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import type { CvQuestion } from "../types/chat";
import styles from "./cvChatEnhanceButton.module.css";

export const CvChatEnhanceButton = ({ questions }: { questions: CvQuestion[] }) => {
  const dispatch = useAppDispatch();
  const { status, monthlyInventsUsed, isUnlimited } = useAppSelector((s) => s.cvGeneration);

  const inventsRemaining =
    !isUnlimited && monthlyInventsUsed !== null ? MAX_INVENTS_PER_MONTH - monthlyInventsUsed : null;
  const atLimit = inventsRemaining !== null && inventsRemaining <= 0;
  const loading = status === "loading";
  const disabled = loading || questions.length === 0 || atLimit;

  return (
    <div className={styles.wrapper}>
      <button
        type="button"
        className={styles.enhance}
        disabled={disabled}
        onClick={() => void dispatch(enhanceAnswers(questions))}
      >
        <span aria-hidden="true">✨</span>
        {loading ? "Enhancing…" : atLimit ? "Limit reached" : "Enhance"}
      </button>
      {inventsRemaining !== null && inventsRemaining <= 3 ? (
        <p className={atLimit ? styles.limitReached : styles.limitNote}>
          {atLimit
            ? `Monthly enhancement limit reached (${MAX_INVENTS_PER_MONTH}/${MAX_INVENTS_PER_MONTH}).`
            : `${inventsRemaining} enhancement${inventsRemaining === 1 ? "" : "s"} left this month`}
        </p>
      ) : null}
    </div>
  );
};
