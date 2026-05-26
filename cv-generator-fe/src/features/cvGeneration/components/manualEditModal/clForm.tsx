import type { ClStructuredData } from "../../../../types/cv";
import { Field, FieldRow, Section } from "./formPrimitives";

type Props = {
  data: ClStructuredData;
  onChange: (patch: Partial<ClStructuredData>) => void;
};

export function ClForm({ data, onChange }: Props) {
  return (
    <>
      <Section title="Your details">
        <FieldRow>
          <Field label="Name" value={data.name} onChange={(v) => onChange({ name: v })} />
          <Field label="Title" value={data.title} onChange={(v) => onChange({ title: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Email" value={data.email} onChange={(v) => onChange({ email: v })} />
          <Field label="Phone" value={data.phone ?? ""} onChange={(v) => onChange({ phone: v || null })} />
        </FieldRow>
        <FieldRow>
          <Field label="Location" value={data.location} onChange={(v) => onChange({ location: v })} />
          <Field
            label="LinkedIn"
            value={data.linkedin ?? ""}
            onChange={(v) => onChange({ linkedin: v || null })}
          />
        </FieldRow>
      </Section>

      <Section title="Addressing">
        <FieldRow>
          <Field label="Recipient" value={data.recipient} onChange={(v) => onChange({ recipient: v })} />
          <Field label="Company" value={data.company} onChange={(v) => onChange({ company: v })} />
        </FieldRow>
        <FieldRow>
          <Field label="Greeting" value={data.greeting} onChange={(v) => onChange({ greeting: v })} />
          <Field label="Sign-off" value={data.closer} onChange={(v) => onChange({ closer: v })} />
        </FieldRow>
      </Section>

      <Section title="Body">
        <Field
          label="Letter body (paragraphs separated by blank lines)"
          value={data.body}
          multiline
          rows={14}
          onChange={(v) => onChange({ body: v })}
        />
      </Section>
    </>
  );
}
