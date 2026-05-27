import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type SavedCv = {
  id: string;
  name: string;
  template_id: string | null;
  created_at: string;
};

export type SavedCl = {
  id: string;
  name: string;
  created_at: string;
};

export type JobRequirement = {
  requirement: string;
  importance: "must_have" | "nice_to_have";
  met: boolean;
  evidence: string;
  question: string;
};

export type RequirementsAnalysis = {
  requirements: JobRequirement[];
};

export type JobApplication = {
  id: string;
  job_name: string;
  job_description: string | null;
  submitted_cv_id: string | null;
  submitted_cl_id: string | null;
  status: string;
  notes: string | null;
  job_requirements: RequirementsAnalysis | null;
  created_at: string;
  updated_at: string;
};

export type JobApplicationCreate = {
  job_name: string;
  job_description?: string | null;
  submitted_cv_id?: string | null;
  submitted_cl_id?: string | null;
  status?: string;
  notes?: string | null;
};

export type JobApplicationUpdate = Partial<JobApplicationCreate>;

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return (await res.json()) as T;
}

async function okOrThrow(res: Response): Promise<void> {
  if (!res.ok) throw new Error(await readErrorMessage(res));
}

export async function listJobApplications(): Promise<JobApplication[]> {
  return jsonOrThrow(await authFetch("/job-applications"));
}

export async function createJobApplication(
  body: JobApplicationCreate,
): Promise<JobApplication> {
  return jsonOrThrow(
    await authFetch("/job-applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function startApplicationFromSession(
  sessionId: string,
  jobName: string,
): Promise<JobApplication> {
  return jsonOrThrow(
    await authFetch("/job-applications/from-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, job_name: jobName }),
    }),
  );
}

export async function updateJobApplication(
  id: string,
  body: JobApplicationUpdate,
): Promise<JobApplication> {
  return jsonOrThrow(
    await authFetch(`/job-applications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function deleteJobApplication(id: string): Promise<void> {
  await okOrThrow(await authFetch(`/job-applications/${id}`, { method: "DELETE" }));
}

export async function listSavedCvs(): Promise<SavedCv[]> {
  return jsonOrThrow(await authFetch("/job-applications/cvs"));
}

export async function saveCvFromSession(
  name: string,
  sessionId: string,
): Promise<SavedCv> {
  return jsonOrThrow(
    await authFetch("/job-applications/cvs/from-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, session_id: sessionId }),
    }),
  );
}

export async function deleteSavedCv(id: string): Promise<void> {
  await okOrThrow(await authFetch(`/job-applications/cvs/${id}`, { method: "DELETE" }));
}

export async function renderSavedCvPdf(id: string): Promise<string> {
  const { pdf_base64 } = await jsonOrThrow<{ pdf_base64: string }>(
    await authFetch(`/job-applications/cvs/${id}/pdf`),
  );
  return pdf_base64;
}

export async function listSavedCls(): Promise<SavedCl[]> {
  return jsonOrThrow(await authFetch("/job-applications/cls"));
}

export async function saveClFromSession(
  name: string,
  sessionId: string,
): Promise<SavedCl> {
  return jsonOrThrow(
    await authFetch("/job-applications/cls/from-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, session_id: sessionId }),
    }),
  );
}

export async function deleteSavedCl(id: string): Promise<void> {
  await okOrThrow(await authFetch(`/job-applications/cls/${id}`, { method: "DELETE" }));
}

export async function renderSavedClPdf(id: string): Promise<string> {
  const { pdf_base64 } = await jsonOrThrow<{ pdf_base64: string }>(
    await authFetch(`/job-applications/cls/${id}/pdf`),
  );
  return pdf_base64;
}

