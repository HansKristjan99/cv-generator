import { type FormEvent, useState } from "react";

import { sendMessage } from "../features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "../hooks";

export const CvChatSetup = () => {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((s) => s.cvGeneration);

  const [cvText, setCvText] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [openingMessage, setOpeningMessage] = useState("");

  const isLoading = status === "loading";
  const hasCv = Boolean(cvText.trim() || cvFile);
  const hasJob = Boolean(jobDescription.trim());
  const canStart = hasCv && hasJob && !isLoading;

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canStart) return;
    void dispatch(
      sendMessage({
        conversationId: null,
        userMessage: openingMessage.trim() || "Help me write a CV tailored to this job.",
        cvText,
        cvFile,
        jobDescription,
      }),
    );
  };

  return (
    <form className="cv-chat-setup" onSubmit={onSubmit}>
      <div className="cv-chat-setup-intro">
        <h2>Let's tailor your CV</h2>
        <p>Paste your existing CV (or upload a PDF), drop in the job description, and we'll get going.</p>
      </div>

      <div className="cv-chat-setup-field">
        <label htmlFor="setup-cv-text">Your CV</label>
        <textarea
          id="setup-cv-text"
          value={cvText}
          onChange={(e) => setCvText(e.target.value)}
          placeholder="Paste your current CV here..."
          rows={8}
        />
        <label htmlFor="setup-cv-file" className="cv-chat-setup-sublabel">Or upload a PDF</label>
        <input
          id="setup-cv-file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(e) => setCvFile(e.target.files?.[0] ?? null)}
        />
        {cvFile ? <p className="cv-chat-setup-filename">{cvFile.name}</p> : null}
      </div>

      <div className="cv-chat-setup-field">
        <label htmlFor="setup-job">Job description</label>
        <textarea
          id="setup-job"
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Paste the job posting here..."
          rows={8}
        />
      </div>

      <div className="cv-chat-setup-field">
        <label htmlFor="setup-message">Opening message <span className="cv-chat-setup-optional">(optional)</span></label>
        <input
          id="setup-message"
          type="text"
          value={openingMessage}
          onChange={(e) => setOpeningMessage(e.target.value)}
          placeholder="e.g. Help me write a CV tailored to this job."
        />
      </div>

      <div className="cv-chat-setup-actions">
        <button type="submit" disabled={!canStart}>
          {isLoading ? "Starting..." : "Start chat"}
        </button>
        {!hasCv ? <span className="cv-chat-setup-hint">Add your CV (text or PDF).</span> : null}
        {!hasJob ? <span className="cv-chat-setup-hint">Add a job description.</span> : null}
        {error ? <span className="cv-chat-setup-error">{error}</span> : null}
      </div>
    </form>
  );
};
