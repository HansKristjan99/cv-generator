import type { CvStructuredData } from "../../../../types/cv";
import { Field, FieldRow, ItemCard, ListEditor, Section } from "./formPrimitives";
import { newAward, newEducation, newJob, newProject, newSkill } from "./newItems";

type Props = {
  data: CvStructuredData;
  onChange: (patch: Partial<CvStructuredData>) => void;
};

export function CvForm({ data, onChange }: Props) {
  return (
    <>
      <Section title="Contact">
        <FieldRow>
          <Field label="Name" value={data.name} onChange={(v) => onChange({ name: v })} />
          <Field label="Location" value={data.location} onChange={(v) => onChange({ location: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Email" value={data.email} onChange={(v) => onChange({ email: v })} />
          <Field
            label="Phone"
            value={data.phone ?? ""}
            onChange={(v) => onChange({ phone: v || null })}
          />
        </FieldRow>
        <Field
          label="Links (one per line)"
          value={data.links.join("\n")}
          multiline
          onChange={(v) =>
            onChange({ links: v.split("\n").map((l) => l.trim()).filter(Boolean) })
          }
        />
      </Section>

      <Section title="Summary">
        <Field
          label="Professional summary"
          value={data.summary}
          multiline
          rows={4}
          onChange={(v) => onChange({ summary: v })}
        />
      </Section>

      <Section title="Experience">
        <ListEditor
          items={data.experience}
          onChange={(experience) => onChange({ experience })}
          newItem={newJob}
          renderItem={(job, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Company" value={job.company} onChange={(v) => onItemChange({ ...job, company: v })} />
                <Field label="Position" value={job.position} onChange={(v) => onItemChange({ ...job, position: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="Location" value={job.location} onChange={(v) => onItemChange({ ...job, location: v })} />
                <Field label="Start date" value={job.start_date} onChange={(v) => onItemChange({ ...job, start_date: v })} />
                <Field label="End date" value={job.end_date} onChange={(v) => onItemChange({ ...job, end_date: v })} />
              </FieldRow>
              <Field
                label="Bullets (one per line)"
                value={job.bullets.join("\n")}
                multiline
                rows={4}
                onChange={(v) =>
                  onItemChange({
                    ...job,
                    bullets: v.split("\n").map((l) => l.trim()).filter(Boolean),
                  })
                }
              />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Education">
        <ListEditor
          items={data.education}
          onChange={(education) => onChange({ education })}
          newItem={newEducation}
          renderItem={(edu, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Institution" value={edu.institution} onChange={(v) => onItemChange({ ...edu, institution: v })} />
                <Field label="Degree" value={edu.degree} onChange={(v) => onItemChange({ ...edu, degree: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="Location" value={edu.location} onChange={(v) => onItemChange({ ...edu, location: v })} />
                <Field label="Start date" value={edu.start_date} onChange={(v) => onItemChange({ ...edu, start_date: v })} />
                <Field label="End date" value={edu.end_date} onChange={(v) => onItemChange({ ...edu, end_date: v })} />
              </FieldRow>
              <FieldRow>
                <Field label="GPA" value={edu.gpa ?? ""} onChange={(v) => onItemChange({ ...edu, gpa: v || null })} />
                <Field label="Thesis" value={edu.thesis ?? ""} onChange={(v) => onItemChange({ ...edu, thesis: v || null })} />
              </FieldRow>
              <Field label="Coursework" value={edu.coursework ?? ""} onChange={(v) => onItemChange({ ...edu, coursework: v || null })} />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Skills">
        <ListEditor
          items={data.skills}
          onChange={(skills) => onChange({ skills })}
          newItem={newSkill}
          renderItem={(skill, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <Field label="Category" value={skill.title} onChange={(v) => onItemChange({ ...skill, title: v })} />
              <Field
                label="Items (comma-separated)"
                value={skill.items}
                onChange={(v) => onItemChange({ ...skill, items: v })}
              />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Projects">
        <ListEditor
          items={data.projects}
          onChange={(projects) => onChange({ projects })}
          newItem={newProject}
          renderItem={(proj, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Name" value={proj.name} onChange={(v) => onItemChange({ ...proj, name: v })} />
                <Field label="URL" value={proj.url ?? ""} onChange={(v) => onItemChange({ ...proj, url: v || null })} />
              </FieldRow>
              <Field
                label="Description"
                value={proj.description}
                multiline
                onChange={(v) => onItemChange({ ...proj, description: v })}
              />
            </ItemCard>
          )}
        />
      </Section>

      <Section title="Awards">
        <ListEditor
          items={data.awards}
          onChange={(awards) => onChange({ awards })}
          newItem={newAward}
          renderItem={(award, idx, onItemChange, onRemove) => (
            <ItemCard key={idx} onRemove={onRemove}>
              <FieldRow>
                <Field label="Title" value={award.title} onChange={(v) => onItemChange({ ...award, title: v })} />
                <Field label="Issuer" value={award.issuer ?? ""} onChange={(v) => onItemChange({ ...award, issuer: v || null })} />
                <Field label="Date" value={award.date ?? ""} onChange={(v) => onItemChange({ ...award, date: v || null })} />
              </FieldRow>
            </ItemCard>
          )}
        />
      </Section>
    </>
  );
}
