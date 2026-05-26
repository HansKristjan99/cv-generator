import type {
  Award,
  Education,
  JobExperience,
  Project,
  SkillSection,
} from "../../../../types/cv";

export const newJob = (): JobExperience => ({
  company: "",
  location: "",
  position: "",
  start_date: "",
  end_date: "Present",
  bullets: [],
});

export const newEducation = (): Education => ({
  institution: "",
  location: "",
  degree: "",
  start_date: "",
  end_date: "",
  gpa: null,
  thesis: null,
  coursework: null,
});

export const newSkill = (): SkillSection => ({ title: "", items: "" });

export const newProject = (): Project => ({ name: "", description: "", url: null });

export const newAward = (): Award => ({ title: "", issuer: null, date: null });
