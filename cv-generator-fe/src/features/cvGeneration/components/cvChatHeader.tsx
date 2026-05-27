import { useAppSelector } from "../../../hooks";
import { RequirementsBar } from "../../jobApplications/components/requirementsBar";
import styles from "./cvChatHeader.module.css";

export const CvChatHeader = () => {
  const jobRequirements = useAppSelector((s) => s.cvGeneration.jobRequirements);
  return (
    <header className={styles.header}>
      <div className={styles.avatar}>H</div>
      <div className={styles.titles}>
        <p className={styles.title}>Hireable</p>
        <p className={styles.subtitle}>opinionated, evidence-traced</p>
      </div>
      <div className={styles.headerRight}>
        <RequirementsBar analysis={jobRequirements} compact />
      </div>
    </header>
  );
};
