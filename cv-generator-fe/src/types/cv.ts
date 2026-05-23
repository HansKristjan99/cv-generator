/** Mirrors the backend CurriculumVitae and CoverLetter Pydantic schemas. */

export type JobExperience = {
  company: string;
  location: string;
  position: string;
  start_date: string;
  end_date: string;
  bullets: string[];
};

export type Education = {
  institution: string;
  location: string;
  degree: string;
  start_date: string;
  end_date: string;
  gpa: string | null;
  thesis: string | null;
  coursework: string | null;
};

export type SkillSection = {
  title: string;
  items: string;
};

export type Project = {
  name: string;
  description: string;
  url: string | null;
};

export type Award = {
  title: string;
  issuer: string | null;
  date: string | null;
};

export type Requirement = {
  requirement: string;
  why_satisfied_by_cv: string;
};

export type CvStructuredData = {
  name: string;
  location: string;
  email: string;
  phone: string | null;
  links: string[];
  summary: string;
  experience: JobExperience[];
  education: Education[];
  skills: SkillSection[];
  projects: Project[];
  awards: Award[];
  job_requirements: Requirement[];
};

export type ClStructuredData = {
  name: string;
  title: string;
  email: string;
  phone: string | null;
  location: string;
  linkedin: string | null;
  recipient: string;
  company: string;
  greeting: string;
  body: string;
  closer: string;
};

export type ManualEditResponse = {
  pdf_base64: string;
};
