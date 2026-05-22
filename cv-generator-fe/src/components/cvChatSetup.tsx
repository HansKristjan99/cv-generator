import { type FormEvent, useState } from "react";

import {
  MAX_CV_TEXT_CHARS,
  MAX_FILE_SIZE_BYTES,
  MAX_FILE_SIZE_MB,
  MAX_JOB_DESCRIPTION_CHARS,
  MAX_SESSIONS_PER_MONTH,
} from "../config/limits";
import { sendMessage } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";
import type { GenerationKind } from "../types/chat";
import { cx } from "../utils/cx";
import styles from "./cvChatSetup.module.css";

const OPENING_PROMPTS = [
  "Make it more concise.",
  "Optimize it for ATS screening.",
  "Lead with my strongest, most relevant experience.",
  "Match the tone of the job description.",
];

const PAGE_OPTIONS = [
  { value: 1, title: "1 page", desc: "Junior to mid-level" },
  { value: 2, title: "2 pages", desc: "Senior, 8+ years" },
  { value: 3, title: "3 pages", desc: "Staff / principal" },
];

export const CvChatSetup = () => {
  const dispatch = useAppDispatch();
  const { setupStatus, error: setupError, monthlySessionsUsed, isUnlimited } = useAppSelector(
    (s) => s.cvGeneration,
  );

  const [cvText, setCvText] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [openingMessage, setOpeningMessage] = useState("");
  const [pageCount, setPageCount] = useState(1);

  const isLoading = setupStatus === "loading";
  const hasCv = Boolean(cvText.trim() || cvFile);
  const hasJob = Boolean(jobDescription.trim());
  const sessionsRemaining =
    !isUnlimited && monthlySessionsUsed !== null ? MAX_SESSIONS_PER_MONTH - monthlySessionsUsed : null;
  const atSessionLimit = sessionsRemaining !== null && sessionsRemaining <= 0;
  const canStart = hasCv && hasJob && !isLoading && !atSessionLimit && !fileError;

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    if (f && f.size > MAX_FILE_SIZE_BYTES) {
      setFileError(`File too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`);
      return;
    }
    setFileError(null);
    setCvFile(f);
  };

  const start = (kind: GenerationKind) => {
    if (!canStart) return;
    const defaultMessage =
      kind === "cover_letter"
        ? "Write a cover letter tailored to this job."
        : "Help me write a CV tailored to this job.";
    void dispatch(
      sendMessage({
        sessionId: null,
        userMessage: openingMessage.trim() || defaultMessage,
        cvText,
        cvFile,
        jobDescription,
        pageCount,
        kind,
      }),
    );
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    start("cv");
  };

  return (
    <form className={styles.setup} onSubmit={onSubmit}>
      <header className={styles.hero}>
        <span className={styles.step}>Step 1 of 2</span>
        <h2 className={styles.heroTitle}>
          Paste what you have. Hirable does the <em>close reading</em>.
        </h2>
        <p className={styles.heroSub}>
          Drop in your existing CV and the job description. Hirable rereads both like an editor —
          keeping what fits, sharpening what's vague, and tracing every change back to the listing.
        </p>
      </header>

      <div className={styles.grid}>
        <section className={styles.cvField}>
          <div className={styles.fieldHead}>
            <span className={cx(styles.numTile, styles.numTileMint)}>01</span>
            <label htmlFor="setup-cv-text" className={styles.fieldLabel}>
              Your CV
            </label>
            <span className={cx(styles.required, styles.requiredMint)}>Required</span>
          </div>
          <textarea
            id="setup-cv-text"
            className={styles.textarea}
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            placeholder="Paste the full text of your current CV…"
            rows={9}
            maxLength={MAX_CV_TEXT_CHARS}
          />
          <label htmlFor="setup-cv-file" className={styles.dropzone}>
            <span className={styles.dropIcon} aria-hidden="true">
              ↑
            </span>
            <span className={styles.dropText}>
              <span className={styles.dropTitle}>{cvFile ? cvFile.name : "Or drop in a PDF"}</span>
              <span className={styles.dropHint}>
                PDF up to {MAX_FILE_SIZE_MB} MB · Hirable parses it cleanly
              </span>
            </span>
            <span className={styles.dropBrowse}>Browse</span>
          </label>
          <input
            id="setup-cv-file"
            className={styles.fileInput}
            type="file"
            accept="application/pdf,.pdf"
            onChange={onFileChange}
          />
          {fileError ? <p className={styles.fieldError}>{fileError}</p> : null}
        </section>

        <section className={styles.jdField}>
          <div className={styles.fieldHead}>
            <span className={cx(styles.numTile, styles.numTileSky)}>02</span>
            <label htmlFor="setup-job" className={styles.fieldLabel}>
              Job description
            </label>
            <span className={cx(styles.required, styles.requiredSky)}>Required</span>
          </div>
          <textarea
            id="setup-job"
            className={styles.textarea}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job posting here — the fuller the listing, the sharper Hirable gets."
            rows={13}
            maxLength={MAX_JOB_DESCRIPTION_CHARS}
          />
        </section>
      </div>

      <section className={styles.optional}>
        <div className={styles.optionalHead}>
          <span className={styles.optionalGlyph} aria-hidden="true">
            iii
          </span>
          <span className={styles.optionalLabel}>
            Opening message <span className={styles.optionalTag}>(optional)</span>
          </span>
        </div>
        <div className={styles.promptChips}>
          {OPENING_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className={styles.promptChip}
              onClick={() => setOpeningMessage(prompt)}
            >
              <span aria-hidden="true">+</span>
              {prompt}
            </button>
          ))}
        </div>
        <input
          id="setup-message"
          className={styles.openingInput}
          type="text"
          value={openingMessage}
          onChange={(e) => setOpeningMessage(e.target.value)}
          placeholder="Tell Hirable which angle to chase…"
        />
      </section>

      <section className={styles.length}>
        <div className={styles.lengthHead}>
          <span className={styles.lengthLabel}>CV length</span>
          <span className={styles.lengthHint}>Hirable renders to exactly this many pages.</span>
        </div>
        <div className={styles.lengthOptions} role="radiogroup" aria-label="CV length in pages">
          {PAGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={pageCount === option.value}
              className={cx(styles.lengthChip, pageCount === option.value && styles.lengthChipOn)}
              onClick={() => setPageCount(option.value)}
            >
              <span className={styles.lengthChipValue}>{option.value}</span>
              <span className={styles.lengthChipText}>
                <span className={styles.lengthChipTitle}>{option.title}</span>
                <span className={styles.lengthChipDesc}>{option.desc}</span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <footer className={styles.actions}>
        <ul className={styles.checks}>
          <li className={hasCv ? styles.checkOn : styles.checkOff}>
            <span className={styles.checkBox}>{hasCv ? "✓" : ""}</span>
            CV added
          </li>
          <li className={hasJob ? styles.checkOn : styles.checkOff}>
            <span className={styles.checkBox}>{hasJob ? "✓" : ""}</span>
            Job description added
          </li>
        </ul>
        <div className={styles.startGroup}>
          {sessionsRemaining !== null ? (
            <p className={atSessionLimit ? styles.quotaExhausted : styles.quotaNote}>
              {atSessionLimit
                ? `Monthly limit reached (${MAX_SESSIONS_PER_MONTH} sessions used).`
                : `${sessionsRemaining} of ${MAX_SESSIONS_PER_MONTH} sessions remaining this month`}
            </p>
          ) : null}
          <div className={styles.startButtons}>
            <button
              type="button"
              className={styles.startSecondary}
              onClick={() => start("cover_letter")}
              disabled={!canStart}
            >
              {isLoading ? "Starting…" : "Generate a cover letter"}
            </button>
            <button type="submit" className={styles.start} disabled={!canStart}>
              {isLoading ? "Starting…" : "Start the chat →"}
            </button>
          </div>
        </div>
      </footer>
      {setupError ? <p className={styles.error}>{setupError}</p> : null}
    </form>
  );
};
