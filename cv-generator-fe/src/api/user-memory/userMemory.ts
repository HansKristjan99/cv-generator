import { authFetch, readErrorMessage } from "../auth-utils/authFetch";

export type JobExperienceBullet = {
  id: string;
  bullet_points: string;
  relevant_technologies: string | null;
};

export type JobExperience = {
  id: string;
  company_name: string;
  job_title: string;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
  bullets: JobExperienceBullet[];
};

export type EducationExperience = {
  id: string;
  degree: string;
  field_of_study: string | null;
  institution: string;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
};

export type Project = {
  id: string;
  title: string;
  description: string | null;
  link: string | null;
};

export type Skill = {
  id: string;
  name: string;
};

export type Award = {
  id: string;
  title: string;
  issuer: string | null;
  date: string | null;
  description: string | null;
  link: string | null;
};

export type MemoryNote = {
  id: string;
  content: string;
};

export type UserMemory = {
  job_experiences: JobExperience[];
  education_experiences: EducationExperience[];
  projects: Project[];
  skills: Skill[];
  awards: Award[];
  notes: MemoryNote[];
};

export type IdPatch = {
  id?: string | null;
  delete?: boolean;
};

export type JobExperienceBulletPatch = IdPatch & Partial<Omit<JobExperienceBullet, "id">>;
export type JobExperiencePatch = IdPatch &
  Partial<Omit<JobExperience, "id" | "bullets">> & {
    bullets?: JobExperienceBulletPatch[];
  };
export type EducationExperiencePatch = IdPatch & Partial<Omit<EducationExperience, "id">>;
export type ProjectPatch = IdPatch & Partial<Omit<Project, "id">>;
export type SkillPatch = IdPatch & Partial<Omit<Skill, "id">>;
export type AwardPatch = IdPatch & Partial<Omit<Award, "id">>;
export type MemoryNotePatch = IdPatch & Partial<Omit<MemoryNote, "id">>;

export type UserMemoryPatch = {
  job_experiences?: JobExperiencePatch[];
  education_experiences?: EducationExperiencePatch[];
  projects?: ProjectPatch[];
  skills?: SkillPatch[];
  awards?: AwardPatch[];
  notes?: MemoryNotePatch[];
};

export async function getUserMemory(): Promise<UserMemory> {
  const response = await authFetch("/api/users/memory");

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as UserMemory;
}

export async function updateUserMemory(patch: UserMemoryPatch): Promise<UserMemory> {
  const response = await authFetch("/api/users/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as UserMemory;
}
