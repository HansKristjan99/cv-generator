import type {
  JobExperience,
  JobExperienceBullet,
} from "../../../api/user-memory/userMemory";
import type { BulletDraft, JobDraft } from "./types";

export function jobToDraft(job: JobExperience): JobDraft {
  return {
    id: job.id,
    company_name: job.company_name,
    job_title: job.job_title,
    start_date: job.start_date ?? "",
    end_date: job.end_date ?? "",
    location: job.location ?? "",
    bullets: job.bullets.map(bulletToDraft),
  };
}

export function bulletToDraft(bullet: JobExperienceBullet): BulletDraft {
  return {
    id: bullet.id,
    bullet_points: bullet.bullet_points,
    relevant_technologies: bullet.relevant_technologies ?? "",
  };
}

export function blankJob(): JobDraft {
  return {
    id: "",
    company_name: "",
    job_title: "",
    start_date: "",
    end_date: "",
    location: "",
    bullets: [],
  };
}
